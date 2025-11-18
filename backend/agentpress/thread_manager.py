from typing import List, Dict, Any, Optional, Type, Union, AsyncGenerator
from backend.services.supabase import DBConnection
from agentpress.tool_registry import ToolRegistry
from agentpress.response_processor import ResponseProcessor, ProcessorConfig
from agentpress.tool import Tool
import uuid
import datetime
import structlog
import json
from openai import AsyncOpenAI

logger = structlog.get_logger()


class ThreadManager:
    def __init__(self, ollama_client: Optional[AsyncOpenAI] = None):
        self.db = DBConnection()
        self.tool_registry = ToolRegistry()
        self.response_processor = ResponseProcessor(
            tool_registry=self.tool_registry,
            add_message_callback=self.add_message
        )
        # Client Ollama pour les appels LLM
        self.ollama_client = ollama_client

    def add_tool(self, tool_class: Type[Tool], **kwargs):
        """Ajouter un outil au ThreadManager"""
        self.tool_registry.register_tool(tool_class, **kwargs)

    async def create_thread(self, user_id: str, metadata: Optional[Dict] = None) -> str:
        """Créer une nouvelle conversation"""
        client = await self.db.client
        thread_data = {
            'conversation_id': str(uuid.uuid4()),
            'user_id': user_id,
            'metadata': metadata or {}
        }
        result = await client.table('conversations').insert(thread_data).execute()
        return result.data[0]['conversation_id']

    async def add_message(
        self, thread_id: str, type: str, content: Any,
        is_llm_message: bool = False, metadata: Optional[Dict] = None,
        agent_id: Optional[str] = None, agent_version_id: Optional[str] = None
    ):
        """Ajouter un message à la conversation - adapté pour votre schéma"""
        client = await self.db.client

        # Adapter le type vers role pour votre schéma
        role = "user" if type == "user" else "assistant" if type == "assistant" else type

        message_data = {
            'message_id': str(uuid.uuid4()),
            'conversation_id': thread_id,
            'role': role,  # Utiliser 'role' au lieu de 'type'
            'content': content,
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }

        # Ajouter les champs optionnels s'ils existent dans votre schéma
        if hasattr(self, '_has_is_llm_message_column'):
            message_data['is_llm_message'] = is_llm_message

        result = await client.table('messages').insert(message_data).execute()
        return result.data[0] if result.data else None

    async def get_llm_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Récupérer les messages LLM - adapté pour votre schéma"""
        client = await self.db.client

        try:
            # Utiliser 'role' au lieu de 'is_llm_message' pour filtrer
            result = await client.table('messages').select('message_id, content, role') \
                .eq('conversation_id', thread_id).in_('role', ['user', 'assistant']) \
                .order('timestamp').execute()

            messages = []
            for item in result.data:
                if isinstance(item['content'], str):
                    try:
                        parsed_content = json.loads(item['content'])
                        parsed_content['message_id'] = item['message_id']
                        messages.append(parsed_content)
                    except json.JSONDecodeError:
                        # Si ce n'est pas du JSON, créer un format compatible
                        messages.append({
                            'role': item['role'],
                            'content': item['content'],
                            'message_id': item['message_id']
                        })
                else:
                    content = item['content']
                    content['message_id'] = item['message_id']
                    messages.append(content)

            return messages

        except Exception as e:
            logger.error(f"Failed to get messages for thread {thread_id}: {str(e)}")
            return []

    async def run_thread(
        self,
        thread_id: str,
        system_prompt: Dict[str, Any],
        stream: bool = True,
        llm_model: str = "llama3.2",
        llm_temperature: float = 0.7,
        llm_max_tokens: Optional[int] = 2000,
        processor_config: Optional[ProcessorConfig] = None,
        include_xml_examples: bool = False,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Version complète de run_thread avec intégration Ollama"""

        logger.info(f"Starting thread execution for thread {thread_id} with Ollama model {llm_model}")

        # Configuration par défaut
        if not processor_config:
            processor_config = ProcessorConfig(
                xml_tool_calling=True,
                execute_tools=True,
                tool_execution_strategy="sequential"
            )

        # Copie de travail du prompt système
        working_system_prompt = system_prompt.copy()

        # Ajouter les exemples XML d'outils si demandé
        if include_xml_examples and processor_config.xml_tool_calling:
            openapi_schemas = self.tool_registry.get_openapi_schemas()
            usage_examples = self.tool_registry.get_usage_examples()

            if openapi_schemas:
                schemas_json = json.dumps(openapi_schemas, indent=2)

                usage_examples_section = ""
                if usage_examples:
                    usage_examples_section = "\n\nUsage Examples:\n"
                    for func_name, example in usage_examples.items():
                        usage_examples_section += f"\n{func_name}:\n{example}\n"

                examples_content = f"""
In this environment you have access to a set of tools you can use to answer the user's question.

You can invoke functions by writing a <function_calls> block like the following as part of your reply to the user:

<function_calls>
<invoke name="function_name">
<parameter name="param_name">param_value</parameter>
...
</invoke>
</function_calls>

String and scalar parameters should be specified as-is, while lists and objects should use JSON format.

Here are the functions available in JSON Schema format:

```json
{schemas_json}
When using the tools:

Use the exact function names from the JSON schema above

Include all required parameters as specified in the schema

Format complex data (objects, arrays) as JSON strings within the parameter tags

Boolean values should be "true" or "false" (lowercase)
{usage_examples_section}"""

                system_content = working_system_prompt.get('content')
                if isinstance(system_content, str):
                    working_system_prompt['content'] += examples_content
                    logger.info("Appended XML examples to system prompt")

        try:
            # 1. Récupérer les messages du thread
            messages = await self.get_llm_messages(thread_id)

            # 2. Préparer les messages pour Ollama
            prepared_messages = [working_system_prompt] + messages

            logger.info(f"Prepared {len(prepared_messages)} messages for Ollama")

            # 3. Faire l'appel à Ollama
            if not self.ollama_client:
                raise Exception("Ollama client not initialized")

            logger.info("Making Ollama API call")
            ollama_response = await self.ollama_client.chat.completions.create(
                model=llm_model,
                messages=prepared_messages,
                temperature=llm_temperature,
                max_tokens=llm_max_tokens,
                stream=stream
            )

            # 4. Traiter la réponse avec le ResponseProcessor
            if stream:
                logger.info("Processing streaming response from Ollama")
                response_generator = self.response_processor.process_streaming_response(  
                    llm_response=ollama_response,  
                    thread_id=thread_id,  
                    config=processor_config  
                )

                async for chunk in response_generator:
                    yield chunk
            else:
                logger.info("Processing non-streaming response from Ollama")
                response_generator = self.response_processor.process_streaming_response(  
                    llm_response=ollama_response,  
                    thread_id=thread_id,  
                    config=processor_config  
                )
                async for chunk in response_generator:
                    yield chunk

        except Exception as e:
            logger.error(f"Error in run_thread with Ollama: {str(e)}", exc_info=True)
            yield {
                "type": "status",
                "status": "error",
                "message": f"Erreur Ollama: {str(e)}"
            }

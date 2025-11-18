import base64  
import io  
import traceback  
from fastapi import APIRouter, HTTPException, Depends, Request    
from fastapi.responses import StreamingResponse    
from pydantic import BaseModel    
from typing import List, Optional, AsyncGenerator    
from datetime import datetime    
import uuid    
import json    
import re    
import asyncio
import structlog        
from models.conversation import VoiceMessageCreate
from tools.Condition_General_Search_Tool import ConditionsGeneralesTool
from services.supabase import DBConnection    
from services.redis import redis_service    
from utils.auth_utils import get_current_user_id_from_jwt    
from openai import AsyncOpenAI   # type: ignore  
from qdrant_client import QdrantClient   # type: ignore  
from langfuse import Langfuse   # type: ignore  
from core.config import config    
from qdrant_client.http.models import Filter, FieldCondition, MatchValue  
from qdrant_client.models import Filter, FieldCondition, MatchValue  
from tools.Product_mapping_tool import ProductMappingTool

# 👉 On n'importe plus SentenceTransformer directement ici
from utils.embedding_model import embedding_model   # ✅ centralisation du modèle
from typing import Optional  
try:  
    from langfuse.client import StatefulTraceClient  
except ImportError:  
    StatefulTraceClient = None
router = APIRouter(prefix="/chat", tags=["chat"])    
logger = structlog.get_logger()    

# try:  
#     embedding_model = SentenceTransformer('intfloat/multilingual-e5-large')  
#     logger.info("SentenceTransformer model loaded successfully")  
# except Exception as e:  
#     logger.warning(f"Failed to load SentenceTransformer: {e}")  
#     embedding_model = None

# Modèles    
class MessageCreate(BaseModel):    
    content: str    
    metadata: dict = {}    
    
class MessageResponse(BaseModel):    
    message_id: str    
    conversation_id: str    
    role: str  # "user" ou "assistant"    
    content: str    
    timestamp: datetime    
    metadata: dict    
    
class ChatRequest(BaseModel):    
    message: str    
    stream: bool = True    
    metadata: dict = {}    
  
db = None    
    
def initialize(_db: DBConnection):    
    """Initialize with database connection from main API."""    
    global db    
    db = _db  

ollama_client = AsyncOpenAI(    
    base_url=config.OLLAMA_BASE_URL + "/v1",    
    api_key="ollama"  # Clé factice pour Ollama    
)    

openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=config.OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://bhassurance.com",  # Required by OpenRouter
        "X-Title": "BH Assurance Chat",               # Optional
    }
)
    
try:    
    qdrant_client = QdrantClient(    
        host=config.QDRANT_HOST,    
        port=config.QDRANT_PORT    
    )    
except Exception as e:    
    logger.warning(f"Failed to initialize Qdrant client: {e}")    
    qdrant_client = None    
    
try:    
    langfuse = Langfuse(    
        public_key=config.LANGFUSE_PUBLIC_KEY,    
        secret_key=config.LANGFUSE_SECRET_KEY,    
        host=config.LANGFUSE_HOST    
    )    
except Exception as e:    
    logger.warning(f"Failed to initialize Langfuse: {e}")    
    langfuse = None  
  
@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])    
async def get_messages(    
    conversation_id: str,     
    request: Request,     
    limit: int = 50,    
    user_id: str = Depends(get_current_user_id_from_jwt)    
):    
    """Récupérer l'historique des messages d'une conversation"""    
    try:    
        client = await db.client    
            
        # Vérifier que l'utilisateur a accès à cette conversation    
        conv_result = await client.table('conversations').select('*').eq('conversation_id', conversation_id).eq('user_id', user_id).execute()    
            
        if not conv_result.data:    
            raise HTTPException(status_code=404, detail="Conversation not found")    
            
        # Récupérer les messages depuis Supabase    
        messages_result = await client.table('messages').select('*').eq('conversation_id', conversation_id).order('timestamp', desc=False).limit(limit).execute()    
            
        messages = []    
        for msg in messages_result.data:    
            # Gérer le format de timestamp    
            timestamp_str = msg['timestamp']    
            if timestamp_str.endswith('Z'):    
                timestamp_str = timestamp_str.replace('Z', '+00:00')    
                
            messages.append(MessageResponse(    
                message_id=msg['message_id'],    
                conversation_id=msg['conversation_id'],    
                role=msg['role'],    
                content=msg['content'],    
                timestamp=datetime.fromisoformat(timestamp_str),    
                metadata=msg.get('metadata', {})    
            ))    
            
        logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")    
        return messages    
            
    except HTTPException:    
        raise    
    except Exception as e:    
        logger.error(f"Error fetching messages: {str(e)}")    
        raise HTTPException(status_code=500, detail="Failed to fetch messages")    
  





@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)  
async def send_message(  
    conversation_id: str,  
    message_data: MessageCreate,  
    request: Request,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Version sans streaming avec réponse unique"""  
    try:  
        client = await db.client  
          
        # Vérifier l'accès  
        conv = await client.table('conversations').select('*').eq('conversation_id', conversation_id).eq('user_id', user_id).execute()  
        if not conv.data:  
            raise HTTPException(status_code=404, detail="Conversation not found")  
  
        # Récupérer le REF_PERSONNE de l'utilisateur  
        client_ref = 12169  
        now = datetime.utcnow()  
          
        # Enregistrer message utilisateur  
        user_message_id = str(uuid.uuid4())  
        await client.table('messages').insert({  
            'message_id': user_message_id,  
            'conversation_id': conversation_id,  
            'role': 'user',  
            'content': message_data.content,  
            'timestamp': now.isoformat(),  
            'metadata': message_data.metadata  
        }).execute()  
  
        # Générer une seule réponse complète avec filtrage par client  
        rag_context = await perform_rag_search(message_data.content, client_ref)  
        history = await redis_service.get_conversation_history(conversation_id, limit=10)  
        assistant_response = await generate_openrouter_response(message_data.content, rag_context, history)  
  
        # Enregistrer réponse assistant  
        assistant_message_id = str(uuid.uuid4())  
        await client.table('messages').insert({  
            'message_id': assistant_message_id,  
            'conversation_id': conversation_id,  
            'role': 'assistant',  
            'content': assistant_response,  
            'timestamp': datetime.utcnow().isoformat(),  
            'metadata': {  
                'rag_context': len(rag_context) if rag_context else 0,  
                'response_type': 'complete',  
                'client_ref': client_ref  
            }  
        }).execute()  
  
        return MessageResponse(  
            message_id=user_message_id,  
            conversation_id=conversation_id,  
            role="user",  
            content=message_data.content,  
            timestamp=now,  
            metadata=message_data.metadata  
        )  
  
    except Exception as e:  
        logger.error(f"Error in send_message: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to process message")  
  
# Import des outils  
from tools.create_devis_tool import CreateDevisTool    
from tools.rag_search_tool import RAGSearchTool  # Nouveau  
import re    
    
def is_simple_greeting(message: str) -> bool:  
    """Détecter si le message est une salutation simple"""  
    simple_greetings = [  
        "bonjour", "salut", "hello", "hi", "bonsoir",   
        "ça va", "ca va", "comment allez-vous", "comment ça va",  
        "merci", "au revoir", "bye", "à bientôt"  
    ]  
    message_lower = message.lower().strip()  
    return any(greeting in message_lower for greeting in simple_greetings)  
  
async def detect_and_execute_tools_with_tracing(  
    response_text: str,   
    client_ref: int,   
    message: str = "",   
    trace: Optional[StatefulTraceClient] = None  
) -> tuple[str, dict, dict]:  
    """  
    Détecter les appels d'outils dans la réponse, les exécuter et retourner les données pour le LLM.  
    Version avec tracing Langfuse complet.  
      
    Returns:  
        tuple: (cleaned_response_text, tool_results, tool_data_for_llm)  
    """  
    tool_results = {}  
    tool_data_for_llm = {}  
    devis_data = None  
  
    # Vérifier si search_conditions_generales a été utilisé pour les questions non-salutations  
    if message and not is_simple_greeting(message) and "search_conditions_generales" not in response_text:  
        # Créer un span pour l'exécution forcée  
        forced_span = None  
        if trace:  
            forced_span = trace.span(  
                name="execute_tool.search_conditions_generales_forced",  
                input={"tool_name": "search_conditions_generales", "query": message, "forced": True}  
            )  
          
        try:  
            tool_instance = ConditionsGeneralesTool(qdrant_client, ollama_client, embedding_model)  
            result = await tool_instance.search_conditions_generales(message, limit=5)  
              
            if result.success:  
                search_results = result.output.get("results", [])  
                metadata = result.output.get("metadata", {})  
                tool_data_for_llm["search_conditions_generales"] = {  
                    "query": message,  
                    "results": search_results,  
                    "metadata": metadata,  
                    "success": True,  
                    "forced": True  
                }  
                logger.info(f"Forced execution of search_conditions_generales with {len(search_results)} results")  
                  
                # Finaliser le span avec succès  
                if forced_span:  
                    forced_span.end(  
                        output={"success": True, "results_count": len(search_results)},  
                        status_message="tool_executed_forced"  
                    )  
            else:  
                if forced_span:  
                    forced_span.end(  
                        output={"success": False, "error": getattr(result, 'error', 'Unknown error')},  
                        status_message="tool_execution_failed"  
                    )  
                      
        except Exception as e:  
            logger.error(f"Error in forced execution of search_conditions_generales: {str(e)}")  
            if forced_span:  
                forced_span.end(  
                    status_message="tool_execution_error",  
                    level="ERROR",  
                    metadata={"error": str(e)}  
                )  
  
    # Patterns pour détection des outils inspirés de Suna  
    patterns = [  
        r'<function_calls>\s*<invoke name="([^"]+)">(.*?)</invoke>\s*</function_calls>',  
        r'<n_function_calls>\s*<invoke name="([^"]+)">(.*?)</invoke>\s*</function_calls>',  
        r'<invoke name="([^"]+)">(.*?)</invoke>',  
    ]  
      
    param_pattern = r'<parameter name="([^"]+)">([^<]*)</parameter>'  
      
    matches = []  
    used_pattern = None  
      
    for pattern in patterns:  
        matches = re.findall(pattern, response_text, re.DOTALL)  
        if matches:  
            used_pattern = pattern  
            break  
      
    if not matches:  
        response_text = re.sub(r'<function_calls>.*?</function_calls>', "", response_text, flags=re.DOTALL)  
        response_text = response_text.strip()  
        return response_text, tool_results, tool_data_for_llm  
      
    logger.info(f"Found {len(matches)} tool calls using pattern: {used_pattern}")  
    if trace:  
        trace.event(  
            name="tool_calls_parsed",  
            level="DEFAULT",  
            metadata={"tool_count": len(matches), "pattern_used": used_pattern}  
        )  
      
    for tool_name, params_text in matches:  
        # Créer un span pour chaque outil  
        span = None  
        if trace:  
            span = trace.span(  
                name=f"execute_tool.{tool_name}",  
                input={"tool_name": tool_name, "params_text": params_text[:200]}  
            )  
          
        try:  
            if tool_name == "search_rag":  
                params = {"client_ref": client_ref}  
                param_matches = re.findall(param_pattern, params_text)  
                  
                for param_name, param_value in param_matches:  
                    if param_name == "limit":  
                        params[param_name] = int(param_value.strip())  
                    elif param_name == "client_ref":  
                        params[param_name] = int(param_value.strip())  
                    else:  
                        params[param_name] = param_value.strip()  
                  
                tool_instance = RAGSearchTool(db, qdrant_client, ollama_client)  
                result = await tool_instance.search_rag(**params)  
                tool_results[tool_name] = result  
                  
                if result.success:  
                    search_results = result.output.get("results", {"client_data": [], "faq_data": []})  
                    statistics = result.output.get("statistics", {})  
                      
                    tool_data_for_llm[tool_name] = {  
                        "query": params.get("query", ""),  
                        "client_data": search_results.get("client_data", []),  
                        "faq_data": search_results.get("faq_data", []),  
                        "statistics": statistics,  
                        "success": True  
                    }  
                      
                    # Finaliser le span avec succès  
                    if span:  
                        span.end(  
                            output={  
                                "success": True,   
                                "client_results": len(search_results.get("client_data", [])),  
                                "faq_results": len(search_results.get("faq_data", []))  
                            },  
                            status_message="tool_executed"  
                        )  
                else:  
                    tool_data_for_llm[tool_name] = {  
                        "query": params.get("query", ""),  
                        "error": getattr(result, 'error', 'Erreur inconnue'),  
                        "success": False  
                    }  
                      
                    if span:  
                        span.end(  
                            output={"success": False, "error": getattr(result, 'error', 'Unknown error')},  
                            status_message="tool_execution_failed"  
                        )  
                  
                # Supprimer le bloc XML  
                replacement_patterns = [  
                    r'<function_calls>\s*<invoke name="search_rag">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',  
                    r'<n_function_calls>\s*<invoke name="search_rag">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',  
                    r'<invoke name="search_rag">.*?</invoke>(?:\s*</function_calls>)?'  
                ]  
                  
                for repl_pattern in replacement_patterns:  
                    if re.search(repl_pattern, response_text, re.DOTALL):  
                        response_text = re.sub(repl_pattern, "", response_text, flags=re.DOTALL)  
                        break  
  
            elif tool_name == "search_conditions_generales":  
                params = {}  
                param_matches = re.findall(param_pattern, params_text)  
                  
                for param_name, param_value in param_matches:  
                    if param_name == "limit":  
                        params[param_name] = int(param_value.strip())  
                    else:  
                        params[param_name] = param_value.strip()  
                  
                tool_instance = ConditionsGeneralesTool(qdrant_client, ollama_client, embedding_model)  
                result = await tool_instance.search_conditions_generales(**params)  
                tool_results[tool_name] = result  
                  
                logger.info(f"Conditions générales tool execution result: success={result.success}")  
                  
                if result.success:  
                    search_results = result.output.get("results", [])  
                    metadata = result.output.get("metadata", {})  
                      
                    tool_data_for_llm[tool_name] = {  
                        "query": params.get("query", ""),  
                        "results": search_results,  
                        "metadata": metadata,  
                        "success": True  
                    }  
                      
                    # Finaliser le span avec succès  
                    if span:  
                        span.end(  
                            output={"success": True, "results_count": len(search_results)},  
                            status_message="tool_executed"  
                        )  
                else:  
                    tool_data_for_llm[tool_name] = {  
                        "query": params.get("query", ""),  
                        "error": getattr(result, 'error', 'Erreur inconnue'),  
                        "success": False  
                    }  
                      
                    if span:  
                        span.end(  
                            output={"success": False, "error": getattr(result, 'error', 'Unknown error')},  
                            status_message="tool_execution_failed"  
                        )  
                  
                # Supprimer le bloc XML  
                replacement_patterns = [  
                    r'<function_calls>\s*<invoke name="search_conditions_generales">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',  
                    r'<n_function_calls>\s*<invoke name="search_conditions_generales">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',  
                    r'<invoke name="search_conditions_generales">.*?</invoke>(?:\s*</function_calls>)?'  
                ]  
                  
                for repl_pattern in replacement_patterns:  
                    if re.search(repl_pattern, response_text, re.DOTALL):  
                        response_text = re.sub(repl_pattern, "", response_text, flags=re.DOTALL)  
                        break  
  
            elif tool_name == "create_devis":  
                params = {"client_ref": client_ref}  
                param_matches = re.findall(param_pattern, params_text)  
                  
                for param_name, param_value in param_matches:  
                    value = param_value.strip()  
                      
                    if param_name == "client_ref":  
                        params["client_ref"] = int(value)  
                    elif param_name == "n_cin":  
                        params["n_cin"] = value  
                    elif param_name in ["valeur_venale", "valeur_a_neuf", "capital_bris_de_glace", "capital_dommage_collision"]:  
                        # Conversion robuste des valeurs numériques
                        try:
                            if value.isdigit():
                                params[param_name] = int(value)
                            else:
                                # Essayer de convertir en float puis en int
                                params[param_name] = int(float(value))
                        except (ValueError, TypeError):
                            logger.warning(f"Impossible de convertir {param_name}={value} en nombre")
                            params[param_name] = value
                    elif param_name in ["nombre_place", "puissance", "classe"]:  
                        try:
                            params[param_name] = int(value)
                        except (ValueError, TypeError):
                            logger.warning(f"Impossible de convertir {param_name}={value} en entier")
                            params[param_name] = value
                    elif param_name == "nature_contrat":  
                        params[param_name] = value  
                    elif param_name == "date_premiere_mise_en_circulation":  
                        try:  
                            if "/" in value:  
                                date_obj = datetime.strptime(value, "%d/%m/%Y")  
                            elif "-" in value and len(value.split("-")[0]) == 2:  
                                date_obj = datetime.strptime(value, "%d-%m-%Y")  
                            else:  
                                date_obj = datetime.strptime(value, "%Y-%m-%d")  
                            params[param_name] = date_obj.strftime("%Y-%m-%d")  
                        except Exception as e:  
                            logger.error(f"Erreur format date pour {param_name}={value}: {e}")  
                            params[param_name] = value  
                    else:  
                        params[param_name] = value  
                  
                tool_instance = CreateDevisTool(db)  
                result = await tool_instance.create_devis(**params)  
                tool_results[tool_name] = result  
                  
                if result.success:  
                    devis_output = result.output  
                    devis_id = None  
                      
                    if isinstance(devis_output, dict):  
                        devis_id = devis_output.get('devis_id')  
                    elif hasattr(result, 'devis_id'):  
                        devis_id = result.devis_id  
                      
                    tool_data_for_llm[tool_name] = {  
                        "devis_id": devis_id,  
                        "devis_data": devis_output,  
                        "success": True,  
                        "action": "devis_created"  
                    }  
                      
                    # Finaliser le span avec succès  
                    if span:  
                        span.end(  
                            output={"success": True, "devis_id": devis_id},  
                            status_message="tool_executed"  
                        )  
                else:  
                    tool_data_for_llm[tool_name] = {  
                        "error": getattr(result, 'error', 'Erreur inconnue'),  
                        "success": False  
                    }  
                      
                    if span:  
                        span.end(  
                            output={"success": False, "error": getattr(result, 'error', 'Unknown error')},  
                            status_message="tool_execution_failed"  
                        )  
                  
                # Supprimer le bloc XML  
                replacement_patterns = [  
                    r'<function_calls>\s*<invoke name="create_devis">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',  
                    r'<n_function_calls>\s*<invoke name="create_devis">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',  
                    r'<invoke name="create_devis">.*?</invoke>(?:\s*</function_calls>)?'  
                ]  
                  
                for repl_pattern in replacement_patterns:  
                    if re.search(repl_pattern, response_text, re.DOTALL):  
                        response_text = re.sub(repl_pattern, "", response_text, flags=re.DOTALL)  
                        break
            elif tool_name == "search_product_mapping":  
                params = {}  
                param_matches = re.findall(param_pattern, params_text)  
                  
                for param_name, param_value in param_matches:  
                    if param_name == "limit":  
                        params[param_name] = int(param_value.strip())  
                    else:  
                        params[param_name] = param_value.strip()  
                  
                tool_instance = ProductMappingTool(qdrant_client, ollama_client, embedding_model)  
                result = await tool_instance.search_product_mapping(**params)  
                tool_results[tool_name] = result  
                  
                if result.success:  
                    search_results = result.output.get("results", [])  
                    metadata = result.output.get("metadata", {})  
                      
                    tool_data_for_llm[tool_name] = {  
                        "query": params.get("query", ""),  
                        "results": search_results,  
                        "metadata": metadata,  
                        "success": True  
                    }  
                      
                    # Finaliser le span avec succès  
                    if span:  
                        span.end(  
                            output={"success": True, "results_count": len(search_results)},  
                            status_message="tool_executed"  
                        )  
                else:  
                    tool_data_for_llm[tool_name] = {  
                        "query": params.get("query", ""),  
                        "error": getattr(result, 'error', 'Erreur inconnue'),  
                        "success": False  
                    }  
                      
                    if span:  
                        span.end(  
                            output={"success": False, "error": getattr(result, 'error', 'Unknown error')},  
                            status_message="tool_execution_failed"  
                        )  
                  
                # Supprimer le bloc XML  
                replacement_patterns = [  
                    r'<function_calls>\s*<invoke name="search_product_mapping">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',  
                    r'<n_function_calls>\s*<invoke name="search_product_mapping">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',  
                    r'<invoke name="search_product_mapping">.*?</invoke>(?:\s*</function_calls>)?'  
                ]  
                  
                for repl_pattern in replacement_patterns:  
                    if re.search(repl_pattern, response_text, re.DOTALL):  
                        response_text = re.sub(repl_pattern, "", response_text, flags=re.DOTALL)  
                        break  
                          
        except Exception as e:  
            logger.error(f"Error executing tool {tool_name}: {str(e)}")  
            tool_results[tool_name] = {"success": False, "error": str(e)}  
            tool_data_for_llm[tool_name] = {  
                "error": str(e),  
                "success": False  
            }  
              
            # Finaliser le span avec erreur  
            if span:  
                span.end(  
                    status_message="tool_execution_error",  
                    level="ERROR",  
                    metadata={"error": str(e)}  
                )  
              
            # Supprimer le XML même en cas d'erreur  
            response_text = re.sub(r'<function_calls>.*?</function_calls>', "", response_text, flags=re.DOTALL)  
  
    # Nettoyer la réponse de tout XML restant  
    response_text = re.sub(r'<function_calls>.*?</function_calls>', "", response_text, flags=re.DOTALL)  
    response_text = response_text.strip()  
      
    logger.info(f"Tool execution completed. Tools executed: {list(tool_data_for_llm.keys())}")  
      
    # Event final pour completion des outils  
    if trace:  
        trace.event(  
            name="tool_execution_completed",  
            level="DEFAULT",  
            metadata={  
                "tools_executed": list(tool_data_for_llm.keys()),  
                "total_tools": len(tool_data_for_llm)  
            }  
        )  
      
    return response_text, tool_results, tool_data_for_llm







@router.get("/devis/{devis_id}/pdf")  
async def download_devis_pdf(  
    devis_id: str,  
):  
    """Télécharger le PDF d'un devis à partir de Supabase."""  
    try:  
        logger.info(f"🔍 Recherche du devis: {devis_id}")  
  
        client = await db.client  
  
        # Recherche uniquement par devis_id  
        result = await client.table("devis").select("*").eq("devis_id", devis_id).execute()  
        logger.info(f"📦 Résultat par devis_id: {len(result.data)} résultat(s)")  
  
        if not result.data:  
            logger.error(f"❌ Devis {devis_id} non trouvé dans la base")  
            raise HTTPException(status_code=404, detail="Devis not found")  
  
        devis = result.data[0]  
        logger.info(f"✅ Devis trouvé: {devis.get('devis_id')}")  
  
        # Vérifier le champ PDF  
        pdf_content = devis.get("pdf_content") or devis.get("pdf_data") or devis.get("content")  
        if not pdf_content:  
            logger.error(f"❌ PDF content manquant pour le devis {devis_id}")  
            logger.error(f"📋 Champs disponibles: {list(devis.keys())}")  
            raise HTTPException(status_code=404, detail="PDF content not available")  
  
        # Décodage du PDF  
        try:  
            if isinstance(pdf_content, str) and pdf_content.startswith("data:application/pdf;base64,"):  
                logger.info("📄 Format détecté: data URI base64")  
                pdf_bytes = base64.b64decode(pdf_content.split(",")[1])  
            elif isinstance(pdf_content, str):  
                logger.info("📄 Format détecté: base64 simple")  
                pdf_bytes = base64.b64decode(pdf_content)  
            else:  
                logger.info("📄 Format détecté: bytes")  
                pdf_bytes = pdf_content  
  
            logger.info(f"✅ PDF décodé, taille: {len(pdf_bytes)} bytes")  
  
        except Exception as decode_error:  
            logger.error(f"❌ Erreur décodage PDF: {decode_error}")  
            logger.error(f"🔍 Extrait du content: {str(pdf_content)[:100]}...")  
            raise HTTPException(status_code=500, detail="Invalid PDF format")  
  
        # Retour du PDF  
        return StreamingResponse(  
            io.BytesIO(pdf_bytes),  
            media_type="application/pdf",  
            headers={  
                "Content-Disposition": f"attachment; filename=devis_{devis_id}.pdf",  
                "Content-Length": str(len(pdf_bytes)),  
            },  
        )  
  
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"❌ Erreur inattendue: {str(e)}")  
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")  
        raise HTTPException(status_code=500, detail="Failed to download PDF")  
  

async def generate_chat_response(  
    conversation_id: str,  
    message: str,  
    user_id: str,  
    use_rag: bool = True  
) -> AsyncGenerator[str, None]:  
    trace = None  
    generation = None  
    full_response = ""  
    chunk_count = 0  
    client_ref = 12169  
    accumulated_content = ""  
    in_function_calls = False  
    function_calls_depth = 0  
    last_sent_position = 0  
    has_executed_tools = False  
    final_response = ""  
    tool_data_for_llm = {}  # ← Déjà ajouté  
    devis_data = None       # ← Ajouter cette ligne  
      
    try:   
        # 1. Initialiser tracing Langfuse avec input  
        if langfuse:  
            try:  
                trace = langfuse.trace(  
                    name="streaming_chat",  
                    user_id=user_id,  
                    input=message,  # ← Ajouter l'input comme Suna  
                    metadata={  
                        "conversation_id": conversation_id,  
                        "streaming": True,  
                        "client_ref": client_ref,  
                        "use_rag": use_rag  
                    }  
                )  
                # Créer une génération pour le LLM call  
                generation = trace.generation(  
                    name="chat_completion",  
                    model="deepseek/deepseek-chat-v3.1:free"  
                )  
            except Exception as e:  
                logger.warning(f"Langfuse tracing failed: {e}")  
  
        client = await db.client  
  
        # 2. Event pour RAG search  
        if use_rag and trace:  
            trace.event(name="rag_search_started", level="DEFAULT")  
  
        # Recherche RAG initiale si activée  
        rag_context = []  
        total_contrats = 0  
        total_sinistres = 0  
        montant_total_sinistres = 0.0  
        context_text = ""  
  
        if use_rag:  
            try:  
                rag_tool = RAGSearchTool(db, qdrant_client, openrouter_client)  
                rag_result = await rag_tool.search_rag(message, client_ref, limit=20)  
                  
                # Event pour résultat RAG  
                if trace:  
                    trace.event(  
                        name="rag_search_completed",  
                        level="DEFAULT",  
                        metadata={  
                            "success": rag_result.success,  
                            "results_count": len(rag_result.output.get("results", {}).get("client_data", [])) if rag_result.success else 0  
                        }  
                    )  
                  
                if rag_result.success:  
                    rag_context_structured = rag_result.output.get("results", {"client_data": [], "faq_data": []})  
                    stats = rag_result.output.get("statistics", {})  
                    total_contrats = stats.get("total_contrats", 0)  
                    total_sinistres = stats.get("total_sinistres", 0)  
                    montant_total_sinistres = stats.get("montant_total_sinistres", 0.0)  
                else:  
                    rag_context_structured = {"client_data": [], "faq_data": []}  
  
                # Construire le contexte initial  
                context_text = _build_context_text(rag_context_structured)  
  
            except Exception as e:  
                logger.warning(f"RAG search failed: {e}")  
                if trace:  
                    trace.event(  
                        name="rag_search_failed",  
                        level="WARNING",  
                        metadata={"error": str(e)}  
                    )  
                context_text = ""  
  
        # Prompt système initial  
            system_prompt = f"""
Tu es un Assistant IA, **expert membre de l'équipe BH Assurance**, spécialisé dans toutes les branches : Automobile, Engineering, Santé, Vie, Transport et IARD.

# RÈGLES STRICTES
- Répondre DIRECTEMENT et EXPLICATIVEMENT à toutes les questions d'assurance.
- UTILISER OBLIGATOIREMENT search_conditions_generales pour toute question d'assurance,
  sauf dans deux cas :
  1. Demande explicite de génération d’un devis auto
  2. Demande des informations nécessaires à l’établissement d’un devis auto
- create_devis : utilisé uniquement sur demande explicite de devis auto, après collecte et validation de toutes les informations obligatoires.
- NE JAMAIS dire à l'utilisateur d'aller consulter ses conditions générales, un site web ou un document externe.
- NE JAMAIS répondre par des phrases vagues ou incomplètes (ex: "cela dépend…" ou "consultez vos conditions…").
- EXPLIQUER toujours de manière claire, complète et pédagogique.
- UTILISER OBLIGATOIREMENT le format XML pour tous les appels aux outils.
- VALIDER toutes les informations avant de générer un devis.

# CRITÈRES DE VALIDATION POUR LES DEVIS
Avant d'appeler create_devis, vérifier que toutes les informations sont valides :
1. CIN : exactement 8 chiffres
2. Valeur vénale : nombre positif
3. Nature du contrat : 'r' (tous risques) ou 'a' (au tiers)
4. Nombre de places : entre 1 et 9
5. Valeur à neuf : nombre positif
6. Date de première mise en circulation : format YYYY-MM-DD et date dans le passé
7. Capital bris de glace : nombre positif
8. Capital dommage collision : nombre positif
9. Puissance : nombre entre 1 et 10
10. Classe : nombre entre 1 et 18
Après réception des données depuis les outils, générer automatiquement un devis d’assurance en utilisant uniquement les informations fournies, répondre à la demande de l’utilisateur en s’appuyant sur ces données, et établir des liens entre elles si une relation existe (ex. CIN ↔ véhicule, garanties ↔ valeurs).
Si une information est invalide, demander spécifiquement la correction.

# OUTILS DISPONIBLES
- search_conditions_generales : recherche dans les conditions générales d'assurance.
- search_rag : recherche dans les données clients et FAQ.
- search_product_mapping : recherche de produits d'assurance adaptés aux besoins exprimés.
- create_devis : génération de devis automobile (uniquement sur demande explicite et après validation).

# INSTRUCTIONS D'UTILISATION DES OUTILS
- Pour toute question d'assurance :
  1. Appeler OBLIGATOIREMENT search_conditions_generales.
  2. Puis appeler search_rag avec le client_ref correspondant.
  3. Après réception des données, répondre à la question de l'utilisateur en s'appuyant sur les informations disponibles et établir automatiquement les liens entre les données lorsqu'une relation existe.
  4. La réponse finale doit être claire, détaillée et directement utile.

- Pour les demandes de devis :
  1. Vérifier que toutes les informations obligatoires sont présentes et valides
  2. Si des informations manquent ou sont invalides, demander spécifiquement les corrections
  3. Uniquement si toutes les informations sont valides, appeler create_devis

# FORMATS XML DES OUTILS

- Format XML search_conditions_generales :
<function_calls>
<invoke name="search_conditions_generales">
    <parameter name="query">votre requête de recherche</parameter>
</invoke>
</function_calls>

- Format XML search_rag :
<function_calls>
<invoke name="search_rag">
    <parameter name="query">votre requête de recherche</parameter>
    <parameter name="client_ref">{client_ref}</parameter>
    <parameter name="limit">10</parameter>
</invoke>
</function_calls>

- Format XML create_devis (uniquement après validation) :
<function_calls>
<invoke name="create_devis">
    <parameter name="client_ref">{client_ref}</parameter>
    <parameter name="n_cin">08478931</parameter>
    <parameter name="valeur_venale">60000</parameter>
    <parameter name="nature_contrat">r</parameter>
    <parameter name="nombre_place">5</parameter>
    <parameter name="valeur_a_neuf">60000</parameter>
    <parameter name="date_premiere_mise_en_circulation">2022-02-28</parameter>
    <parameter name="capital_bris_de_glace">900</parameter>
    <parameter name="capital_dommage_collision">60000</parameter>
    <parameter name="puissance">6</parameter>
    <parameter name="classe">3</parameter>
</invoke>
</function_calls>

- Format XML search_product_mapping :
<function_calls>  
<invoke name="search_product_mapping">  
<parameter name="query">description du besoin utilisateur</parameter>  
<parameter name="limit">3</parameter>  
</invoke>  
</function_calls>

# MESSAGES D'ERREUR SPÉCIFIQUES
- Si le CIN n'a pas 8 chiffres : "Le numéro de CIN doit contenir exactement 8 chiffres. Veuillez corriger."
- Si une valeur numérique est négative : "La valeur [nom du champ] doit être positive. Veuillez corriger."
- Si la date est dans le futur : "La date de première mise en circulation ne peut pas être dans le futur. Veuillez corriger."
- Si la nature du contrat n'est pas 'r' ou 'a' : "La nature du contrat doit être 'r' (tous risques) ou 'a' (au tiers). Veuillez corriger."

# MESSAGE STANDARD POUR INFORMATIONS MANQUANTES
Si des informations obligatoires manquent (sauf client_ref={client_ref}), répondre exactement :
"Pour établir votre devis d'assurance automobile, j'ai besoin des informations suivantes :
1. CIN (8 chiffres)
2. Valeur vénale du véhicule (positive)
3. Nature du contrat ('r' pour tous risques, 'a' pour au tiers)
4. Nombre de places du véhicule (1-9)
5. Valeur à neuf (positive)
6. Date de première mise en circulation (format YYYY-MM-DD)
7. Capital bris de glace (positive)
8. Capital dommage collision (positive)
9. Puissance du véhicule (1-10)
10. Classe du véhicule (1-18)

Pouvez-vous me fournir ces informations ?"

# RAPPEL FINAL
- Toujours utiliser search_conditions_generales et search_rag pour toute question d'assurance.
- Utiliser create_devis uniquement sur demande explicite et après validation de toutes les informations.
- Valider scrupuleusement toutes les informations avant de générer un devis.
- Ne jamais renvoyer l'utilisateur vers un site, document ou autre ressource externe.
- Répondre de manière claire, détaillée et pédagogique.

# CONTEXTE ACTUEL
{context_text}
"""
 
        history = []  
        try:  
            history = await redis_service.get_conversation_history(conversation_id, limit=10)  
        except Exception as e:  
            logger.warning(f"Failed to fetch conversation history: {e}")  
  
        # Préparer les messages pour l'appel LLM  
        messages = [  
            {"role": "system", "content": system_prompt.strip()},  
            *[{"role": msg.get("role"), "content": msg.get("content")} for msg in history[-5:]],  
            {"role": "user", "content": message}  
        ]  
  
        # 3. Event avant LLM call  
        if trace:  
            trace.event(  
                name="llm_call_started",  
                level="DEFAULT",  
                metadata={  
                    "model": "deepseek/deepseek-chat-v3.1:free",  
                    "streaming": True,  
                    "message_count": len(messages)  
                }  
            )  
  
        # Mettre à jour la génération avec les messages  
        if generation:  
            generation.update(  
                input=messages,  
                model="deepseek/deepseek-chat-v3.1:free",  
                model_parameters={  
                    "temperature": 0.7,  
                    "max_tokens": 2000,  
                    "stream": True  
                }  
            )  
  
        # Premier appel LLM en streaming  
        logger.info(f"Starting streaming response for conversation {conversation_id}, client {client_ref}")  
        try:  
            stream = await openrouter_client.chat.completions.create(  
                model="deepseek/deepseek-chat-v3.1:free",  
                messages=messages,  
                temperature=0.7,  
                max_tokens=2000,  
                stream=True,  
                extra_headers={  
                    "HTTP-Referer": "https://bhassurance.com",  
                    "X-Title": "BH Assurance Chat",  
                    "X-Think": "false"  
                }  
            )  
        except Exception as e:  
            logger.error(f"Failed to create OpenRouter stream: {e}")  
            if trace:  
                trace.event(  
                    name="llm_call_failed",  
                    level="ERROR",  
                    metadata={"error": str(e)}  
                )  
            yield f"data: {json.dumps({'error': 'Failed to start stream', 'done': True})}\n\n"  
            return  
  
        has_sent_initial_response = False  
  
        # Streaming avec masquage XML inspiré de Suna  
        async for chunk in stream:  
            try:  
                if not chunk.choices or not chunk.choices[0].delta.content:  
                    continue  
                    
                content = chunk.choices[0].delta.content  
                full_response += content  
                accumulated_content += content  
                
                # Détecter les balises XML et masquer le contenu  
                while True:  
                    if not in_function_calls:  
                        start_pos = accumulated_content.find('<function_calls>', last_sent_position)  
                        if start_pos == -1:  
                            # Pas de balise détectée, envoyer le contenu  
                            content_to_send = accumulated_content[last_sent_position:]  
                            if content_to_send.strip():  
                                # Nettoyage léger qui préserve les espaces  
                                cleaned_content = content_to_send.replace('<invoke', ' <invoke').replace('</invoke>', '</invoke> ')  
                                
                                yield f"data: {json.dumps({'action': 'append','content': cleaned_content})}\n\n"  
                            
                            last_sent_position = len(accumulated_content)  
                            break  
                        else:  
                            # Balise détectée, envoyer seulement le contenu avant  
                            content_before = accumulated_content[last_sent_position:start_pos]  
                            if content_before.strip():  
                                yield f"data: {json.dumps({'action': 'append','content': content_before})}\n\n"  
                            
                            in_function_calls = True  
                            last_sent_position = start_pos  
                    else:  
                        # Chercher la fin de la balise  
                        end_pos = accumulated_content.find('</function_calls>', last_sent_position)  
                        if end_pos == -1:  
                            break  
                        else:  
                            last_sent_position = end_pos + len('</function_calls>')  
                            in_function_calls = False
                      
            except Exception as e:  
                logger.error(f"Error processing chunk: {e}")  
                continue  
  
        # Envoyer le contenu restant  
        if last_sent_position < len(accumulated_content) and not in_function_calls:  
            remaining_content = accumulated_content[last_sent_position:]  
            if remaining_content.strip():  
                yield f"data: {json.dumps({'action': 'append','content': remaining_content})}\n\n"  
  
        # Nettoyage de la réponse  
        clean_response = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL).strip()  
  
        # 4. Event pour tool detection  
        if ("create_devis" in clean_response or   
            "search_rag" in clean_response or   
            "search_conditions_generales" in clean_response or   
            "search_product_mapping" in clean_response or  
            "<function_calls>" in clean_response):  
              
            if trace:  
                trace.event(name="tool_calls_detected", level="DEFAULT")  
                  
            logger.info("Tool calls detected, executing and enriching context...")  
            clean_response, tool_results, tool_data_for_llm = await detect_and_execute_tools_with_tracing(  
                clean_response, client_ref, message, trace  
            )  
            has_executed_tools = True  
              
            # Si des outils ont été exécutés, régénérer la réponse avec le contexte enrichi  
            if tool_data_for_llm:  
                if trace:  
                    trace.event(  
                        name="context_enrichment_started",  
                        level="DEFAULT",  
                        metadata={"tools_executed": list(tool_data_for_llm.keys())}  
                    )  
                  
                logger.info(f"Enriching context with tool data: {list(tool_data_for_llm.keys())}")  
                  
                # Construire le contexte enrichi  
                enriched_context = context_text  
                  
                for tool_name, data in tool_data_for_llm.items():  
                    if tool_name == "search_rag" and data.get("success"):  
                        client_data = data.get("client_data", [])  
                        faq_data = data.get("faq_data", [])  
                        query = data.get("query", "")  
                          
                        enriched_context += f"\n\n# Résultats de recherche pour: {query}\n"  
                        enriched_context += _format_tool_data_for_context(client_data, faq_data)  
                          
                    elif tool_name == "search_conditions_generales" and data.get("success"):  
                        results = data.get("results", {})  
                        query = data.get("query", "")  
  
                        enriched_context += f"\n\n# Résultats de recherche pour: {query}\n"  
  
                        # Résultats Conditions Générales  
                        cond_generales = results.get("conditions_generales", [])  
                        if cond_generales:  
                            enriched_context += "\n## Conditions Générales:\n"  
                            for r in cond_generales:  
                                enriched_context += f"- {r.get('text', '')[:200]}... (Branche: {r.get('branche', 'N/A')}, Source: {r.get('source', 'N/A')})\n"  
  
                        # Résultats FAQ  
                        faq_results = results.get("bh_faq", [])  
                        if faq_results:  
                            enriched_context += "\n## FAQ:\n"  
                            for r in faq_results:  
                                enriched_context += f"- Q: {r.get('question', 'N/A')} → {r.get('text', '')[:200]}... (Catégorie: {r.get('categorie', 'N/A')}, Source: {r.get('source', 'N/A')})\n"  
                          
                    elif tool_name == "create_devis" and data.get("success"):  
                        devis_data = {  
                            'devis_id': data.get('devis_id'),  
                            'success': True,  
                            'action': 'download_devis'  
                        }  
                        enriched_context += f"\n\n# Devis créé avec succès\nID: {data.get('devis_id')}\n"  
  
                    elif tool_name == "search_product_mapping" and data.get("success"):  
                        product_results = data.get("results", [])  
                        query = data.get("query", "")  
                          
                        enriched_context += f"\n\n# Produits recommandés pour: {query}\n"  
                        for product in product_results:  
                            enriched_context += f"- **{product.get('produit')}** ({product.get('branche')} - {product.get('sous_branche')})\n"  
                            enriched_context += f"  Score: {product.get('score', 0):.3f}\n"  
                            if product.get('text'):  
                                enriched_context += f"  {product.get('text')[:200]}...\n"  
                  
                # Régénérer la réponse avec le contexte enrichi  
                enriched_messages = [  
                    {"role": "system", "content": f"""  
Utilise ces informations pour répondre à la question de l'utilisateur de manière naturelle et professionnelle.  
  
{enriched_context}  
  
Instructions:  
- Utilise uniquement les informations fournies dans le contexte  
- Sois précis et utile  
- Ne mentionne pas les outils utilisés"""},  
                    {"role": "user", "content": message}  
                ]  
                  
                # Event pour enriched response  
                if trace:  
                    trace.event(  
                        name="enriched_llm_call_started",  
                        level="DEFAULT",  
                        metadata={"enriched_context_length": len(enriched_context)}  
                    )  
                  
                # Nouvel appel LLM avec le contexte enrichi  
                try:  
                    enriched_stream = await openrouter_client.chat.completions.create(  
                        model="deepseek/deepseek-chat-v3.1:free",  
                        messages=enriched_messages, 
                        temperature=0.7,  
                        max_tokens=2000,  
                        stream=True,  
                        extra_headers={  
                            "HTTP-Referer": "https://bhassurance.com",  
                            "X-Title": "BH Assurance Chat",  
                            "X-Think": "false"  
                        }  
                    )  
                      
                    # Streamer la nouvelle réponse enrichie  
                    enriched_response = ""  
                    async for enriched_chunk in enriched_stream:  
                        if enriched_chunk.choices and enriched_chunk.choices[0].delta.content:  
                            enriched_content = enriched_chunk.choices[0].delta.content  
                            enriched_response += enriched_content  
                            yield f"data: {json.dumps({'action': 'append','content': enriched_content})}\n\n"  
                      
                    # Utiliser la réponse enrichie comme réponse finale  
                    final_response = enriched_response.strip()  
                      
                    if trace:  
                        trace.event(  
                            name="enriched_response_completed",  
                            level="DEFAULT",  
                            metadata={"response_length": len(final_response)}  
                        )  
                      
                except Exception as e:  
                    logger.error(f"Failed to generate enriched response: {e}")  
                    if trace:  
                        trace.event(  
                            name="enriched_response_failed",  
                            level="ERROR",  
                            metadata={"error": str(e)}  
                        )  
                    # Fallback sur la réponse originale nettoyée  
                    final_response = clean_response  
            else:  
                final_response = clean_response  
        else:  
            final_response = clean_response  
  
        # 5. Finaliser la génération  
        if generation:  
            generation.end(  
                output=final_response,  
                metadata={  
                    "chunk_count": chunk_count,  
                    "tools_executed": list(tool_data_for_llm.keys()) if tool_data_for_llm else [],  
                    "has_executed_tools": has_executed_tools  
                }  
            )  
  
        # Métadonnées pour la sauvegarde  
        metadata_update = {  
            'rag_context_items': len(rag_context),  
            'chunk_count': chunk_count,  
            'streaming': True,  
            'client_ref': client_ref,  
            'total_contrats': total_contrats,  
            'total_sinistres': total_sinistres,  
            'montant_total_sinistres': montant_total_sinistres,  
            'tools_executed': list(tool_data_for_llm.keys()) if tool_data_for_llm else [],  
            'devis_data': devis_data,  
            'has_executed_tools': has_executed_tools  
        }  
  
        # Sauvegarde en base de données  
        try:  
            assistant_message_id = str(uuid.uuid4())  
            await client.table('messages').insert({  
                'message_id': assistant_message_id,  
                'conversation_id': conversation_id,  
                'role': 'assistant',  
                'content': final_response,  
                'timestamp': datetime.utcnow().isoformat(),  
                'metadata': metadata_update  
            }).execute()  
  
            # Ajouter à l'historique Redis  
            await redis_service.add_message_to_history(conversation_id, {  
                'role': 'assistant',  
                'content': final_response,  
                'timestamp': datetime.utcnow().isoformat()  
            })  
  
        except Exception as e:  
            logger.error(f"Failed to save assistant message: {e}")  
            if trace:  
                trace.event(  
                    name="message_save_failed",  
                    level="ERROR",  
                    metadata={"error": str(e)}  
                )  
  
        # Signal de fin de streaming  
        yield f"data: {json.dumps({  
            'action': 'complete',  
            'message_id': assistant_message_id,  
            'metadata': metadata_update  
        })}\n\n"  
  
        logger.info(  
            f"Completed streaming for conversation {conversation_id} "  
            f"({chunk_count} chunks), client {client_ref}, "  
            f"tools executed: {list(tool_data_for_llm.keys()) if tool_data_for_llm else []}"  
        )  
  
    except Exception as e:  
        logger.error(f"Error in generate_chat_response: {str(e)}", exc_info=True)  
        if trace:  
            trace.event(  
                name="generate_chat_response_error",  
                level="ERROR",  
                metadata={"error": str(e)}  
            )  
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"  
  
    finally:  
        # 6. Finaliser la trace  
        if trace:  
            try:  
                trace.update(  
                    output=final_response if final_response else full_response,  
                    status_message="COMPLETED",  
                    metadata={  
                        'chunk_count': chunk_count,  
                        'tools_executed': list(tool_data_for_llm.keys()) if tool_data_for_llm else [],  
                        'client_ref': client_ref,  
                        'has_executed_tools': has_executed_tools,  
                        'final_length': len(final_response) if final_response else len(full_response)  
                    }  
                )  
            except Exception as e:  
                logger.warning(f"Failed to update trace: {e}")














def _build_context_text(rag_context_structured: dict) -> str:  
    """Construire le texte de contexte à partir des données RAG structurées."""  
    client_chunks = rag_context_structured.get("client_data", [])[:100]  
    faq_chunks = rag_context_structured.get("faq_data", [])[:5]  
      
    # Construire le contexte client  
    context_client_list = []  
    for chunk in client_chunks:  
        if chunk and isinstance(chunk, dict):  
            # Contrats  
            for c in chunk.get("contrats", []):  
                context_client_list.append(  
                    f"## Contrat {c.get('NUM_CONTRAT', 'non renseigné')}\n"  
                    f"Produit: {c.get('LIB_PRODUIT', 'non renseigné')}\n"  
                    f"État: {c.get('LIB_ETAT_CONTRAT', 'non renseigné')}\n"  
                    f"Capital assuré: {c.get('Capital_assure', 'non renseigné')}\n"  
                    f"Paiement: {c.get('statut_paiement', 'non renseigné')}"  
                )  
  
            # Garanties  
            for g in chunk.get("garanties", []):  
                context_client_list.append(  
                    f"## Garantie (Contrat {g.get('NUM_CONTRAT', 'non renseigné')})\n"  
                    f"{g.get('LIB_GARANTIE', 'non renseigné')}, "  
                    f"capital assuré: {g.get('CAPITAL_ASSURE', 'non renseigné')}"  
                )  
  
            # Sinistres  
            for s in chunk.get("sinistres", []):  
                context_client_list.append(  
                    f"## Sinistre {s.get('NUM_SINISTRE', 'non renseigné')}\n"  
                    f"Contrat: {s.get('NUM_CONTRAT', 'non renseigné')}\n"  
                    f"Type: {s.get('LIB_TYPE_SINISTRE', 'non renseigné')}\n"  
                    f"État: {s.get('LIB_ETAT_SINISTRE', 'non renseigné')}\n"  
                    f"Montant à encaisser: {s.get('MONTANT_A_ENCAISSER', 0)}"  
                )  
  
            # Infos client si aucun contrat/sinistre  
            if not chunk.get("contrats") and not chunk.get("sinistres"):  
                client_info = chunk.get("client_info", {})  
                context_client_list.append(  
                    f"## Infos client\n"  
                    f"Client: {client_info.get('RAISON_SOCIALE', 'non renseignée')}\n"  
                    f"Activité: {client_info.get('LIB_SECTEUR_ACTIVITE', 'non renseigné')}"  
                )  
  
    # Construire le contexte FAQ  
    context_faq_list = []  
    for f in faq_chunks:  
        context_faq_list.append(f"## FAQ\n{f.get('text', '')}")  
  
    # Concaténer contexte final avec sections séparées  
    context_sections = []  
    if context_client_list:  
        context_sections.append("# Données client\n" + "\n".join(context_client_list))  
    if context_faq_list:  
        context_sections.append("# FAQ / Support\n" + "\n".join(context_faq_list))  
  
    return "\n\n".join(context_sections).strip()  
  
def _format_tool_data_for_context(client_data: list, faq_data: list, product_data: list = None) -> str:  
    """Formater les données des outils pour le contexte LLM."""  
    formatted_sections = []  
      
    # Formater les données client  
    if client_data:  
        client_section = "## Données client trouvées\n"  
        for chunk in client_data:  
            if chunk and isinstance(chunk, dict):  
                # Contrats  
                for c in chunk.get("contrats", []):  
                    client_section += f"- Contrat {c.get('NUM_CONTRAT')}: {c.get('LIB_PRODUIT')} ({c.get('LIB_ETAT_CONTRAT')})\n"  
                  
                # Sinistres  
                for s in chunk.get("sinistres", []):  
                    client_section += f"- Sinistre {s.get('NUM_SINISTRE')}: {s.get('LIB_TYPE_SINISTRE')} - {s.get('LIB_ETAT_SINISTRE')}\n"  
                  
                # Garanties  
                for g in chunk.get("garanties", []):  
                    client_section += f"- Garantie: {g.get('LIB_GARANTIE')} (Capital: {g.get('CAPITAL_ASSURE')})\n"  
          
        formatted_sections.append(client_section)  
      
    # Formater les données FAQ  
    if faq_data:  
        faq_section = "## FAQ pertinente\n"  
        for faq in faq_data:  
            if faq and isinstance(faq, dict):  
                faq_section += f"- {faq.get('text', '')}\n"  
          
        formatted_sections.append(faq_section)
    
    # Formater les données de mapping produits
    if product_data:
        product_section = "## Produits d'assurance recommandés\n"
        for product in product_data:
            if product and isinstance(product, dict):
                product_section += f"- **{product.get('produit', 'N/A')}** ({product.get('branche', 'N/A')} - {product.get('sous_branche', 'N/A')})\n"
                product_section += f"  Score: {product.get('score', 0):.3f}\n"
                if product.get('text'):
                    product_section += f"  Description: {product.get('text', '')[:150]}...\n"
        
        formatted_sections.append(product_section)
      
    return "\n\n".join(formatted_sections)



















  
@router.post("/conversations/{conversation_id}/stream")    
async def stream_chat(     
    conversation_id: str,     
    chat_request: ChatRequest,    
    request: Request,    
    user_id: str = Depends(get_current_user_id_from_jwt)    
):    
    """Envoyer un message et recevoir une réponse en streaming"""    
    try:    
        client = await db.client    
            
        # Vérifier l'accès à la conversation    
        conv_result = await client.table('conversations').select('*').eq('conversation_id', conversation_id).eq('user_id', user_id).execute()    
            
        if not conv_result.data:    
            raise HTTPException(status_code=404, detail="Conversation not found")    
            
        # Sauvegarder le message utilisateur  
        user_message_id = str(uuid.uuid4())  
        await client.table('messages').insert({  
            'message_id': user_message_id,  
            'conversation_id': conversation_id,  
            'role': 'user',  
            'content': chat_request.message,  
            'timestamp': datetime.utcnow().isoformat(),  
            'metadata': chat_request.metadata  
        }).execute()  
  
        # Mode streaming uniquement  
        return StreamingResponse(    
            generate_chat_response(conversation_id, chat_request.message, user_id),    
            media_type="text/event-stream",    
            headers={    
                "Cache-Control": "no-cache",    
                "Connection": "keep-alive",    
                "X-Message-ID": user_message_id  # Important pour la synchronisation  
            }    
        )    
            
    except HTTPException:    
        raise    
    except Exception as e:    
        logger.error(f"Error in stream chat: {str(e)}")    
        raise HTTPException(status_code=500, detail="Failed to process chat request")  
      
@router.delete("/conversations/{conversation_id}/messages/{message_id}")    
async def delete_message(    
    conversation_id: str,     
    message_id: str,     
    request: Request,    
    user_id: str = Depends(get_current_user_id_from_jwt)    
):    
    """Supprimer un message spécifique"""    
    try:    
        client = await db.client    
            
        # Vérifier l'accès à la conversation    
        conv_result = await client.table('conversations').select('*').eq('conversation_id', conversation_id).eq('user_id', user_id).execute()    
            
        if not conv_result.data:    
            raise HTTPException(status_code=404, detail="Conversation not found")    
            
        # Vérifier que le message existe et appartient à cette conversation    
        message_result = await client.table('messages').select('*').eq('message_id', message_id).eq('conversation_id', conversation_id).execute()    
            
        if not message_result.data:    
            raise HTTPException(status_code=404, detail="Message not found")    
            
        # Supprimer le message    
        delete_result = await client.table('messages').delete().eq('message_id', message_id).execute()    
            
        if not delete_result.data:    
            raise HTTPException(status_code=500, detail="Failed to delete message")    
            
        # Supprimer de l'historique Redis si présent    
        try:    
            # Note: Redis stocke l'historique comme une liste,     
            # la suppression d'un message spécifique nécessiterait une reconstruction    
            # Pour simplifier, on peut juste laisser Redis se synchroniser naturellement    
            logger.info(f"Message {message_id} deleted from conversation {conversation_id}")    
        except Exception as redis_error:    
            logger.warning(f"Failed to update Redis after message deletion: {redis_error}")    
            
        return {"message": "Message deleted successfully", "message_id": message_id}    
            
    except HTTPException:    
        raise    
    except Exception as e:    
        logger.error(f"Error deleting message: {str(e)}")    
        raise HTTPException(status_code=500, detail="Failed to delete message")    
    
  

@router.post("/debug/test-search")  
async def test_search(  
    request: dict  
):  
    """Test manuel de recherche"""  
    try:  
        query = request.get("query", "assurance")  
        client_ref = request.get("client_ref", 12169)  
          
        # Générer l'embedding  
        embedding_response = await ollama_client.embeddings.create(  
            model="nomic-embed-text",  
            input=query  
        )  
        query_vector = embedding_response.data[0].embedding  
          
        # Construire le filtre  
        search_filter = Filter(  
            must=[FieldCondition(key="REF_PERSONNE", match=MatchValue(value=client_ref))]  
        )  
          
        # Essayer la recherche  
        search_results = qdrant_client.search(  
            collection_name="bh_assurance_clients_ollama",  
            query_vector=query_vector,  
            query_filter=search_filter,  
            limit=10  
        )  
          
        results = []  
        for result in search_results:  
            results.append({  
                "score": result.score,  
                "id": result.id,  
                "payload": result.payload,  
                "payload_keys": list(result.payload.keys()) if result.payload else []  
            })  
          
        return {  
            "status": "success",  
            "query": query,  
            "client_ref": client_ref,  
            "results_count": len(results),  
            "results": results  
        }  
          
    except Exception as e:  
        return {"status": "error", "message": f"Search test failed: {str(e)}"}  
  
def clean_markdown_content(content: str) -> str:  
    """Nettoyer et formater le contenu en préservant les espaces"""  
    if not content:  
        return ""  
      
    # Remplacer les balises XML par un espace pour préserver la structure  
    content = re.sub(r'<function_calls>.*?</function_calls>', ' ', content, flags=re.DOTALL)  
    content = re.sub(r'<think>.*?</think>', ' ', content, flags=re.DOTALL)  
    content = re.sub(r'<invoke.*?</invoke>', ' ', content, flags=re.DOTALL)  
      
    # Normaliser les espaces multiples  
    content = re.sub(r'\s+', ' ', content)  
      
    # Améliorer la structure des sections  
    content = enhance_section_structure(content)  
      
    return content.strip()
def enhance_section_structure(content: str) -> str:
    """Améliorer la structure des sections avec des titres clairs"""
    # Standardiser les titres de sections
    section_patterns = [
        (r'(## Résultats de recherche pour:.*?\n)', r'\n## 🔍 Résultats de Recherche\n'),
        (r'(## Conditions Générales:)', r'\n## 📋 Conditions Générales\n'),
        (r'(## FAQ:)', r'\n## ❓ FAQ\n'),
        (r'(## Données client trouvées)', r'\n## 👤 Données Client\n'),
        (r'(## FAQ pertinente)', r'\n## ❓ Questions Fréquentes\n'),
        (r'(# Devis créé avec succès)', r'\n## 📄 Devis Créé\n'),
    ]
    
    for pattern, replacement in section_patterns:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    # Ajouter des séparateurs entre les sections principales
    content = re.sub(r'\n(## [^\n]+)\n', r'\n\n---\n\n\1\n', content)
    
    # Formater les listes pour une meilleure lisibilité
    content = format_lists(content)
    
    return content

def format_lists(content: str) -> str:
    """Améliorer le formatage des listes"""
    # Formater les listes à puces
    
    return content



def clean_assistant_response(content: str) -> str:
    """Nettoyer la réponse de l'assistant avec un formatage structuré"""
    if not content or not isinstance(content, str):
        return "" if content is None else str(content)
    
    # Supprimer les balises XML et les invoke blocks (insensible à la casse, DOTALL)
    cleaned_content = re.sub(r'(?is)<function_calls>.*?</function_calls>', '', content)
    cleaned_content = re.sub(r'(?is)<invoke.*?</invoke>', '', cleaned_content)
    
    # Supprimer les annotations techniques (insensible à la casse)
    cleaned_content = re.sub(r'(?i)\(Résultat du search_rag\)\s*', '', cleaned_content)
    cleaned_content = re.sub(r'(?i)\(Résultat des conditions générales\)\s*', '', cleaned_content)
    
    # Structurer le contenu avec des sections claires
    cleaned_content = structure_assistant_response(cleaned_content)
    
    return cleaned_content.strip()

def structure_assistant_response(content: str) -> str:
    """Structurer la réponse de l'assistant avec des sections organisées"""
    # Détecter et organiser les sections naturelles
    sections = []
    
    # Section introduction
    intro_match = re.search(r'^(.*?)(?=##|$)', content, re.DOTALL)
    if intro_match and intro_match.group(1).strip():
        sections.append(f"## 💬 Réponse\n{intro_match.group(1).strip()}")
    
    # Sections techniques (données, résultats)
    technical_sections = re.findall(r'(## [^\n]+.*?)(?=## |$)', content, re.DOTALL)
    for section in technical_sections:
        if "donnée" in section.lower() or "résultat" in section.lower():
            sections.append(f"## 📊 Données Techniques\n{section}")
        else:
            sections.append(section)
    
    # Section conclusion
    conclusion_match = re.search(r'(## Conclusion|.*?$)(?!.*##)', content, re.DOTALL | re.IGNORECASE)
    if conclusion_match and conclusion_match.group(1).strip():
        sections.append(f"## ✅ Conclusion\n{conclusion_match.group(1).strip()}")
    
    return '\n\n---\n\n'.join(sections)











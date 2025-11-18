import json  
import re  
from typing import Dict, Any, Optional, AsyncGenerator, Callable  
from agentpress.tool_registry import ToolRegistry  
from agentpress.tool import ToolResult  
  
class ProcessorConfig:  
    def __init__(self, xml_tool_calling: bool = True, execute_tools: bool = True):  
        self.xml_tool_calling = xml_tool_calling  
        self.execute_tools = execute_tools  
  
class ResponseProcessor:  
    def __init__(self, tool_registry: ToolRegistry, add_message_callback: Callable):  
        self.tool_registry = tool_registry  
        self.add_message = add_message_callback  
  
    async def process_streaming_response(self, llm_response: AsyncGenerator,   
                                       thread_id: str, config: ProcessorConfig):  
        """Traiter une réponse streaming avec détection d'outils"""  
        full_response = ""  
          
        async for chunk in llm_response:  
            if hasattr(chunk, 'choices') and chunk.choices:  
                delta = chunk.choices[0].delta  
                if hasattr(delta, 'content') and delta.content:  
                    content = delta.content  
                    full_response += content  
                    yield {"action": "append", "content": content}  
  
        # Détecter et exécuter les outils  
        if config.execute_tools and self._has_tool_calls(full_response):  
            tool_results = await self._execute_detected_tools(full_response, thread_id)  
            yield {"action": "tool_results", "results": tool_results}  
  
        yield {"action": "complete", "content": full_response}  
  
    def _has_tool_calls(self, content: str) -> bool:  
        """Vérifier si le contenu contient des appels d'outils"""  
        return "<function_calls>" in content or "<invoke" in content  
  
    async def _execute_detected_tools(self, content: str, thread_id: str) -> Dict[str, Any]:  
        """Exécuter les outils détectés dans le contenu"""  
        # Votre logique existante de detect_and_execute_tools  
        patterns = [  
            r'<function_calls>\s*<invoke name="([^"]+)">(.*?)</invoke>\s*</function_calls>',  
            r'<invoke name="([^"]+)">(.*?)</invoke>'  
        ]  
          
        for pattern in patterns:  
            matches = re.findall(pattern, content, re.DOTALL)  
            if matches:  
                return await self._process_tool_matches(matches, thread_id)  
          
        return {}  
  
    async def _process_tool_matches(self, matches, thread_id: str) -> Dict[str, Any]:  
        """Traiter les correspondances d'outils trouvées"""  
        results = {}  
        available_functions = self.tool_registry.get_available_functions()  
          
        for tool_name, params_text in matches:  
            if tool_name in available_functions:  
                # Extraire les paramètres  
                params = self._extract_parameters(params_text)  
                  
                # Exécuter l'outil  
                tool_fn = available_functions[tool_name]  
                try:  
                    result = await tool_fn(**params)  
                    results[tool_name] = result  
                except Exception as e:  
                    results[tool_name] = ToolResult(success=False, output=str(e))  
          
        return results  
  
    def _extract_parameters(self, params_text: str) -> Dict[str, Any]:  
        """Extraire les paramètres du XML"""  
        param_pattern = r'<parameter name="([^"]+)">([^<]*)</parameter>'  
        param_matches = re.findall(param_pattern, params_text)  
          
        params = {}  
        for param_name, param_value in param_matches:  
            # Conversion de type basique  
            value = param_value.strip()  
            try:  
                # Essayer de convertir en nombre  
                if '.' in value:  
                    params[param_name] = float(value)  
                else:  
                    params[param_name] = int(value)  
            except ValueError:  
                params[param_name] = value  
          
        return params
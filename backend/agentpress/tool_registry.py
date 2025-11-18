import structlog  
from utils.logger import logger
from typing import Dict, Type, Any, List, Optional, Callable  
from agentpress.tool import Tool, SchemaType
  
class ToolRegistry:  
    def __init__(self):  
        self.tools = {}  
  
    def register_tool(self, tool_class: Type[Tool], function_names: Optional[List[str]] = None, **kwargs):  
        """Enregistrer un outil avec filtrage optionnel des fonctions"""  
        tool_instance = tool_class(**kwargs)  
        schemas = tool_instance.get_schemas()  
          
        for func_name, schema_list in schemas.items():  
            if function_names is None or func_name in function_names:  
                self.tools[func_name] = {  
                    "instance": tool_instance,  
                    "schema": schema_list[0] if schema_list else None  
                }  
  
    def get_available_functions(self) -> Dict[str, Callable]:  
        """Obtenir toutes les fonctions d'outils disponibles"""  
        available_functions = {}  
          
        for tool_name, tool_info in self.tools.items():  
            tool_instance = tool_info['instance']  
            function = getattr(tool_instance, tool_name)  
            available_functions[tool_name] = function  
              
        return available_functions  
  
    def get_openapi_schemas(self) -> List[Dict[str, Any]]:  
        """Obtenir les schémas OpenAPI pour l'appel de fonctions"""  
        schemas = []  
        for tool_name, tool_info in self.tools.items():  
            if tool_info['schema']:  
                schemas.append(tool_info['schema'].schema)  
        return schemas
    def get_usage_examples(self) -> Dict[str, str]:  
        """Get usage examples for tools.  
        
        Returns:  
            Dict mapping function names to their usage examples  
        """  
        examples = {}  
        
        # Get all registered tools and their schemas  
        for tool_name, tool_info in self.tools.items():  
            tool_instance = tool_info['instance']  
            all_schemas = tool_instance.get_schemas()  
            
            # Look for usage examples for this function  
            if tool_name in all_schemas:  
                for schema in all_schemas[tool_name]:  
                    if schema.schema_type == SchemaType.USAGE_EXAMPLE:  
                        examples[tool_name] = schema.schema.get('example', '')  
                        logger.debug(f"Found usage example for {tool_name}")  
                        break  
        
        logger.debug(f"Retrieved {len(examples)} usage examples")  
        return examples
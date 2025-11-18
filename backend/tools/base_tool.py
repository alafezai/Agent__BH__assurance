from typing import Dict, Any, Optional  
from abc import ABC, abstractmethod  
import json
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


from agentpress.tool import SchemaType, ToolSchema, _add_schema  
  
class ToolResult:  
    """Résultat d'exécution d'un outil."""  
      
    def __init__(self, success: bool, output: Any, error: Optional[str] = None):  
        self.success = success  
        self.output = output  
        self.error = error  
  
class Tool(ABC):  
    """Classe de base pour tous les outils."""  
      
    def __init__(self):  
        pass  
      
    def success_response(self, data: Any) -> ToolResult:  
        """Créer une réponse de succès."""  
        return ToolResult(success=True, output=data)  
      
    def fail_response(self, error: str) -> ToolResult:  
        """Créer une réponse d'erreur."""  
        return ToolResult(success=False, output=None, error=error)  
  
# Décorateurs simplifiés (remplacent ceux de Suna)  
def openapi_schema(schema: Dict[str, Any]):  
    """Décorateur pour définir le schéma OpenAPI d'un outil."""  
    def decorator(func):  
        func._openapi_schema = schema  
        return func  
    return decorator  
  
def usage_example(example: str):  
    """Decorator for providing usage examples for tools in prompts."""  
    def decorator(func):  
        #logger.debug(f"Adding usage example to function {func.__name__}")
        return _add_schema(func, ToolSchema(  
            schema_type=SchemaType.USAGE_EXAMPLE,  
            schema={"example": example}  
        ))  
    return decorator

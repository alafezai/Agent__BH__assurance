import os
from pydantic_settings import BaseSettings  
from typing import Optional
from services.encryption_service import generate_encryption_key  
  
class Settings(BaseSettings):  
    # Environment  
    ENV_MODE: str = "local"  
      
    OPENROUTER_API_KEY: Optional[str] = None  
    OPENROUTER_API_BASE: Optional[str] = "https://openrouter.ai/api/v1"
    
    # Supabase (gardé comme Suna)  
    SUPABASE_URL: str  
    SUPABASE_ANON_KEY: str  
    SUPABASE_SERVICE_ROLE_KEY: str  
      
    # Redis  
    REDIS_HOST: str = "localhost"  
    REDIS_PORT: int = 6379  
    REDIS_PASSWORD: Optional[str] = None  
    REDIS_SSL: bool = False  
      
    # Ollama  
    OLLAMA_BASE_URL: str = "http://localhost:11434"  
    OLLAMA_MODEL: str = "llama2"  
      
    # Qdrant  
    QDRANT_HOST: str = "localhost"  
    QDRANT_PORT: int = 6333  
      
    # Langfuse  
    LANGFUSE_PUBLIC_KEY: str  
    LANGFUSE_SECRET_KEY: str  
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"  
      
    # JWT  
    JWT_SECRET_KEY: str  
    JWT_ALGORITHM: str = "HS256"  
    
    # Clé de chiffrement (ajoutée comme champ Pydantic)
    MCP_CREDENTIAL_ENCRYPTION_KEY: Optional[str] = None
      
    class Config:  
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ensure_encryption_key()
    
    def ensure_encryption_key(self):
        """Vérifie et génère une clé de chiffrement si nécessaire."""
        if not self.MCP_CREDENTIAL_ENCRYPTION_KEY:
            # Générer une nouvelle clé
            new_key = generate_encryption_key()
            
            # Mettre à jour l'instance
            self.MCP_CREDENTIAL_ENCRYPTION_KEY = new_key
            
            # Ajouter au fichier .env (pour le développement)
            env_file = '.env'
            if os.path.exists(env_file):
                with open(env_file, 'a', encoding='utf-8') as f:
                    f.write(f"\nMCP_CREDENTIAL_ENCRYPTION_KEY={new_key}\n")
            
            print(f"⚠️  Nouvelle clé de chiffrement générée: {new_key[:20]}...")
            print("⚠️  Redémarrez l'application pour utiliser la nouvelle clé")
  
config = Settings()
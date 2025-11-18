import os
import json
import base64
import secrets
from cryptography.fernet import Fernet
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

class InsuranceDataEncryption:
    """Service de chiffrement des données sensibles inspiré de Suna"""
    
    def __init__(self):
        self.encryption_key = self._get_encryption_key()
    
    def _get_encryption_key(self) -> bytes:
        """Récupère la clé de chiffrement depuis les variables d'environnement."""
        key = os.getenv("MCP_CREDENTIAL_ENCRYPTION_KEY")
        if not key:
            logger.warning("MCP_CREDENTIAL_ENCRYPTION_KEY not found, using default key for development")
            # Clé par défaut pour le développement - À CHANGER EN PRODUCTION
            return Fernet.generate_key()
        return key.encode()
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Chiffre les données sensibles comme les numéros CIN."""
        try:
            fernet = Fernet(self.encryption_key)
            encrypted_data = fernet.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Erreur lors du chiffrement: {e}")
            raise
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Déchiffre les données sensibles."""
        try:
            fernet = Fernet(self.encryption_key)
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            return fernet.decrypt(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement: {e}")
            raise
    
    def encrypt_client_data(self, client_data: Dict[str, Any]) -> str:
        """Chiffre un dictionnaire complet de données client."""
        data_json = json.dumps(client_data, ensure_ascii=False)
        return self.encrypt_sensitive_data(data_json)
    
    def decrypt_client_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Déchiffre un dictionnaire de données client."""
        decrypted_json = self.decrypt_sensitive_data(encrypted_data)
        return json.loads(decrypted_json)

# Singleton pour le service de chiffrement
encryption_service = InsuranceDataEncryption()

def generate_encryption_key() -> str:
    """Génère une clé de chiffrement sécurisée base64 pour les données sensibles."""
    key_bytes = secrets.token_bytes(32)
    return base64.b64encode(key_bytes).decode("utf-8")
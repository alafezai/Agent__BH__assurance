import redis.asyncio as redis
from core.config import config
from typing import Optional, List
import json

class RedisService:
    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialise la connexion Redis."""
        self.client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD or None,
            ssl=config.REDIS_SSL,
            decode_responses=True
        )
        # Test de connexion
        try:
            await self.client.ping()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}")

    async def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[dict]:
        """Récupère l'historique d'une conversation dans l'ordre chronologique."""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        key = f"conversation:{conversation_id}:history"
        messages = await self.client.lrange(key, -limit, -1)
        return [json.loads(msg) for msg in messages]

    async def add_message_to_history(self, conversation_id: str, message: dict):
        """Ajoute un message à l'historique en respectant l'ordre chronologique."""
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        key = f"conversation:{conversation_id}:history"
        await self.client.rpush(key, json.dumps(message))  # rpush pour garder l'ordre
        await self.client.expire(key, 86400)  # TTL 24h

# Instance singleton
redis_service = RedisService()

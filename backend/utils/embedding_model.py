import structlog
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()

try:
    # Chargement du modèle multilingue
    embedding_model = SentenceTransformer('intfloat/multilingual-e5-large')
    logger.info("✅ SentenceTransformer model loaded successfully")
except Exception as e:
    logger.warning(f"⚠️ Failed to load SentenceTransformer: {e}")
    embedding_model = None
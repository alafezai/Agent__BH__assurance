import uuid
import structlog
from datetime import datetime
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Filter
from .base_tool import Tool, ToolResult, openapi_schema, usage_example
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()


class ProductMappingTool(Tool):
    """Outil RAG pour rechercher le produit d’assurance correspondant dans la collection produits_assurance."""

    def __init__(self, qdrant_client: QdrantClient, ollama_client=None, embedding_model=None):
        super().__init__()
        self.qdrant_client = qdrant_client
        self.ollama_client = ollama_client
        self.embedding_model = embedding_model

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "search_product_mapping",
            "description": "Trouver le produit d’assurance correspondant à une description utilisateur",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Description du besoin utilisateur (ex: 'assurance maison', 'protection décès', 'assistance voyage')"},
                    "limit": {"type": "integer", "description": "Nombre max de résultats produits", "default": 3},
                    "collection": {"type": "string", "description": "Nom de la collection Qdrant", "default": "produits_assurance"}
                },
                "required": ["query"]
            }
        }
    })
    @usage_example('''
        <function_calls>
        <invoke name="search_product_mapping">
        <parameter name="query">assurance habitation</parameter>
        </invoke>
        </function_calls>
    ''')
    async def search_product_mapping(self, query: str, limit: int = 3, collection: str = "mapping_produits") -> ToolResult:
        """Recherche RAG dans la collection produits_assurance."""
        try:
            if not query or not isinstance(query, str):
                return self.fail_response("Requête invalide.")

            # --- Génération embedding ---
            if self.embedding_model:
                # Version locale
                query_vector = self.embedding_model.encode(query, normalize_embeddings=True).tolist()
            elif self.ollama_client:
                # Version Ollama distante
                embedding_response = await self.ollama_client.embeddings.create(
                    model="nomic-embed-text",
                    input=query
                )
                query_vector = embedding_response.data[0].embedding
            else:
                return self.fail_response("Aucun modèle d'embedding disponible.")

            # --- Recherche dans Qdrant ---
            search_results = self.qdrant_client.search(
                collection_name=collection,
                query_vector=query_vector,
                query_filter=Filter(must=[]),
                limit=limit
            )

            # --- Structurer la réponse ---
            formatted_results = []
            for r in search_results:
                formatted_results.append({
                    "score": r.score,
                    "branche": r.payload.get("LIB_BRANCHE", "N/A"),
                    "sous_branche": r.payload.get("LIB_SOUS_BRANCHE", "N/A"),
                    "produit": r.payload.get("LIB_PRODUIT", "N/A"),
                    "text": r.payload.get("text", "")
                })

            if not formatted_results:
                return self.fail_response("Aucun produit trouvé dans la collection.")

            return self.success_response({
                "message": "Résultats du mapping produit",
                "query": query,
                "results": formatted_results,
                "metadata": {
                    "search_timestamp": datetime.utcnow().isoformat(),
                    "search_id": str(uuid.uuid4()),
                    "limit_used": limit,
                    "collection_searched": collection
                }
            })

        except Exception as e:
            logger.error(f"Erreur recherche produit: {str(e)}")
            return self.fail_response(f"Erreur lors de la recherche: {str(e)}")

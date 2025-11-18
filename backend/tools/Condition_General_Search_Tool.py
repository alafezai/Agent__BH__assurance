import uuid
import structlog
from datetime import datetime
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Filter
from .base_tool import Tool, ToolResult, openapi_schema, usage_example
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()


class ConditionsGeneralesTool(Tool):
    """Outil RAG pour rechercher dans les collections conditions_generales et bh_faq."""

    def __init__(self, qdrant_client: QdrantClient, ollama_client=None, embedding_model=None):
        super().__init__()
        self.qdrant_client = qdrant_client
        self.ollama_client = ollama_client       # Option 1 : embeddings via Ollama
        self.embedding_model = embedding_model   # Option 2 : embeddings via SentenceTransformer

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "search_conditions_generales",
            "description": "Rechercher des passages dans les collections conditions_generales et bh_faq",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Requête de recherche"},
                    "limit_conditions": {"type": "integer", "description": "Nombre max de résultats conditions générales", "default": 5},
                    "limit_faq": {"type": "integer", "description": "Nombre max de résultats FAQ", "default": 3},
                    "collections": {
                        "type": "array", 
                        "items": {"type": "string"}, 
                        "description": "Collections à rechercher", 
                        "default": ["conditions_generales", "bh_faq"]
                    }
                },
                "required": ["query"]
            }
        }
    })
    @usage_example('''
        <function_calls>
        <invoke name="search_conditions_generales">
        <parameter name="query">résiliation contrat assurance</parameter>
        </invoke>
        </function_calls>
    ''')
    async def search_conditions_generales(self, query: str, collections: List[str] = None) -> ToolResult:
        """Recherche RAG dans les conditions générales et la FAQ."""
        try:
            if not query or not isinstance(query, str):
                return self.fail_response("Requête invalide.")

            # Normaliser les limites
            limit_conditions = 3
            limit_faq = 3

            # Collections par défaut
            if collections is None:
                collections = ["conditions_generales", "bh_faq"]

            # --- Génération embedding ---
            if self.embedding_model:
                # Version SentenceTransformer locale
                query_vector = self.embedding_model.encode(query, normalize_embeddings=True).tolist()
                embedding_response = await self.ollama_client.embeddings.create(
                    model="nomic-embed-text",
                    input=query
                )
            elif self.ollama_client:
                # Version Ollama distante
                embedding_response = await self.ollama_client.embeddings.create(
                    model="nomic-embed-text",
                    input=query
                )
                query_vector = embedding_response.data[0].embedding
            else:
                return self.fail_response("Aucun modèle d'embedding disponible.")

            # --- Recherche dans les collections ---
            results = {
                "conditions_generales": [],
                "bh_faq": []
            }

            # Recherche dans conditions_generales
            if "conditions_generales" in collections:
                conditions_results = self.qdrant_client.search(
                    collection_name="conditions_generales",
                    query_vector=query_vector,
                    query_filter=Filter(must=[]),  # pas de filtre ici
                    limit=limit_conditions
                )
                results["conditions_generales"] = conditions_results

            # Recherche dans bh_faq
            if "bh_faq" in collections:
                faq_results = self.qdrant_client.search(
                    collection_name="bh_faq",
                    query_vector=embedding_response.data[0].embedding,
                    query_filter=Filter(must=[]),  # pas de filtre ici
                    limit=limit_faq
                )
                results["bh_faq"] = faq_results

            # --- Structurer la réponse ---
            formatted_results = self._format_results(results)

            if not any(formatted_results.values()):
                return self.fail_response("Aucun résultat trouvé dans les collections spécifiées.")

            return self.success_response({
                "message": "Résultats de recherche dans les conditions générales et FAQ",
                "query": query,
                "results": formatted_results,
                "metadata": {
                    "search_timestamp": datetime.utcnow().isoformat(),
                    "search_id": str(uuid.uuid4()),
                    "limit_conditions_used": limit_conditions,
                    "limit_faq_used": limit_faq,
                    "collections_searched": collections
                }
            })

        except Exception as e:
            logger.error(f"Erreur recherche conditions générales et FAQ: {str(e)}")
            return self.fail_response(f"Erreur lors de la recherche: {str(e)}")

    def _format_results(self, results: Dict[str, List]) -> Dict[str, List[Dict[str, Any]]]:
        """Formate les résultats des différentes collections."""
        formatted = {
            "conditions_generales": [],
            "bh_faq": []
        }

        # Formater les conditions générales
        for r in results["conditions_generales"]:
            formatted["conditions_generales"].append({
                "text": r.payload.get("text", ""),
                "branche": r.payload.get("branche", "N/A"),
                "filename": r.payload.get("filename", "N/A"),
                "score": r.score,
                "source": "conditions_generales"
            })

        # Formater la FAQ
        for r in results["bh_faq"]:
            formatted["bh_faq"].append({
                "text": r.payload.get("text", ""),
                "question": r.payload.get("question", ""),
                "categorie": r.payload.get("categorie", "N/A"),
                "score": r.score,
                "source": "bh_faq"
            })

        return formatted

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "format_combined_context",
            "description": "Formater le contexte combiné conditions générales et FAQ pour l'injection dans le prompt",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_results": {"type": "object", "description": "Résultats de recherche structurés"},
                    "max_length_conditions": {"type": "integer", "description": "Longueur max par condition", "default": 500},
                    "max_length_faq": {"type": "integer", "description": "Longueur max par FAQ", "default": 300}
                },
                "required": ["search_results"]
            }
        }
    })
    async def format_combined_context(self, search_results: Dict[str, List], max_length_conditions: int = 500, max_length_faq: int = 300) -> ToolResult:
        """Formater le contexte combiné pour l'injection dans le prompt."""
        try:
            context_sections = []

            # Section Conditions Générales
            conditions = search_results.get("conditions_generales", [])
            if conditions:
                context_sections.append("# CONDITIONS GÉNÉRALES")
                for i, condition in enumerate(conditions[:5], 1):
                    text = condition.get("text", "")[:max_length_conditions]
                    context_sections.append(
                        f"## Condition {i} - {condition.get('branche', 'N/A')}\n"
                        f"{text}\n"
                        f"Source: {condition.get('filename', 'N/A')}"
                    )

            # Section FAQ
            faqs = search_results.get("bh_faq", [])
            if faqs:
                context_sections.append("# FAQ - QUESTIONS FRÉQUENTES")
                for i, faq in enumerate(faqs[:3], 1):
                    text = faq.get("text", "")[:max_length_faq]
                    question = faq.get("question", "")
                    context_sections.append(
                        f"## FAQ {i} - {faq.get('categorie', 'N/A')}\n"
                        f"Question: {question}\n"
                        f"Réponse: {text}"
                    )

            if not context_sections:
                return self.success_response({
                    "formatted_context": "Aucune information trouvée dans les conditions générales ou la FAQ.",
                    "sections_count": 0
                })

            formatted_context = "\n\n".join(context_sections)

            return self.success_response({
                "formatted_context": formatted_context,
                "sections_count": {
                    "conditions": len(conditions),
                    "faq": len(faqs)
                },
                "total_results": len(conditions) + len(faqs)
            })

        except Exception as e:
            logger.error(f"Erreur formatage contexte combiné: {str(e)}")
            return self.fail_response(f"Erreur lors du formatage du contexte: {str(e)}")
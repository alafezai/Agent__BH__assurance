import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from openai import AsyncOpenAI
from .base_tool import Tool, ToolResult, openapi_schema, usage_example

logger = structlog.get_logger()

class RAGSearchTool(Tool):
    """Outil pour effectuer des recherches RAG dans les données clients."""
    
    def __init__(self, db_connection, qdrant_client, ollama_client):
        super().__init__()
        self.db = db_connection
        self.qdrant_client = qdrant_client
        self.ollama_client = ollama_client
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "search_rag",
            "description": "Rechercher des informations dans les données clients avec filtrage par client",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Requête de recherche"},
                    "client_ref": {"type": "integer", "description": "Référence du client"},
                    "limit": {"type": "integer", "description": "Nombre max de résultats", "default": 20}
                },
                "required": ["query", "client_ref"]
            }
        }
    })
    @usage_example('''
        <function_calls>
        <invoke name="search_rag">
        <parameter name="query">contrats d'assurance auto</parameter>
        <parameter name="client_ref">12169</parameter>
        <parameter name="limit">10</parameter>
        </invoke>
        </function_calls>
        ''')
    async def search_rag(self, query: str, client_ref: int, limit: int = 20) -> ToolResult:
        """Effectuer une recherche RAG dans les données clients uniquement."""
        try:
            # Validation des paramètres
            if not query or not isinstance(query, str):
                return self.fail_response("Une requête de recherche valide est requise.")
            
            if isinstance(client_ref, str) and client_ref.isdigit():
                client_ref = int(client_ref)
            
            if not client_ref or not isinstance(client_ref, int):
                return self.fail_response("Une référence client valide est requise.")
            
            # Normaliser la limite
            limit = max(1, min(limit, 50))
            
            # Effectuer la recherche RAG
            context = await self._perform_rag_search(query, client_ref, limit)
            
            if not context or not context.get("client_data"):
                return self.fail_response("Aucun résultat trouvé pour cette recherche.")
            
            # Calculer les statistiques
            client_data = context.get("client_data", [])
            
            total_contrats = 0
            total_sinistres = 0
            montant_total_sinistres = 0.0
            
            for chunk in client_data:
                if chunk and isinstance(chunk, dict):
                    total_contrats += len(chunk.get("contrats", []))
                    sinistres = chunk.get("sinistres", [])
                    total_sinistres += len(sinistres)
                    for s in sinistres:
                        montant_total_sinistres += s.get("MONTANT_A_ENCAISSER", 0) or 0
            
            return self.success_response({
                "message": "Recherche RAG effectuée avec succès",
                "query": query,
                "client_ref": client_ref,
                "results": context,
                "statistics": {
                    "total_client_docs": len(client_data),
                    "total_contrats": total_contrats,
                    "total_sinistres": total_sinistres,
                    "montant_total_sinistres": montant_total_sinistres
                },
                "metadata": {
                    "search_timestamp": datetime.utcnow().isoformat(),
                    "search_id": str(uuid.uuid4()),
                    "limit_used": limit
                }
            })
            
        except Exception as e:
            logger.error(f"Erreur recherche RAG: {str(e)}")
            return self.fail_response(f"Erreur lors de la recherche RAG: {str(e)}")
    
    async def _perform_rag_search(self, query: str, client_ref: int, limit: int = 20) -> dict:
        """
        Recherche RAG dans les données clients uniquement.
        Retourne un dictionnaire avec les données clients.
        """
        try:
            if not self.qdrant_client:
                logger.warning("Qdrant client not available, skipping RAG search")
                return {"client_data": []}

            # 1️⃣ Embedding de la requête (Ollama async)
            embedding_response = await self.ollama_client.embeddings.create(
                model="nomic-embed-text",
                input=query
            )
            query_vector = embedding_response.data[0].embedding  # liste de floats

            # 2️⃣ Filtre documents client
            client_filter = Filter(
                must=[
                    FieldCondition(
                        key="REF_PERSONNE", 
                        match=MatchValue(value=client_ref)
                    )
                ]
            )

            # 3️⃣ Recherche dans Qdrant pour les documents clients uniquement
            client_results = self.qdrant_client.search(
                collection_name="bh_assurance_clients_ollama",
                query_vector=query_vector,
                query_filter=client_filter,
                limit=limit
            )

            # 4️⃣ Construire un contexte structuré avec seulement les données clients
            context_structured = {
                "client_data": [r.payload for r in client_results]
            }

            logger.info(f"Found {len(context_structured['client_data'])} client documents for client {client_ref}")
            return context_structured

        except Exception as e:
            logger.warning(f"RAG search failed: {str(e)}")
            return {"client_data": []}
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "format_rag_context",
            "description": "Formater le contexte RAG pour l'injection dans le prompt système",
            "parameters": {
                "type": "object",
                "properties": {
                    "rag_context": {"type": "object", "description": "Contexte RAG structuré"},
                    "include_stats": {"type": "boolean", "description": "Inclure les statistiques", "default": True}
                },
                "required": ["rag_context"]
            }
        }
    })
    async def format_rag_context(self, rag_context: dict, include_stats: bool = True) -> ToolResult:
        """Formater le contexte RAG pour l'injection dans le prompt système."""
        try:
            client_chunks = rag_context.get("client_data", [])[:20]
            
            # Construire le contexte client
            context_client_list = []
            total_contrats = 0
            total_sinistres = 0
            montant_total_sinistres = 0.0
            
            for chunk in client_chunks:
                if chunk and isinstance(chunk, dict):
                    # Contrats
                    for c in chunk.get("contrats", []):
                        total_contrats += 1
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
                        total_sinistres += 1
                        montant_total_sinistres += s.get("MONTANT_A_ENCAISSER", 0) or 0
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

            # Concaténer contexte final
            context_text = "# Données client\n" + "\n".join(context_client_list) if context_client_list else "Aucune donnée client trouvée."
            
            result = {
                "formatted_context": context_text.strip(),
                "sections": {
                    "client_sections": len(context_client_list)
                }
            }
            
            if include_stats:
                result["statistics"] = {
                    "total_contrats": total_contrats,
                    "total_sinistres": total_sinistres,
                    "montant_total_sinistres": montant_total_sinistres
                }
            
            return self.success_response(result)
            
        except Exception as e:
            logger.error(f"Erreur formatage contexte RAG: {str(e)}")
            return self.fail_response(f"Erreur lors du formatage du contexte RAG: {str(e)}")
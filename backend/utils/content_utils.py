import re
from typing import Optional

def clean_markdown_content(content: str) -> str:
    """Nettoyer et formater le contenu pour un affichage Markdown optimal avec sections claires"""
    if not content:
        return ""
    
    # Supprimer les balises XML résiduelles
    content = re.sub(r'<function_calls>.*?</function_calls>', "", content, flags=re.DOTALL)
    content = re.sub(r'<think>.*?</think>', "", content, flags=re.DOTALL)
    content = re.sub(r'<invoke.*?</invoke>', "", content, flags=re.DOTALL)
    
    # Nettoyer les espaces multiples et sauts de ligne excessifs
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    content = re.sub(r'[ \t]+', ' ', content)
    
    # Améliorer la structure des sections
    content = enhance_section_structure(content)
    
    return content.strip()

def enhance_section_structure(content: str) -> str:
    """Améliorer la structure des sections avec des titres clairs"""
    # Standardiser les titres de sections
    section_patterns = [
        (r'(## Résultats de recherche pour:.*?\n)', r'\n## 🔍 Résultats de Recherche\n'),
        (r'(## Conditions Générales:)', r'\n## 📋 Conditions Générales\n'),
        (r'(## FAQ:)', r'\n## ❓ FAQ\n'),
        (r'(## Données client trouvées)', r'\n## 👤 Données Client\n'),
        (r'(## FAQ pertinente)', r'\n## ❓ Questions Fréquentes\n'),
        (r'(# Devis créé avec succès)', r'\n## 📄 Devis Créé\n'),
    ]
    
    for pattern, replacement in section_patterns:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    # Ajouter des séparateurs entre les sections principales
    content = re.sub(r'\n(## [^\n]+)\n', r'\n\n---\n\n\1\n', content)
    
    # Formater les listes pour une meilleure lisibilité
    content = format_lists(content)
    
    return content

def format_lists(content: str) -> str:
    """Améliorer le formatage des listes"""
    # Formater les listes à puces
    content = re.sub(r'\n- ', r'\n• ', content)
    
    # Formater les listes numérotées
    content = re.sub(r'\n(\d+)\.', r'\n\1. ', content)
    
    # Ajouter des espaces après les puces
    content = re.sub(r'•(\S)', r'• \1', content)
    
    return content

def clean_assistant_response(content: str) -> str:
    """Nettoyer la réponse de l'assistant avec un formatage structuré"""
    if not content or not isinstance(content, str):
        return "" if content is None else str(content)
    
    # Supprimer les balises XML et les invoke blocks (insensible à la casse, DOTALL)
    cleaned_content = re.sub(r'(?is)<function_calls>.*?</function_calls>', '', content)
    cleaned_content = re.sub(r'(?is)<invoke.*?</invoke>', '', cleaned_content)
    
    # Supprimer les annotations techniques (insensible à la casse)
    cleaned_content = re.sub(r'(?i)\(Résultat du search_rag\)\s*', '', cleaned_content)
    cleaned_content = re.sub(r'(?i)\(Résultat des conditions générales\)\s*', '', cleaned_content)
    
    # Structurer le contenu avec des sections claires
    cleaned_content = structure_assistant_response(cleaned_content)
    
    return cleaned_content.strip()

def structure_assistant_response(content: str) -> str:
    """Structurer la réponse de l'assistant avec des sections organisées"""
    # Détecter et organiser les sections naturelles
    sections = []
    
    # Section introduction
    intro_match = re.search(r'^(.*?)(?=##|$)', content, re.DOTALL)
    if intro_match and intro_match.group(1).strip():
        sections.append(f"## 💬 Réponse\n{intro_match.group(1).strip()}")
    
    # Sections techniques (données, résultats)
    technical_sections = re.findall(r'(## [^\n]+.*?)(?=## |$)', content, re.DOTALL)
    for section in technical_sections:
        if "donnée" in section.lower() or "résultat" in section.lower():
            sections.append(f"## 📊 Données Techniques\n{section}")
        else:
            sections.append(section)
    
    # Section conclusion
    conclusion_match = re.search(r'(## Conclusion|.*?$)(?!.*##)', content, re.DOTALL | re.IGNORECASE)
    if conclusion_match and conclusion_match.group(1).strip():
        sections.append(f"## ✅ Conclusion\n{conclusion_match.group(1).strip()}")
    
    return '\n\n---\n\n'.join(sections)

def is_simple_greeting(message: str) -> bool:
    """Détecter si le message est une salutation simple"""
    if not message:
        return False
        
    simple_greetings = [
        "bonjour", "salut", "hello", "hi", "bonsoir",
        "ça va", "ca va", "comment allez-vous", "comment ça va",
        "merci", "au revoir", "bye", "à bientôt"
    ]
    message_lower = message.lower().strip()
    return any(greeting in message_lower for greeting in simple_greetings)

def extract_tool_parameters(params_text: str) -> dict:
    """Extraire les paramètres des balises XML des outils"""
    param_pattern = r'<parameter name="([^"]+)">([^<]*)</parameter>'
    param_matches = re.findall(param_pattern, params_text)
    
    params = {}
    for param_name, param_value in param_matches:
        # Conversion des types selon le nom du paramètre
        if param_name in ["limit", "client_ref", "nombre_place", "puissance", "classe"]:
            try:
                params[param_name] = int(param_value.strip())
            except ValueError:
                params[param_name] = param_value.strip()
        elif param_name in ["valeur_venale", "valeur_a_neuf", "capital_bris_de_glace", "capital_dommage_collision"]:
            try:
                params[param_name] = float(param_value.strip())
            except ValueError:
                params[param_name] = param_value.strip()
        else:
            params[param_name] = param_value.strip()
    
    return params

def remove_xml_tool_call(response_text: str, tool_name: str) -> str:
    """Supprimer les appels d'outils XML de la réponse"""
    replacement_patterns = [
        rf'<function_calls>\s*<invoke name="{tool_name}">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',
        rf'<n_function_calls>\s*<invoke name="{tool_name}">.*?</invoke>\s*</function_calls>(?:\s*</function_calls>)?',
        rf'<invoke name="{tool_name}">.*?</invoke>(?:\s*</function_calls>)?'
    ]
    
    for pattern in replacement_patterns:
        if re.search(pattern, response_text, re.DOTALL):
            response_text = re.sub(pattern, "", response_text, flags=re.DOTALL)
            return response_text
    
    # Fallback: supprimer tout bloc XML
    response_text = re.sub(r'<function_calls>.*?</function_calls>', "", response_text, flags=re.DOTALL)
    return response_text

from typing import Dict, List, Any, Optional

def build_context_text(rag_context_structured: dict) -> str:
    """Construire le texte de contexte à partir des données RAG structurées."""
    client_chunks = rag_context_structured.get("client_data", [])[:100]
    faq_chunks = rag_context_structured.get("faq_data", [])[:5]
    
    # Construire le contexte client
    context_client_list = []
    for chunk in client_chunks:
        if chunk and isinstance(chunk, dict):
            # Contrats
            for c in chunk.get("contrats", []):
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

    # Construire le contexte FAQ
    context_faq_list = []
    for f in faq_chunks:
        context_faq_list.append(f"## FAQ\n{f.get('text', '')}")

    # Concaténer contexte final avec sections séparées
    context_sections = []
    if context_client_list:
        context_sections.append("# Données client\n" + "\n".join(context_client_list))
    if context_faq_list:
        context_sections.append("# FAQ / Support\n" + "\n".join(context_faq_list))

    return "\n\n".join(context_sections).strip()

def format_tool_data_for_context(client_data: list, faq_data: list) -> str:
    """Formater les données des outils pour le contexte LLM."""
    formatted_sections = []
    
    # Formater les données client
    if client_data:
        client_section = "## Données client trouvées\n"
        for chunk in client_data:
            if chunk and isinstance(chunk, dict):
                # Contrats
                for c in chunk.get("contrats", []):
                    client_section += f"- Contrat {c.get('NUM_CONTRAT')}: {c.get('LIB_PRODUIT')} ({c.get('LIB_ETAT_CONTRAT')})\n"
                
                # Sinistres
                for s in chunk.get("sinistres", []):
                    client_section += f"- Sinistre {s.get('NUM_SINISTRE')}: {s.get('LIB_TYPE_SINISTRE')} - {s.get('LIB_ETAT_SINISTRE')}\n"
                
                # Garanties
                for g in chunk.get("garanties", []):
                    client_section += f"- Garantie: {g.get('LIB_GARANTIE')} (Capital: {g.get('CAPITAL_ASSURE')})\n"
        
        formatted_sections.append(client_section)
    
    # Formater les données FAQ
    if faq_data:
        faq_section = "## FAQ pertinente\n"
        for faq in faq_data:
            if faq and isinstance(faq, dict):
                faq_section += f"- {faq.get('text', '')}\n"
        
        formatted_sections.append(faq_section)
    
    return "\n\n".join(formatted_sections)

def build_system_prompt(context_text: str, client_ref: int) -> str:
    """Construire le prompt système avec le contexte"""
    return f"""TOUTE QUESTION D'ASSURANCE :  
    1. Commencer OBLIGATOIREMENT par appeler search_conditions_generales  
    2. Puis appeler search_rag avec le client_ref correspondant  
    3. Ne donner une réponse finale qu'après avoir récupéré les informations de ces deux outils  
- Format XML obligatoire pour tous les appels :

Format search_conditions_generales:
<function_calls>  
<invoke name="search_conditions_generales">  
<parameter name="query">votre requête de recherche</parameter>   
</invoke>  
</function_calls>  

Format search_rag:
<function_calls>  
<invoke name="search_rag">  
<parameter name="query">votre requête de recherche</parameter>  
<parameter name="client_ref">{client_ref}</parameter>  
<parameter name="limit">10</parameter>  
</invoke>  
</function_calls>  

- Format create_devis (à utiliser uniquement sur demande explicite de devis) :
<function_calls>  
<invoke name="create_devis">  
<parameter name="n_cin">numero_cin</parameter>  
<parameter name="valeur_venale">valeur</parameter>  
<parameter name="nombre_place">places</parameter>  
<parameter name="valeur_a_neuf">valeur_neuf</parameter>  
<parameter name="date_premiere_mise_en_circulation">date</parameter>  
<parameter name="capital_dommage_collision">capital</parameter>  
<parameter name="puissance">puissance</parameter>  
<parameter name="classe">classe</parameter>  
</invoke>  
</function_calls>  

- Si l'utilisateur demande les informations nécessaires pour un devis, répondre exactement comme suit sans modifier le contenu :
"Pour établir votre devis d'assurance automobile, j'ai besoin des informations suivantes :  
1. Numéro de carte d'identité nationale (CIN)  
2. Valeur vénale du véhicule (prix actuel)  
3. Nombre de places du véhicule  
4. Valeur à neuf (prix d'achat initial)  
5. Date de première mise en circulation  
6. Capital dommage collision souhaité  
7. Puissance du véhicule (en chevaux)  
8. Classe du véhicule  
  
Pouvez-vous me fournir ces informations ?"

# Contexte actuel  
{context_text}  

RAPPEL :  
- Utiliser OBLIGATOIREMENT search_conditions_generales et search_rag pour toutes questions d'assurance  
- N'utiliser create_devis que si l'utilisateur demande explicitement un devis"""

def build_enriched_system_prompt(enriched_context: str) -> str:
    """Construire un prompt système enrichi après exécution des outils"""
    return f"""Utilise ces informations pour répondre à la question de l'utilisateur de manière naturelle et professionnelle.  

{enriched_context}  

Instructions:  
- Utilise uniquement les informations fournies dans le contexte  
- Sois précis et utile  
- Ne mentionne pas les outils utilisés
- Donne une réponse claire et détaillée
- INTERDICTION ABSOLUE de dire à l'utilisateur d'aller consulter ses conditions générales, un site ou un document externe
- L'agent doit TOUJOURS expliquer avec ses propres mots, à partir des résultats fournis
- Si une information est incomplète, demander directement à l'utilisateur de préciser"""

def extract_statistics_from_context(rag_context: dict) -> tuple:
    """Extraire les statistiques du contexte RAG"""
    total_contrats = 0
    total_sinistres = 0
    montant_total_sinistres = 0.0
    
    for chunk in rag_context.get("client_data", []):
        if chunk and isinstance(chunk, dict):
            total_contrats += len(chunk.get("contrats", []))
            sinistres = chunk.get("sinistres", [])
            total_sinistres += len(sinistres)
            for sinistre in sinistres:
                montant = sinistre.get("MONTANT_A_ENCAISSER", 0)
                if isinstance(montant, (int, float)):
                    montant_total_sinistres += montant
    
    return total_contrats, total_sinistres, montant_total_sinistres

def build_enriched_context(context_text: str, tool_data_for_llm: dict) -> str:
    """Construire le contexte enrichi avec les données des outils"""
    enriched_context = context_text
    
    for tool_name, data in tool_data_for_llm.items():
        if tool_name == "search_rag" and data.get("success"):
            # Ajouter les résultats RAG au contexte
            client_data = data.get("client_data", [])
            faq_data = data.get("faq_data", [])
            query = data.get("query", "")
            
            enriched_context += f"\n\n# Résultats de recherche pour: {query}\n"
            enriched_context += format_tool_data_for_context(client_data, faq_data)
            
        elif tool_name == "search_conditions_generales" and data.get("success"):
            results = data.get("results", {})
            query = data.get("query", "")

            enriched_context += f"\n\n# Résultats de recherche pour: {query}\n"

            # Résultats Conditions Générales
            cond_generales = results.get("conditions_generales", [])
            if cond_generales:
                enriched_context += "\n## Conditions Générales:\n"
                for r in cond_generales:
                    enriched_context += f"- {r.get('text', '')[:200]}... (Branche: {r.get('branche', 'N/A')}, Source: {r.get('source', 'N/A')})\n"

            # Résultats FAQ
            faq_results = results.get("bh_faq", [])
            if faq_results:
                enriched_context += "\n## FAQ:\n"
                for r in faq_results:
                    enriched_context += f"- Q: {r.get('question', 'N/A')} → {r.get('text', '')[:200]}... (Catégorie: {r.get('categorie', 'N/A')}, Source: {r.get('source', 'N/A')})\n"
                    
        elif tool_name == "create_devis" and data.get("success"):
            # Stocker les données de devis pour le frontend
            devis_id = data.get('devis_id')
            enriched_context += f"\n\n# Devis créé avec succès\nID: {devis_id}\n"
    
    return enriched_context
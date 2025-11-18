import asyncio
import httpx  
from typing import Dict, Any, Optional  
from datetime import datetime  
import uuid  
import json  
import structlog  
from reportlab.lib.pagesizes import A4  
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle  
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  
from reportlab.lib.units import inch  
from reportlab.lib import colors  
import io  
import base64

from .base_tool import Tool, ToolResult, openapi_schema, usage_example  
  
logger = structlog.get_logger()  
  
class CreateDevisTool(Tool):  
    """Outil pour créer des devis d'assurance en appelant l'API externe et générer un PDF."""  
      
    def __init__(self, db_connection):  
        super().__init__()  
        self.db = db_connection  
        self.api_base_url = "https://apidevis.onrender.com/api"  
      
    @openapi_schema({  
        "type": "function",  
        "function": {  
            "name": "create_devis",  
            "description": "Créer un devis d'assurance auto en appelant l'API externe et générer un PDF",  
            "parameters": {  
                "type": "object",  
                "properties": {  
                    "client_ref": {"type": "integer", "description": "Référence du client"},  
                    "n_cin": {"type": "string", "description": "Numéro CIN du client"},  
                    "valeur_venale": {"type": "number", "description": "Valeur vénale du véhicule"},  
                    "nature_contrat": {"type": "string", "description": "Nature du contrat (r/n)", "default": "r"},  
                    "nombre_place": {"type": "integer", "description": "Nombre de places du véhicule"},  
                    "valeur_a_neuf": {"type": "number", "description": "Valeur à neuf du véhicule"},  
                    "date_premiere_mise_en_circulation": {"type": "string", "description": "Date (YYYY-MM-DD)"},  
                    "capital_bris_de_glace": {"type": "number", "description": "Capital bris de glace", "default": 900},  
                    "capital_dommage_collision": {"type": "number", "description": "Capital dommage collision"},  
                    "puissance": {"type": "integer", "description": "Puissance du véhicule"},  
                    "classe": {"type": "integer", "description": "Classe du véhicule"}  
                },  
                "required": ["client_ref", "n_cin", "valeur_venale", "nombre_place", "valeur_a_neuf",   
                           "date_premiere_mise_en_circulation", "capital_dommage_collision", "puissance", "classe"]  
            }  
        }  
    })  
    @usage_example('''  
        <function_calls>  
        <invoke name="create_devis">  
        <parameter name="client_ref">12169</parameter>  
        <parameter name="n_cin">08478931</parameter>  
        <parameter name="valeur_venale">60000</parameter>  
        <parameter name="nature_contrat">r</parameter>  
        <parameter name="nombre_place">5</parameter>  
        <parameter name="valeur_a_neuf">60000</parameter>  
        <parameter name="date_premiere_mise_en_circulation">2022-02-28</parameter>  
        <parameter name="capital_bris_de_glace">900</parameter>  
        <parameter name="capital_dommage_collision">60000</parameter>  
        <parameter name="puissance">6</parameter>  
        <parameter name="classe">3</parameter>  
        </invoke>  
        </function_calls>  
        ''')  
    async def create_devis(self, client_ref: int, n_cin: str, valeur_venale: float,   
                          nombre_place: int, valeur_a_neuf: float,   
                          date_premiere_mise_en_circulation: str, capital_dommage_collision: float,  
                          puissance: int, classe: int, nature_contrat: str = "r",   
                          capital_bris_de_glace: float = 900) -> ToolResult:  
        """Créer un devis d'assurance auto via l'API externe et générer un PDF."""  
        try:  
            params = {  
                "n_cin": n_cin, "valeur_venale": valeur_venale, "nature_contrat": nature_contrat,  
                "nombre_place": nombre_place, "valeur_a_neuf": valeur_a_neuf,  
                "date_premiere_mise_en_circulation": date_premiere_mise_en_circulation,  
                "capital_bris_de_glace": capital_bris_de_glace,  
                "capital_dommage_collision": capital_dommage_collision,  
                "puissance": puissance, "classe": classe  
            }  
              
            # Appel à l'API externe pour obtenir le devis  
            devis_data = await self._call_devis_api(params)  
            if not devis_data:  
                return self.fail_response("Erreur lors de l'appel à l'API de devis")  
              
            devis_id = str(uuid.uuid4())  
              
            # Générer le PDF formaté  
            pdf_bytes = await self._generate_pdf_devis(devis_data, devis_id, params)  
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')  
              
            # Sauvegarder en base avec le PDF  
            client = await self.db.client  
            devis_record = {  
                'devis_id': devis_id, 'client_ref': client_ref, 'type_assurance': 'auto',  
                'parametres_vehicule': params, 'reponse_api': devis_data,  
                'pdf_content': pdf_base64,  # Stocker le PDF en base64  
                'statut': 'brouillon', 'date_creation': datetime.utcnow().isoformat(),  
                'metadata': {  
                    'api_source': 'apidevis.onrender.com',   
                    'api_endpoint': '/api/auto/packs',  
                    'pdf_generated': True  
                }  
            }  
              
            result = await client.table('devis').insert(devis_record).execute()  
              
            if result.data:  
                return self.success_response({  
                    "message": "Devis créé avec succès",  
                    "devis_id": devis_id,  
                    "pdf_available": True,  
                    "download_info": "📄 Votre devis PDF est prêt à télécharger !",  
                    "download_url": f"/api/chat/devis/{devis_id}/pdf"  
                })  
            else:  
                return self.fail_response("Erreur lors de la sauvegarde du devis")  
                  
        except Exception as e:  
            logger.error(f"Erreur création devis: {str(e)}")  
            return self.fail_response(f"Erreur lors de la création du devis: {str(e)}")  
      
    async def _call_devis_api(self, params: Dict[str, Any]) -> Optional[Dict]:
        """Appeler l'API externe pour obtenir le devis."""
        try:
            url = f"{self.api_base_url}/auto/packs"
            
            # Réduire le timeout et ajouter des retries
            timeout_config = httpx.Timeout(15.0, connect=10.0)
            
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                logger.info(f"Calling devis API: {url} with params: {params}")
                
                # Essayer plusieurs fois en cas d'échec
                for attempt in range(3):
                    try:
                        response = await client.get(url, params=params)
                        response.raise_for_status()
                        data = response.json()
                        logger.info(f"API response received: {len(str(data))} characters")
                        return data
                        
                    except (httpx.TimeoutException, httpx.ConnectError) as e:
                        if attempt == 2:  # Dernière tentative
                            raise
                        logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying...")
                        await asyncio.sleep(2)  # Attendre avant de réessayer
                        
        except httpx.TimeoutException:
            logger.error("API timeout after multiple attempts")
            return None
        except httpx.ConnectError:
            logger.error("API connection error")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à l'API de devis: {str(e)}")
            return None
      
    async def _generate_pdf_devis(self, devis_data: dict, devis_id: str, client_params: dict) -> bytes:  
        """Générer un PDF formaté professionnel pour le devis."""  
        buffer = io.BytesIO()  
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,   
                               topMargin=72, bottomMargin=18)  
          
        # Styles personnalisés  
        styles = getSampleStyleSheet()  
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],   
                                    fontSize=20, spaceAfter=30, alignment=1, textColor=colors.darkblue)  
        subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'],   
                                       fontSize=14, spaceAfter=15, textColor=colors.darkblue)  
          
        story = []  
          
        # En-tête avec titre  
        story.append(Paragraph("DEVIS D'ASSURANCE AUTOMOBILE", title_style))  
        story.append(Paragraph(f"Devis N°: {devis_id}", styles['Normal']))  
        story.append(Paragraph(f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))  
        story.append(Spacer(1, 30))  
          
        # Section informations véhicule  
        story.append(Paragraph("INFORMATIONS VÉHICULE", subtitle_style))  
          
        client_info = [  
            ['CIN du propriétaire:', client_params.get('n_cin', 'N/A')],  
            ['Valeur vénale:', f"{client_params.get('valeur_venale', 0):,.0f} DT"],  
            ['Valeur à neuf:', f"{client_params.get('valeur_a_neuf', 0):,.0f} DT"],  
            ['Nombre de places:', str(client_params.get('nombre_place', 'N/A'))],  
            ['Date mise en circulation:', client_params.get('date_premiere_mise_en_circulation', 'N/A')],  
            ['Puissance fiscale:', f"{client_params.get('puissance', 'N/A')} CV"],  
            ['Classe du véhicule:', str(client_params.get('classe', 'N/A'))],  
            ['Capital dommage collision:', f"{client_params.get('capital_dommage_collision', 0):,.0f} DT"]  
        ]  
          
        client_table = Table(client_info, colWidths=[2.5*inch, 3*inch])  
        client_table.setStyle(TableStyle([  
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),  
            ('BACKGROUND', (1, 0), (1, -1), colors.white),  
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),  
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),  
            ('FONTSIZE', (0, 0), (-1, -1), 10),  
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),  
            ('TOPPADDING', (0, 0), (-1, -1), 8),  
            ('GRID', (0, 0), (-1, -1), 1, colors.black)  
        ]))  
          
        story.append(client_table)  
        story.append(Spacer(1, 30))  
          
        # Section packs d'assurance  
        story.append(Paragraph("OFFRES D'ASSURANCE DISPONIBLES", subtitle_style))  
          
        if 'body' in devis_data and 'result' in devis_data['body']:  
            pack_count = 0  
            for pack in devis_data['body']['result']:  
                if pack.get('packApplicable', False):  
                    pack_count += 1  
                      
                    # Titre du pack  
                    pack_title = f"PACK {pack.get('codeProduit', 'N/A')} - {pack.get('packDisponible', 'Pack disponible')}"  
                    story.append(Paragraph(pack_title, styles['Heading3']))  
                      
                    # Tableau des prix  
                    prime_annuelle = pack.get('montantTotalPrime', 0)  
                    prime_mensuelle = pack.get('montantPrimeDivisePar12', 0)  
                      
                    prix_data = [  
                        ['Prime annuelle:', f"{prime_annuelle:,.2f} DT"],  
                        ['Prime mensuelle:', f"{prime_mensuelle:,.2f} DT"]  
                    ]  
                      
                    prix_table = Table(prix_data, colWidths=[2*inch, 2*inch])  
                    prix_table.setStyle(TableStyle([  
                        ('BACKGROUND', (0, 0), (0, -1), colors.lightgreen),  
                        ('BACKGROUND', (1, 0), (1, -1), colors.white),  
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),  
                        ('FONTSIZE', (0, 0), (-1, -1), 12),  
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),  
                        ('TOPPADDING', (0, 0), (-1, -1), 8),  
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)  
                    ]))  
                      
                    story.append(prix_table)  
                    story.append(Spacer(1, 15))  
                      
                    # Tableau des garanties  
                    story.append(Paragraph("Garanties incluses:", styles['Heading4']))  
                      
                    garanties_data = [['Garantie', 'Capital assuré', 'Franchise']]  
                    for garantie in pack.get('garantieCourtierModels', []):  
                        capital = garantie.get('capital', '0')  
                        if capital and float(capital) > 0:  
                            capital_str = f"{float(capital):,.0f} DT"  
                        else:  
                            capital_str = 'Incluse'  
                          
                        garanties_data.append([  
                            garantie.get('libGarantie', 'N/A'),  
                            capital_str,  
                            garantie.get('codeFranchise', 'N/A')  
                        ])  
                      
                    garanties_table = Table(garanties_data, colWidths=[3*inch, 1.5*inch, 1*inch])  
                    garanties_table.setStyle(TableStyle([  
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
                        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),  
                        ('FONTSIZE', (0, 0), (-1, -1), 9),  
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  
                        ('TOPPADDING', (0, 0), (-1, -1), 6),  
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)  
                    ]))  
                      
                    story.append(garanties_table)  
                    story.append(Spacer(1, 20))  
                      
                    # Ajouter une séparation entre les packs  
                    if pack_count < len([p for p in devis_data['body']['result'] if p.get('packApplicable', False)]):  
                        story.append(Spacer(1, 10))  
          
        # Section récapitulatif  
        story.append(Spacer(1, 30))  
        story.append(Paragraph("RÉCAPITULATIF", subtitle_style))  
          
        # Compter les packs disponibles  
        packs_disponibles = len([p for p in devis_data['body']['result'] if p.get('packApplicable', False)])  
          
        recap_info = [  
            ['Nombre de packs disponibles:', str(packs_disponibles)],  
            ['Statut du devis:', 'Brouillon'],  
            ['Validité:', '30 jours à compter de la date de génération']  
        ]  
          
        recap_table = Table(recap_info, colWidths=[3*inch, 2*inch])  
        recap_table.setStyle(TableStyle([  
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),  
            ('BACKGROUND', (1, 0), (1, -1), colors.white),  
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),  
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),  
            ('FONTSIZE', (0, 0), (-1, -1), 10),  
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),  
            ('TOPPADDING', (0, 0), (-1, -1), 8),  
            ('GRID', (0, 0), (-1, -1), 1, colors.black)  
        ]))  
          
        story.append(recap_table)  
          
        # Footer avec informations légales  
        story.append(Spacer(1, 40))  
        story.append(Paragraph("MENTIONS LÉGALES", styles['Heading4']))  
        story.append(Paragraph(  
            "Ce devis est généré automatiquement et n'engage pas définitivement l'assureur. "  
            "Les conditions définitives seront précisées dans le contrat d'assurance. "  
            "Pour toute question, veuillez contacter votre conseiller.",  
            styles['Normal']  
        ))  
          
        # Pied de page avec date et ID  
        story.append(Spacer(1, 20))  
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'],   
                                     fontSize=8, textColor=colors.grey, alignment=1)  
        story.append(Paragraph(f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} - ID: {devis_id}", footer_style))  
          
        # Construire le PDF  
        doc.build(story)  
        buffer.seek(0)  
        return buffer.getvalue()
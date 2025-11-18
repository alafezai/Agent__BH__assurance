import base64
import io
from fastapi import APIRouter, HTTPException, Depends, Request  
from typing import List, Optional  
from openai import AsyncOpenAI
from pydantic import BaseModel  
from datetime import datetime  
import uuid  
import structlog  
from routers.chat import send_message

from models.conversation import MessageCreate, VoiceMessageCreate
from services.supabase import DBConnection  
from utils.auth_utils import get_current_user_id_from_jwt  
from core.config import config 
  
router = APIRouter(prefix="/conversations", tags=["conversations"])  
logger = structlog.get_logger()  
  
# Modèles  
class ConversationCreate(BaseModel):  
    title: str  
    metadata: dict = {}  
  
class ConversationResponse(BaseModel):  
    conversation_id: str  
    user_id: str  
    title: str  
    created_at: datetime  
    updated_at: datetime  
    metadata: dict  
  
class ConversationUpdate(BaseModel):  
    title: Optional[str] = None  
    metadata: Optional[dict] = None  
  
class ConversationStats(BaseModel):  
    total_conversations: int  
    total_messages: int  
    last_activity: Optional[datetime] = None  



openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="",
    default_headers={
        "HTTP-Referer": "https://bhassurance.com",  # Required by OpenRouter
        "X-Title": "BH Assurance Chat",               # Optional
    }
)


ollama_client = AsyncOpenAI(    
    base_url=config.OLLAMA_BASE_URL + "/v1",    
    api_key="ollama"  # Clé factice pour Ollama    
)  
db = None  
  
def initialize(_db: DBConnection):  
    """Initialize with database connection from main API."""  
    global db  
    db = _db
  
@router.get("/", response_model=List[ConversationResponse])  
async def get_conversations(  
    request: Request,  
    limit: int = 50,  
    offset: int = 0,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Récupérer toutes les conversations de l'utilisateur"""  
    try:  
        # Initialiser la connexion Supabase  
        client = await db.client  
          
        # Récupérer les conversations depuis Supabase avec pagination  
        conversations_result = await client.table('conversations').select('*').eq('user_id', user_id).order('updated_at', desc=True).range(offset, offset + limit - 1).execute()  
          
        conversations = []  
        for conv in conversations_result.data:  
            # Gérer le format de timestamp  
            created_at_str = conv['created_at']  
            updated_at_str = conv['updated_at']  
              
            if created_at_str.endswith('Z'):  
                created_at_str = created_at_str.replace('Z', '+00:00')  
            if updated_at_str.endswith('Z'):  
                updated_at_str = updated_at_str.replace('Z', '+00:00')  
              
            conversations.append(ConversationResponse(  
                conversation_id=conv['conversation_id'],  
                user_id=conv['user_id'],  
                title=conv['title'],  
                created_at=datetime.fromisoformat(created_at_str),  
                updated_at=datetime.fromisoformat(updated_at_str),  
                metadata=conv.get('metadata', {})  
            ))  
          
        logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")  
        return conversations  
          
    except Exception as e:  
        logger.error(f"Error fetching conversations: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to fetch conversations")  
  
@router.post("/", response_model=ConversationResponse)  
async def create_conversation(  
    conversation: ConversationCreate,   
    request: Request,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Créer une nouvelle conversation"""  
    try:  
        # Initialiser la connexion Supabase  
        client = await db.client  
          
        now = datetime.utcnow()  
        conversation_id = str(uuid.uuid4())  
          
        # Créer la conversation dans Supabase  
        conversation_data = {  
            'conversation_id': conversation_id,  
            'user_id': user_id,  
            'title': conversation.title,  
            'created_at': now.isoformat(),  
            'updated_at': now.isoformat(),  
            'metadata': conversation.metadata  
        }  
          
        result = await client.table('conversations').insert(conversation_data).execute()  
          
        if not result.data:  
            raise HTTPException(status_code=500, detail="Failed to create conversation")  
          
        logger.info(f"Created conversation {conversation_id} for user {user_id}")  
          
        return ConversationResponse(  
            conversation_id=conversation_id,  
            user_id=user_id,  
            title=conversation.title,  
            created_at=now,  
            updated_at=now,  
            metadata=conversation.metadata  
        )  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Error creating conversation: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to create conversation")  
  
@router.get("/{conversation_id}", response_model=ConversationResponse)  
async def get_conversation(  
    conversation_id: str,   
    request: Request,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Récupérer une conversation spécifique"""  
    try:  
        # Initialiser la connexion Supabase  
        client = await db.client  
          
        # Récupérer la conversation depuis Supabase  
        conversation_result = await client.table('conversations').select('*').eq('conversation_id', conversation_id).eq('user_id', user_id).execute()  
          
        if not conversation_result.data:  
            raise HTTPException(status_code=404, detail="Conversation not found")  
          
        conv = conversation_result.data[0]  
          
        # Gérer le format de timestamp  
        created_at_str = conv['created_at']  
        updated_at_str = conv['updated_at']  
          
        if created_at_str.endswith('Z'):  
            created_at_str = created_at_str.replace('Z', '+00:00')  
        if updated_at_str.endswith('Z'):  
            updated_at_str = updated_at_str.replace('Z', '+00:00')  
          
        return ConversationResponse(  
            conversation_id=conv['conversation_id'],  
            user_id=conv['user_id'],  
            title=conv['title'],  
            created_at=datetime.fromisoformat(created_at_str),  
            updated_at=datetime.fromisoformat(updated_at_str),  
            metadata=conv.get('metadata', {})  
        )  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Error fetching conversation {conversation_id}: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to fetch conversation")  
  


 
  
@router.delete("/{conversation_id}")  
async def delete_conversation(  
    conversation_id: str,  
    request: Request,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Supprimer une conversation et tous ses messages"""  
    try:  
        # Utiliser une nouvelle instance DB et l'initialiser avant d'accéder au client  
        client = await db.client  # Utiliser l'instance initialisée  
          
        # Convertir conversation_id en UUID  
        try:  
            conversation_uuid = uuid.UUID(conversation_id)  
        except ValueError:  
            raise HTTPException(status_code=400, detail="Invalid conversation_id format")  
  
        logger.info(f"Attempting to delete conversation {conversation_uuid} for user {user_id}")  
  
        # Vérifier que la conversation existe et appartient à l'utilisateur  
        conversation_result = await client.table('conversations').select('*').eq('conversation_id', conversation_uuid).eq('user_id', user_id).execute()  
  
        if not conversation_result.data:  
            logger.error(f"Conversation {conversation_uuid} not found or user_id mismatch")  
            raise HTTPException(status_code=404, detail="Conversation not found")  
  
        # Supprimer tous les messages associés d'abord  
        messages_delete_result = await client.table('messages').delete().eq('conversation_id', conversation_uuid).execute()  
          
        logger.info(f"Deleted {len(messages_delete_result.data) if messages_delete_result.data else 0} messages")  
  
        # Supprimer la conversation avec une vérification plus robuste  
        delete_result = await client.table('conversations').delete().eq('conversation_id', conversation_uuid).eq('user_id', user_id).execute()  
  
        # Vérifier le succès de la suppression  
        if not delete_result.data or len(delete_result.data) == 0:  
            # Vérifier si la conversation existe encore  
            check_result = await client.table('conversations').select('*').eq('conversation_id', conversation_uuid).execute()  
              
            if check_result.data:  
                logger.error(f"Conversation still exists after delete attempt")  
                raise HTTPException(status_code=403, detail="Permission denied or conversation is protected")  
            else:  
                logger.warning(f"Conversation may have been already deleted")  
  
        logger.info(f"Successfully deleted conversation {conversation_uuid}")  
        
        return {"message": "Conversation deleted successfully"}  
  
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        logger.info(f"Conversation data before delete: {conversation_result.data[0]}")  
        logger.info(f"User ID from token: {user_id}")  
        logger.info(f"Conversation user_id: {conversation_result.data[0].get('user_id')}") 
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

    
  
@router.get("/{conversation_id}/stats", response_model=ConversationStats)  
async def get_conversation_stats(  
    conversation_id: str,  
    request: Request,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Récupérer les statistiques d'une conversation"""  
    try:  
        # Initialiser la connexion Supabase  
        client = await db.client  
          
        # Vérifier que la conversation existe et appartient à l'utilisateur  
        conversation_result = await client.table('conversations').select('*').eq('conversation_id', conversation_id).eq('user_id', user_id).execute()  
          
        if not conversation_result.data:  
            raise HTTPException(status_code=404, detail="Conversation not found")  
          
        # Compter les messages  
        messages_result = await client.table('messages').select('*', count='exact').eq('conversation_id', conversation_id).execute()  
          
        total_messages = messages_result.count or 0  
          
        # Récupérer le dernier message pour la dernière activité  
        last_message_result = await client.table('messages').select('timestamp').eq('conversation_id', conversation_id).order('timestamp', desc=True).limit(1).execute()  
          
        last_activity = None  
        if last_message_result.data:  
            timestamp_str = last_message_result.data[0]['timestamp']  
            if timestamp_str.endswith('Z'):  
                timestamp_str = timestamp_str.replace('Z', '+00:00')  
            last_activity = datetime.fromisoformat(timestamp_str)  
          
        return ConversationStats(  
            total_conversations=1,  
            total_messages=total_messages,  
            last_activity=last_activity  
        )  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Error fetching conversation stats {conversation_id}: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to fetch conversation stats")  
  
@router.post("/{conversation_id}/archive")  
async def archive_conversation(  
    conversation_id: str,  
    request: Request,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Archiver une conversation"""  
    try:  
        # Mettre à jour les métadonnées pour marquer comme archivée  
        update_data = ConversationUpdate(  
            metadata={"archived": True, "archived_at": datetime.utcnow().isoformat()}  
        )  
          
        await update_conversation(conversation_id, update_data, request, user_id)  
          
        return {"message": "Conversation archived successfully"}  
          
    except Exception as e:  
        logger.error(f"Error archiving conversation {conversation_id}: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to archive conversation")  
  
@router.post("/{conversation_id}/unarchive")  
async def unarchive_conversation(  
    conversation_id: str,  
    request: Request,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Désarchiver une conversation"""  
    try:  
        # Mettre à jour les métadonnées pour retirer le marquage d'archive  
        update_data = ConversationUpdate(  
            metadata={"archived": False, "unarchived_at": datetime.utcnow().isoformat()}  
        )  
          
        await update_conversation(conversation_id, update_data, request, user_id)  
          
        return {"message": "Conversation unarchived successfully"}  
          
    except Exception as e:  
        logger.error(f"Error unarchiving conversation {conversation_id}: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to unarchive conversation")  
  
@router.get("/stats", response_model=ConversationStats)  
async def get_user_conversation_stats(  
    request: Request,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Récupérer les statistiques globales des conversations de l'utilisateur"""  
    try:  
        # Initialiser la connexion Supabase  
        client = await db.client  
          
        # Compter le nombre total de conversations  
        conversations_result = await client.table('conversations').select('*', count='exact').eq('user_id', user_id).execute()  
          
        total_conversations = conversations_result.count or 0  
          
        # Compter le nombre total de messages  
        messages_result = await client.table('messages').select('*', count='exact').in_('conversation_id', [conv['conversation_id'] for conv in conversations_result.data]).execute()  
          
        total_messages = messages_result.count or 0  
          
        # Récupérer la dernière activité  
        last_activity = None  
        if conversations_result.data:  
            last_conversation = await client.table('conversations').select('updated_at').eq('user_id', user_id).order('updated_at', desc=True).limit(1).execute()  
              
            if last_conversation.data:  
                timestamp_str = last_conversation.data[0]['updated_at']  
                if timestamp_str.endswith('Z'):  
                    timestamp_str = timestamp_str.replace('Z', '+00:00')  
                last_activity = datetime.fromisoformat(timestamp_str)  
          
        return ConversationStats(  
            total_conversations=total_conversations,  
            total_messages=total_messages,  
            last_activity=last_activity  
        )  
          
    except Exception as e:  
        logger.error(f"Error fetching user conversation stats: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to fetch conversation stats")  
  
@router.get("/search")  
async def search_conversations(  
    request: Request,  
    query: str,  
    limit: int = 20,  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Rechercher dans les conversations par titre ou contenu"""  
    try:  
        # Initialiser la connexion Supabase  
        client = await db.client  
          
        # Rechercher dans les titres de conversations  
        conversations_result = await client.table('conversations').select('*').eq('user_id', user_id).ilike('title', f'%{query}%').order('updated_at', desc=True).limit(limit).execute()  
          
        # Rechercher dans le contenu des messages  
        messages_result = await client.table('messages').select('conversation_id, content').ilike('content', f'%{query}%').execute()  
          
        # Récupérer les conversations correspondantes aux messages trouvés  
        message_conversation_ids = list(set([msg['conversation_id'] for msg in messages_result.data]))  
          
        if message_conversation_ids:  
            message_conversations_result = await client.table('conversations').select('*').eq('user_id', user_id).in_('conversation_id', message_conversation_ids).order('updated_at', desc=True).execute()  
        else:  
            message_conversations_result = {'data': []}  
          
        # Combiner et dédupliquer les résultats  
        all_conversations = {}  
          
        # Ajouter les conversations trouvées par titre  
        for conv in conversations_result.data:  
            all_conversations[conv['conversation_id']] = conv  
          
        # Ajouter les conversations trouvées par contenu de message  
        for conv in message_conversations_result.data:  
            all_conversations[conv['conversation_id']] = conv  
          
        # Convertir en liste et formater  
        results = []  
        for conv in list(all_conversations.values())[:limit]:  
            # Gérer le format de timestamp  
            created_at_str = conv['created_at']  
            updated_at_str = conv['updated_at']  
              
            if created_at_str.endswith('Z'):  
                created_at_str = created_at_str.replace('Z', '+00:00')  
            if updated_at_str.endswith('Z'):  
                updated_at_str = updated_at_str.replace('Z', '+00:00')  
              
            results.append(ConversationResponse(  
                conversation_id=conv['conversation_id'],  
                user_id=conv['user_id'],  
                title=conv['title'],  
                created_at=datetime.fromisoformat(created_at_str),  
                updated_at=datetime.fromisoformat(updated_at_str),  
                metadata=conv.get('metadata', {})  
            ))  
          
        # Trier par date de mise à jour  
        results.sort(key=lambda x: x.updated_at, reverse=True)  
          
        logger.info(f"Search for '{query}' returned {len(results)} conversations")  
          
        return {  
            "query": query,  
            "total_results": len(results),  
            "conversations": results  
        }  
          
    except Exception as e:  
        logger.error(f"Error searching conversations: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to search conversations")  
  
@router.post("/bulk-delete")  
async def bulk_delete_conversations(  
    request: Request,  
    conversation_ids: List[str],  
    user_id: str = Depends(get_current_user_id_from_jwt)  
):  
    """Supprimer plusieurs conversations en lot"""  
    try:  
        # Initialiser la connexion Supabase  
        client = await db.client  
          
        # Vérifier que toutes les conversations appartiennent à l'utilisateur  
        conversations_result = await client.table('conversations').select('conversation_id').eq('user_id', user_id).in_('conversation_id', conversation_ids).execute()  
          
        valid_conversation_ids = [conv['conversation_id'] for conv in conversations_result.data]  
          
        if len(valid_conversation_ids) != len(conversation_ids):  
            invalid_ids = set(conversation_ids) - set(valid_conversation_ids)  
            logger.warning(f"Invalid conversation IDs for user {user_id}: {invalid_ids}")  
          
        if not valid_conversation_ids:  
            raise HTTPException(status_code=404, detail="No valid conversations found")  
          
        # Supprimer tous les messages associés  
        messages_delete_result = await client.table('messages').delete().in_('conversation_id', valid_conversation_ids).execute()  
          
        # Supprimer les conversations  
        conversations_delete_result = await client.table('conversations').delete().eq('user_id', user_id).in_('conversation_id', valid_conversation_ids).execute()  
          
        deleted_count = len(conversations_delete_result.data) if conversations_delete_result.data else 0  
          
        logger.info(f"Bulk deleted {deleted_count} conversations for user {user_id}")  
          
        return {  
            "message": f"Successfully deleted {deleted_count} conversations",  
            "deleted_count": deleted_count,  
            "deleted_conversation_ids": valid_conversation_ids,  
            "invalid_conversation_ids": list(set(conversation_ids) - set(valid_conversation_ids))  
        }  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Error in bulk delete: {str(e)}")  
        raise HTTPException(status_code=500, detail="Failed to delete conversations")



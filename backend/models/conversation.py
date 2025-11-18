from pydantic import BaseModel, Field  
from datetime import datetime  
from typing import Optional  
import uuid  
  
class ConversationCreate(BaseModel):  
    title: str  
    metadata: dict = Field(default_factory=dict)  
  
class Conversation(BaseModel):  
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))  
    user_id: str  
    title: str  
    created_at: datetime = Field(default_factory=datetime.utcnow)  
    updated_at: datetime = Field(default_factory=datetime.utcnow)  
    metadata: dict = Field(default_factory=dict)  
  
class MessageCreate(BaseModel):  
    content: str  
    metadata: dict = Field(default_factory=dict)  
  
class Message(BaseModel):  
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))  
    conversation_id: str  
    role: str  # "user" ou "assistant"  
    content: str  
    timestamp: datetime = Field(default_factory=datetime.utcnow)  
    metadata: dict = Field(default_factory=dict)

class VoiceMessageCreate(BaseModel):  
    audio_data: str  # Base64 encoded audio  
    audio_format: str = "webm"  # ou "mp3", "wav", etc.  
    metadata: dict = {}

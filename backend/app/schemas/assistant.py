from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SourceCitation(BaseModel):
    name: str
    authority: Optional[str] = "Government of India"
    url: Optional[str] = ""
    last_verified_at: Optional[Union[str, datetime]] = None
    scheme_id: Optional[int] = None
    slug: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    language: Optional[str] = "en"
    user_profile_context: Optional[Dict[str, Any]] = None

class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: List[SourceCitation] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []
    model_config = ConfigDict(from_attributes=True)

class ChatResponse(BaseModel):
    session_id: int
    reply: str
    sources: List[SourceCitation] = []
    suggested_questions: List[str] = []

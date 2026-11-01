from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_optional_current_user
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.schemas.assistant import ChatRequest, ChatResponse, ChatSessionResponse, ChatMessageResponse
from app.services.rag_assistant import RAGAssistantService

router = APIRouter(prefix="/assistant", tags=["SchemeSahayak AI Assistant"])

@router.post("/chat", response_model=ChatResponse)
def chat_with_assistant(
    chat_req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user)
) -> Any:
    user_id = current_user.id if current_user else None

    # Retrieve or create session
    session = None
    if chat_req.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == chat_req.session_id).first()
    
    if not session:
        session_title = chat_req.message[:40] + ("..." if len(chat_req.message) > 40 else "")
        session = ChatSession(user_id=user_id, title=session_title)
        db.add(session)
        db.commit()
        db.refresh(session)

    # Save User message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=chat_req.message
    )
    db.add(user_msg)
    db.commit()

    # Pass user profile context if available
    profile_ctx = chat_req.user_profile_context
    if not profile_ctx and current_user and current_user.profile:
        profile_ctx = {
            "state_code": current_user.profile.state_code,
            "age": current_user.profile.age,
            "gender": current_user.profile.gender,
            "occupation": current_user.profile.occupation,
            "annual_income": current_user.profile.annual_income,
            "caste_category": current_user.profile.caste_category
        }

    # Generate RAG grounded answer
    rag_response = RAGAssistantService.generate_grounded_response(
        db=db,
        query=chat_req.message,
        session_id=session.id,
        requested_lang=chat_req.language or "en",
        user_profile=profile_ctx
    )

    # Save Assistant message
    sources_dict = [s.model_dump() for s in rag_response.sources]
    asst_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=rag_response.reply,
        sources=sources_dict
    )
    db.add(asst_msg)
    db.commit()

    return rag_response

@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_user_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user)
) -> Any:
    if not current_user:
        return []
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(ChatSession.updated_at.desc()).all()
    return sessions

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_session_history(
    session_id: int,
    db: Session = Depends(get_db)
) -> Any:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session

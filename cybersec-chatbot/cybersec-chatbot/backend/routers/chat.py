"""
chat.py — Chat router.

Endpoints:
  POST /chat/              Send a message and get an AI reply.
  GET  /chat/history/{id} Retrieve full session history.
  DELETE /chat/history/{id} Clear a session.
"""

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import get_settings
from ..models.chat_models import ChatRequest, ChatResponse, HistoryResponse, ChatMessage
from ..services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])
_svc = ChatService()
_limiter = Limiter(key_func=get_remote_address)
settings = get_settings()


@router.post("/", response_model=ChatResponse, summary="Send a message to CyberGuard")
@_limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def chat(request: Request, req: ChatRequest) -> ChatResponse:
    """
    Send a user message and receive an AI-powered cybersecurity response.

    - Optionally runs threat analysis on the message before replying.
    - Maintains conversation context per `session_id`.
    - Returns threat level and detected flags alongside the reply.
    """
    try:
        return await _svc.chat(
            session_id=req.session_id,
            message=req.message,
            include_threat=req.include_threat_analysis,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat error: {exc}") from exc


@router.get(
    "/history/{session_id}",
    response_model=HistoryResponse,
    summary="Get conversation history",
)
async def get_history(session_id: str) -> HistoryResponse:
    """Retrieve the full message history for a session."""
    messages = await _svc.get_history(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found or empty.")
    return HistoryResponse(
        session_id=session_id,
        messages=[ChatMessage(**m) for m in messages],
    )


@router.delete(
    "/history/{session_id}",
    summary="Clear conversation history",
)
async def clear_history(session_id: str) -> dict:
    """Delete all stored messages for a session (GDPR / privacy wipe)."""
    await _svc.clear_history(session_id)
    return {"message": f"History for session '{session_id}' cleared."}

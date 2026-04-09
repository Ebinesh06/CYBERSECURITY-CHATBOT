"""chat_models.py — Pydantic schemas for the /chat endpoint."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    message: str = Field(..., min_length=1, max_length=2000)
    include_threat_analysis: bool = True


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    threat_level: Literal["safe", "suspicious", "critical"] = "safe"
    threat_type: str = "none"
    threat_flags: list[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]

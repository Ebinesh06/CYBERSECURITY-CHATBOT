"""threat_models.py — Pydantic schemas for the /analyze endpoints."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class ThreatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class ThreatResponse(BaseModel):
    threat_level: Literal["safe", "suspicious", "critical"]
    threat_type: str = "unknown"  # e.g., "phishing", "malware", "ddos", etc.
    confidence: float = Field(..., ge=0.0, le=1.0)
    detected_patterns: list[str]
    advice: str
    ai_analysis: Optional[str] = None


class PasswordRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=256)


class PasswordResponse(BaseModel):
    strength: Literal["very_weak", "weak", "moderate", "strong", "very_strong"]
    score: int = Field(..., ge=0, le=100)
    entropy_bits: float
    issues: list[str]
    suggestions: list[str]

"""
analyze.py — Threat and password analysis router.

Endpoints:
  POST /analyze/          Analyse text for phishing/malware patterns.
  POST /analyze/password  Evaluate password strength.
"""

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import get_settings
from ..models.threat_models import (
    ThreatRequest, ThreatResponse,
    PasswordRequest, PasswordResponse,
)
from ..services.threat_service import ThreatService
from ..services.password_service import PasswordService

router = APIRouter(prefix="/analyze", tags=["Analysis"])
_threat_svc = ThreatService()
_pw_svc = PasswordService()
_limiter = Limiter(key_func=get_remote_address)
settings = get_settings()


@router.post("/", response_model=ThreatResponse, summary="Analyse text for threats")
@_limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def analyze_threat(request: Request, req: ThreatRequest) -> ThreatResponse:
    """
    Run two-stage threat analysis on the provided text:
    1. Fast keyword/regex scan (deterministic, zero API cost).
    2. GPT escalation when confidence is low or the text is ambiguous.

    Returns threat level, confidence score, detected patterns, and advice.
    """
    try:
        return await _threat_svc.analyze(req.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis error: {exc}") from exc


@router.post(
    "/password",
    response_model=PasswordResponse,
    summary="Check password strength",
)
def analyze_password(req: PasswordRequest) -> PasswordResponse:
    """
    Evaluate password strength using Shannon entropy and pattern checks.

    Returns:
    - Strength label (very_weak → very_strong)
    - Entropy in bits
    - Specific weaknesses found
    - Actionable improvement suggestions

    Note: the password is NEVER stored or logged.
    """
    return _pw_svc.evaluate(req.password)

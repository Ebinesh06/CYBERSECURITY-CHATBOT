"""
test_threat.py — Unit tests for threat analysis.

Run with:  pytest backend/tests/ -v
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.threat_service import ThreatService, _classify_level, _build_advice
from backend.utils.phishing_keywords import compute_keyword_score


# ── Keyword scanner tests (pure, no mocking needed) ──────────────────────

def test_safe_message():
    score, patterns = compute_keyword_score("What is two-factor authentication?")
    assert score < 0.35
    assert patterns == []


def test_phishing_otp():
    score, patterns = compute_keyword_score(
        "URGENT: Your bank account is suspended. Share your OTP immediately to unlock it."
    )
    assert score >= 0.7
    assert any("otp" in p.lower() for p in patterns)
    assert any("urgency" in p.lower() for p in patterns)


def test_financial_lure():
    score, patterns = compute_keyword_score(
        "Congratulations! You have won a lottery prize. Claim your prize now!"
    )
    assert score >= 0.5
    assert any("financial_lure" in p for p in patterns)


def test_suspicious_url():
    score, _ = compute_keyword_score("Click here to login: http://192.168.1.254/secure/login")
    assert score >= 0.5


def test_malware_signal():
    score, patterns = compute_keyword_score(
        "Please disable antivirus and run this cmd.exe script to fix your PC."
    )
    assert score >= 0.8
    assert any("evasion" in p or "execution" in p for p in patterns)


def test_sensitive_data_pattern():
    score, patterns = compute_keyword_score("My card number is 4111 1111 1111 1111")
    assert score >= 0.5
    assert any("sensitive data" in p for p in patterns)


# ── Classifier and advice helpers ─────────────────────────────────────────

def test_classify_level_safe():
    assert _classify_level(0.1, []) == "safe"


def test_classify_level_suspicious():
    assert _classify_level(0.5, ["urgency: 'urgent'"]) == "suspicious"


def test_classify_level_phishing():
    assert _classify_level(0.8, ["urgency: 'urgent'"]) == "phishing"


def test_classify_level_malware():
    assert _classify_level(0.9, ["malware: 'virus detected'"]) == "malware"


def test_advice_mentions_otp():
    advice = _build_advice("phishing", ["sensitive_data: 'otp'"])
    assert "OTP" in advice or "otp" in advice.lower()


# ── ThreatService integration (mocked OpenAI) ─────────────────────────────

@pytest.mark.asyncio
async def test_obvious_phishing_no_ai_needed():
    """High-confidence phishing should NOT call the AI (saves tokens)."""
    svc = ThreatService()
    with patch.object(svc, "_ai_classify", new_callable=AsyncMock) as mock_ai:
        result = await svc.analyze(
            "URGENT: Account suspended! Share your OTP and password immediately."
        )
    mock_ai.assert_not_called()  # Stage 1 confidence is high enough
    assert result.threat_level in ("phishing", "suspicious")
    assert result.confidence >= 0.5


@pytest.mark.asyncio
async def test_ambiguous_message_escalates_to_ai():
    """Low-confidence message should escalate to AI."""
    svc = ThreatService()
    mock_response = "phishing — the message creates urgency and requests credentials."
    with patch.object(svc, "_ai_classify", new_callable=AsyncMock, return_value=mock_response):
        result = await svc.analyze("Hey, can you quickly update your details on our portal?")
    assert result.ai_analysis is not None
    assert result.threat_level in ("phishing", "suspicious", "safe")


@pytest.mark.asyncio
async def test_safe_message_stays_safe():
    svc = ThreatService()
    with patch.object(svc, "_ai_classify", new_callable=AsyncMock, return_value="safe — no threats."):
        result = await svc.analyze("How do I enable two-factor authentication on Gmail?")
    assert result.threat_level == "safe"

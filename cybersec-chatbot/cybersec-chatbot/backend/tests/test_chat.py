"""
test_chat.py — Integration tests for the /chat router.

Uses FastAPI's TestClient with mocked services so tests run without
a live MongoDB or OpenAI connection.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

# We need to mock DB before importing the app
import sys
from unittest.mock import MagicMock

# Patch database before app import
mock_db = MagicMock()
mock_db.sessions.find_one = AsyncMock(return_value=None)
mock_db.sessions.update_one = AsyncMock(return_value=None)
mock_db.sessions.delete_one = AsyncMock(return_value=None)


@pytest.fixture
def client():
    with patch("backend.database.connect_db", new_callable=AsyncMock), \
         patch("backend.database.close_db",   new_callable=AsyncMock), \
         patch("backend.database.get_database", return_value=mock_db):
        from backend.main import app
        with TestClient(app) as c:
            yield c


def make_chat_payload(message: str = "What is phishing?", session_id: str = "test-session-001"):
    return {"session_id": session_id, "message": message, "include_threat_analysis": False}


# ── Health check ──────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Chat endpoint ─────────────────────────────────────────────────────────

def test_chat_returns_reply(client):
    mock_reply = "Phishing is a social engineering attack where attackers impersonate trusted entities."

    with patch("backend.services.chat_service.AsyncOpenAI") as MockOAI:
        mock_choice = MagicMock()
        mock_choice.message.content = mock_reply
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        instance = MockOAI.return_value
        instance.chat.completions.create = AsyncMock(return_value=mock_completion)

        r = client.post("/chat/", json=make_chat_payload())

    assert r.status_code == 200
    data = r.json()
    assert "reply" in data
    assert data["threat_level"] == "safe"
    assert data["session_id"] == "test-session-001"


def test_chat_validates_short_message(client):
    payload = make_chat_payload(message="")
    r = client.post("/chat/", json=payload)
    assert r.status_code == 422  # Pydantic validation error


def test_chat_validates_long_message(client):
    payload = make_chat_payload(message="x" * 2001)
    r = client.post("/chat/", json=payload)
    assert r.status_code == 422


def test_chat_validates_session_id_too_short(client):
    payload = {"session_id": "ab", "message": "Hello", "include_threat_analysis": False}
    r = client.post("/chat/", json=payload)
    assert r.status_code == 422


# ── History endpoint ──────────────────────────────────────────────────────

def test_history_not_found(client):
    mock_db.sessions.find_one = AsyncMock(return_value=None)
    r = client.get("/chat/history/nonexistent-session-xyz")
    assert r.status_code == 404


def test_history_returns_messages(client):
    mock_db.sessions.find_one = AsyncMock(return_value={
        "session_id": "test-session-001",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"},
        ],
    })
    r = client.get("/chat/history/test-session-001")
    assert r.status_code == 200
    data = r.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"


def test_clear_history(client):
    mock_db.sessions.delete_one = AsyncMock(return_value=None)
    r = client.delete("/chat/history/test-session-001")
    assert r.status_code == 200
    assert "cleared" in r.json()["message"]


# ── Analyze endpoints ─────────────────────────────────────────────────────

def test_analyze_phishing_text(client):
    with patch("backend.services.threat_service.AsyncOpenAI"):
        r = client.post("/analyze/", json={
            "text": "URGENT: Your account is suspended! Share your OTP immediately to verify."
        })
    assert r.status_code == 200
    data = r.json()
    assert data["threat_level"] in ("phishing", "suspicious")
    assert data["confidence"] > 0.5
    assert len(data["detected_patterns"]) > 0
    assert "advice" in data


def test_analyze_safe_text(client):
    with patch("backend.services.threat_service.AsyncOpenAI") as MockOAI:
        instance = MockOAI.return_value
        instance.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="safe — no threats found."))])
        )
        r = client.post("/analyze/", json={"text": "How do I set up two-factor authentication?"})
    assert r.status_code == 200
    assert r.json()["threat_level"] == "safe"


def test_password_very_weak(client):
    r = client.post("/analyze/password", json={"password": "abc"})
    assert r.status_code == 200
    data = r.json()
    assert data["strength"] in ("very_weak", "weak")
    assert data["score"] < 40
    assert len(data["issues"]) > 0


def test_password_strong(client):
    r = client.post("/analyze/password", json={"password": "Xk9#mP2@nQ5!vLw3"})
    assert r.status_code == 200
    data = r.json()
    assert data["strength"] in ("strong", "very_strong")
    assert data["score"] >= 70
    assert data["entropy_bits"] > 80


def test_analyze_empty_text(client):
    r = client.post("/analyze/", json={"text": ""})
    assert r.status_code == 422

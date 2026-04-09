"""
chat_service.py — Orchestrates GPT conversation with context management.

Responsibilities:
  1. Load session history from MongoDB.
  2. Optionally run threat analysis on the incoming message.
  3. Build the OpenAI messages array (system + history + user turn).
  4. Call GPT and persist the updated history.
  5. Return a structured ChatResponse.
"""

from openai import AsyncOpenAI

from ..config import get_settings
from ..database import get_database
from ..models.chat_models import ChatResponse
from .threat_service import ThreatService

# Keep the last N turns to stay within context limits.
MAX_HISTORY_TURNS = 10


class ChatService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        self._threat_svc = ThreatService()

    async def chat(
        self,
        session_id: str,
        message: str,
        include_threat: bool,
    ) -> ChatResponse:
        db = get_database()

        # ── 1. Load history ───────────────────────────────────────────────
        record = await db.sessions.find_one({"session_id": session_id})
        history: list[dict] = record["messages"] if record else []

        # ── 2. Threat analysis ────────────────────────────────────────────
        threat_result = None
        if include_threat:
            threat_result = await self._threat_svc.analyze(message)

        # ── 3. Build messages array ───────────────────────────────────────
        messages: list[dict] = [
            {"role": "system", "content": self._settings.system_prompt}
        ]
        # Inject only the last MAX_HISTORY_TURNS turns
        for turn in history[-MAX_HISTORY_TURNS:]:
            messages.append({"role": turn["role"], "content": turn["content"]})

        # Enrich user content with threat context so GPT tailors its reply
        user_content = message
        if threat_result and threat_result.threat_level != "safe":
            flags = ", ".join(threat_result.detected_patterns[:3])
            user_content = (
                f"[SYSTEM NOTE — Threat detected: {threat_result.threat_level.upper()}. "
                f"Flags: {flags}. Tailor your response to warn the user about these "
                f"specific dangers.]\n\nUser message: {message}"
            )
        messages.append({"role": "user", "content": user_content})

        # ── 4. Call OpenAI ────────────────────────────────────────────────
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.openai_model,
                messages=messages,
                max_tokens=600,
                temperature=0.7,
            )
            reply = response.choices[0].message.content or "I couldn't generate a response."
        except Exception as exc:
            # Fallback response when API is unavailable
            reply = (
                "I'm temporarily unable to access the AI model due to an API error. "
                "However, based on the threat analysis, here's what I can tell you: "
            )
            if threat_result and threat_result.threat_level != "safe":
                reply += threat_result.advice
            else:
                reply += "Your message appears to be safe. Stay vigilant and always verify sender identities!"

        # ── 5. Persist history ────────────────────────────────────────────
        new_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        await db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"session_id": session_id, "messages": new_history}},
            upsert=True,
        )

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            threat_level=threat_result.threat_level if threat_result else "safe",
            threat_type=threat_result.threat_type if threat_result else "none",
            threat_flags=threat_result.detected_patterns[:5] if threat_result else [],
        )

    async def get_history(self, session_id: str) -> list[dict]:
        db = get_database()
        record = await db.sessions.find_one({"session_id": session_id})
        return record["messages"] if record else []

    async def clear_history(self, session_id: str) -> None:
        db = get_database()
        await db.sessions.delete_one({"session_id": session_id})

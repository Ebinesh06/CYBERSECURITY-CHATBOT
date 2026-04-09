"""
config.py — Centralised application settings.
All values are read from environment variables (or a .env file).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = "sk-placeholder"
    openai_model: str = "gpt-4o-mini"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "cybersec_chatbot"
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"
    rate_limit_per_minute: int = 30
    system_prompt: str = (
        "You are CyberGuard, an expert cybersecurity awareness assistant. "
        "Your role is to help users identify and avoid digital threats such as "
        "phishing, malware, social engineering, identity theft, and scams. "
        "Always provide clear, actionable advice. When a user shares suspicious "
        "content, analyse it and explain the specific red flags. "
        "If asked about unrelated topics, politely redirect the conversation to "
        "cybersecurity. Never provide advice that could be used offensively. "
        "Keep responses concise and jargon-free for non-technical users."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()

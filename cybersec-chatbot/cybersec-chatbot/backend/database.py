"""
database.py — Async MongoDB connection using Motor.

Motor is the async MongoDB driver for Python. We create a single client
at startup (lifespan) and close it on shutdown, following FastAPI best
practices for connection pooling.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .config import get_settings

_client: Optional[AsyncIOMotorClient] = None


async def connect_db() -> None:
    """Initialise the Motor client.  Call from the app lifespan startup."""
    global _client
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    # Ping to surface connection errors early rather than on first query
    await _client.admin.command("ping")


async def close_db() -> None:
    """Close the Motor client.  Call from the app lifespan shutdown."""
    global _client
    if _client:
        _client.close()
        _client = None


def get_database() -> AsyncIOMotorDatabase:
    """Return the application database.  Raises if not yet connected."""
    if _client is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _client[get_settings().mongodb_db_name]

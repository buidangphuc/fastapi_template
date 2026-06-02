"""Mongo client builder + readiness check (mirrors app/core/redis.py).

``motor`` is an optional dependency (the ``mongo`` extra). It is imported
lazily via ``importlib`` so the platform stays importable — and type-checkable —
without it; the import only runs when ``MONGO_ENABLED`` is true and the
``MongoAddon`` opens.
"""

from __future__ import annotations

import importlib
from typing import Any

from app.core.config import Settings


def build_mongo_client(settings: Settings) -> Any:
    try:
        motor_asyncio = importlib.import_module("motor.motor_asyncio")
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "motor is required when MONGO_ENABLED is true; install the 'mongo' extra"
        ) from exc

    return motor_asyncio.AsyncIOMotorClient(
        settings.MONGODB_URI or "mongodb://localhost:27017",
        serverSelectionTimeoutMS=settings.MONGODB_CONNECTION_TIMEOUT_MS,
    )


async def check_mongo_connection(client: Any) -> None:
    await client.admin.command("ping")

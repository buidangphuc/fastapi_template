"""Thin async wrapper over a motor client scoped to one database.

Lifespan-managed by ``MongoAddon``; never construct at import time (this is the
explicit replacement for the legacy import-time ``mongo_client`` singleton).
Motor types are intentionally ``Any`` so the platform type-checks without the
optional ``motor`` dependency installed.
"""

from __future__ import annotations

from typing import Any


class MongoGateway:
    def __init__(self, client: Any, *, database: str) -> None:
        self._client = client
        self._database_name = database

    @property
    def client(self) -> Any:
        return self._client

    @property
    def database(self) -> Any:
        return self._client[self._database_name]

    def collection(self, name: str) -> Any:
        return self.database[name]

    async def ping(self) -> Any:
        return await self._client.admin.command("ping")

    async def close(self) -> None:
        # motor's AsyncIOMotorClient.close() is synchronous.
        self._client.close()

"""In-memory fake of the motor collection API used by the listing services.

Covers exactly the operations the ported services call: ``find_one``,
``insert_one``, ``update_one`` ($set), ``delete_many``, and
``find(...).sort(...).limit(...)`` with async iteration. No network / no motor.
"""

from __future__ import annotations

import copy
from collections.abc import AsyncIterator
from typing import Any


def _matches(doc: dict[str, Any], query: dict[str, Any]) -> bool:
    return all(doc.get(key) == value for key, value in query.items())


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs

    def sort(self, key: str, direction: int = 1) -> FakeCursor:
        self._docs.sort(key=lambda doc: doc.get(key), reverse=direction < 0)
        return self

    def limit(self, count: int) -> FakeCursor:
        self._docs = self._docs[:count]
        return self

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[dict[str, Any]]:
        for doc in self._docs:
            yield copy.deepcopy(doc)


class FakeCollection:
    def __init__(self) -> None:
        self.docs: list[dict[str, Any]] = []

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for doc in self.docs:
            if _matches(doc, query):
                return copy.deepcopy(doc)
        return None

    def find(self, query: dict[str, Any]) -> FakeCursor:
        return FakeCursor(
            [copy.deepcopy(doc) for doc in self.docs if _matches(doc, query)]
        )

    async def insert_one(self, document: dict[str, Any]) -> None:
        self.docs.append(copy.deepcopy(document))

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        for doc in self.docs:
            if _matches(doc, query):
                doc.update(update.get("$set", {}))
                return

    async def delete_many(self, query: dict[str, Any]) -> None:
        if not query:
            self.docs.clear()
        else:
            self.docs = [doc for doc in self.docs if not _matches(doc, query)]


class FakeMongoGateway:
    def __init__(self) -> None:
        self._collections: dict[str, FakeCollection] = {}

    def collection(self, name: str) -> FakeCollection:
        return self._collections.setdefault(name, FakeCollection())

    async def close(self) -> None:
        return None

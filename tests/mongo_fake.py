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
    for key, value in query.items():
        if key == "$expr":
            if not _eval_expr(doc, value):
                return False
            continue
        if doc.get(key) != value:
            return False
    return True


def _eval_expr(doc: dict[str, Any], expr: dict[str, Any]) -> bool:
    if "$lte" in expr:
        left, right = expr["$lte"]
        return _eval_value(doc, left) <= _eval_value(doc, right)
    raise NotImplementedError(expr)


def _eval_value(doc: dict[str, Any], value: Any) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        return doc.get(value[1:], 0)
    if isinstance(value, dict) and "$add" in value:
        return sum(_eval_value(doc, item) for item in value["$add"])
    return value


def _apply_update(
    doc: dict[str, Any],
    update: dict[str, Any],
    *,
    is_insert: bool = False,
) -> None:
    if is_insert:
        for key, value in update.get("$setOnInsert", {}).items():
            doc[key] = value
    for key, value in update.get("$set", {}).items():
        doc[key] = value
    for key, value in update.get("$inc", {}).items():
        doc[key] = doc.get(key, 0) + value


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

    async def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> None:
        for doc in self.docs:
            if _matches(doc, query):
                _apply_update(doc, update)
                return
        if upsert:
            new_doc = {
                key: value for key, value in query.items() if not key.startswith("$")
            }
            _apply_update(new_doc, update, is_insert=True)
            self.docs.append(copy.deepcopy(new_doc))

    async def find_one_and_update(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        return_document: Any = None,
    ) -> dict[str, Any] | None:
        for doc in self.docs:
            if _matches(doc, query):
                before = copy.deepcopy(doc)
                _apply_update(doc, update)
                if return_document:
                    return copy.deepcopy(doc)
                return before
        return None

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

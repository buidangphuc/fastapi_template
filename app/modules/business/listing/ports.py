"""Port Protocols for the listing generator domain (hexagonal boundary).

Scaffold only: signatures sketch the seams the Phase 1/2 adapters implement
(Mongo usage/listing stores, Google Maps nearby, BDS project lookup, and the
ai/llm-backed description generator). No implementations here.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.modules.business.listing.config import (
    AddressVersionType,
    LanguageType,
    StyleType,
    ToneType,
)
from app.modules.business.listing.schemas import AllParams


class NearbyProvider(Protocol):
    async def search(
        self,
        place: str | None,
        lat: float | None,
        lng: float | None,
    ) -> dict[str, list[str]] | None: ...


class ProjectProvider(Protocol):
    async def get_summary(self, project_id: str | None) -> dict[str, Any] | None: ...


class UsageQuota(Protocol):
    async def get_remaining(self, user_id: str) -> dict[str, Any]: ...

    async def increase(self, user_id: str, count: int = 1) -> dict[str, Any]: ...


class ListingStore(Protocol):
    async def create(self, listing: dict[str, Any]) -> None: ...

    async def last_ai_listings(
        self,
        user_id: str,
        style: StyleType,
        limit: int = 2,
    ) -> list[dict[str, Any]]: ...


class DescriptionGenerator(Protocol):
    async def agenerate(
        self,
        *,
        language: LanguageType,
        tone: ToneType,
        style: StyleType,
        params: AllParams,
        template_id: str,
        address_version: AddressVersionType,
    ) -> dict[str, Any]: ...

"""Template selection service for listing generation."""

from __future__ import annotations

from app.core.config import Settings
from app.modules.business.listing.generation.templates import select_template_from_ids
from app.modules.business.listing.stores.listing import ListingStore
from app.modules.business.listing.types import StyleType, TemplateResponse


class ListingTemplateSelectionService:
    def __init__(self, store: ListingStore, settings: Settings) -> None:
        self._store = store
        self._settings = settings

    async def select(self, user_id: str, style: StyleType) -> TemplateResponse:
        style = StyleType(style)
        if style == StyleType.SIMPLE:
            return select_template_from_ids([], style, self._settings)

        template_ids = await self._store.get_recent_ai_template_ids(
            user_id=user_id,
            style=style,
            limit=2,
        )
        return select_template_from_ids(template_ids, style, self._settings)

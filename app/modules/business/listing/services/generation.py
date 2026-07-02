"""Application services for legacy listing generation endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.config import Settings
from app.modules.business.listing.generation.description import DescriptionGenerator
from app.modules.business.listing.generation.pair_address import PairAddressGenerator
from app.modules.business.listing.models import Listing
from app.modules.business.listing.schemas import AllParams, PairAddressParams
from app.modules.business.listing.services.template_selection import (
    ListingTemplateSelectionService,
)
from app.modules.business.listing.stores.listing import ListingStore
from app.modules.business.listing.types import (
    AddressVersionType,
    AuthorType,
    LanguageType,
    ProfessionalTemplateType,
    SimpleTemplateType,
    StyleType,
    ToneType,
)


@dataclass(frozen=True)
class ListingGenerationResult:
    title: str
    description: str


def _tone_for_style(style: StyleType) -> ToneType:
    return ToneType.SIMPLE if style == StyleType.SIMPLE else ToneType.PROFESSIONAL


def _build_listing(
    *,
    user_id: str,
    listing_id: str,
    style: StyleType,
    params: AllParams,
    generated: dict[str, Any],
    template_id: ProfessionalTemplateType | SimpleTemplateType,
    settings: Settings,
) -> Listing:
    return Listing(
        user_id=user_id,
        listing_id=listing_id,
        description=generated["description"],
        title=generated["title"],
        style=style,
        prompt=generated["prompt"],
        author=AuthorType.AI,
        created_date=datetime.now(),
        template_id=template_id,
        prompt_tokens=generated["tokens"]["usage"]["prompt_tokens"],
        completion_tokens=generated["tokens"]["usage"]["completion_tokens"],
        generating_time=generated["generating_time"],
        llm_model_name=generated["llm_model_name"],
        user_input=params.model_dump_json(),
        platform=params.platform,
        version=settings.VERSION,
        prompt_version=generated.get("prompt_version"),
    )


class DescriptionGenerationService:
    def __init__(
        self,
        *,
        generator: DescriptionGenerator,
        store: ListingStore,
        template_selection: ListingTemplateSelectionService,
        settings: Settings,
    ) -> None:
        self._generator = generator
        self._store = store
        self._template_selection = template_selection
        self._settings = settings

    async def generate(
        self,
        *,
        user_id: str,
        listing_id: str,
        style: StyleType,
        params: AllParams,
        address_version: AddressVersionType,
    ) -> ListingGenerationResult:
        template = await self._template_selection.select(user_id, style)
        generated = await self._generator.agenerate(
            language=LanguageType.VI,
            tone=_tone_for_style(style),
            style=style,
            params=params,
            template_id=template.selected_template,
            address_version=address_version,
        )
        listing = _build_listing(
            user_id=user_id,
            listing_id=listing_id,
            style=style,
            params=params,
            generated=generated,
            template_id=template.selected_template,
            settings=self._settings,
        )
        await self._store.create_listing(listing)
        return ListingGenerationResult(
            title=generated["title"],
            description=generated["description"],
        )


class PairAddressGenerationService:
    def __init__(
        self,
        *,
        generator: PairAddressGenerator,
        store: ListingStore,
        template_selection: ListingTemplateSelectionService,
        settings: Settings,
    ) -> None:
        self._generator = generator
        self._store = store
        self._template_selection = template_selection
        self._settings = settings

    async def generate(
        self,
        *,
        user_id: str,
        listing_id: str,
        style: StyleType,
        params: PairAddressParams,
        address_version: AddressVersionType,
    ) -> ListingGenerationResult:
        template = await self._template_selection.select(user_id, style)
        generated = await self._generator.agenerate(
            language=LanguageType.VI,
            tone=_tone_for_style(style),
            style=style,
            params=params,
            template_id=template.selected_template,
            address_version=address_version,
        )
        listing = _build_listing(
            user_id=user_id,
            listing_id=listing_id,
            style=style,
            params=params,
            generated=generated,
            template_id=template.selected_template,
            settings=self._settings,
        )
        await self._store.create_listing(listing)
        return ListingGenerationResult(
            title=generated["title"],
            description=generated["description"],
        )

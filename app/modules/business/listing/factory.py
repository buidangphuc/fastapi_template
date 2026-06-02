"""Lifespan provisioning for the listing generator stack.

The shared httpx client and the listing chat model are built once in the
lifespan (via ``ListingGeneratorAddon``) and stored on ``ApplicationResources``;
per-request the endpoint assembles the nearby/project services + generator from
them. Sampling params are pinned on the chat model for behavior parity.
``langchain``/``httpx`` are imported lazily so the module stays importable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import Settings

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.bootstrap.resources import ApplicationResources


def build_listing_chat_model(settings: Settings) -> Any:
    if not settings.CHAT_MODEL:
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        return FakeListChatModel(responses=["fake response"])

    from langchain.chat_models import init_chat_model

    return init_chat_model(
        settings.CHAT_MODEL,
        temperature=settings.LISTING_LLM_TEMPERATURE,
        top_p=settings.LISTING_LLM_TOP_P,
        model_kwargs={
            "presence_penalty": settings.LISTING_LLM_PRESENCE_PENALTY,
            "frequency_penalty": settings.LISTING_LLM_FREQUENCY_PENALTY,
        },
    )


def build_listing_http_client(settings: Settings) -> Any:
    import httpx

    return httpx.AsyncClient(timeout=settings.GMAP_PG_SEARCH_TIMEOUT)


class ListingGeneratorAddon:
    name = "listing_generator"

    def is_enabled(self, settings: Settings) -> bool:
        return settings.MONGO_ENABLED

    async def open(
        self,
        app: FastAPI,
        resources: ApplicationResources,
        settings: Settings,
    ) -> None:
        resources.listing_http_client = build_listing_http_client(settings)
        resources.listing_chat_model = build_listing_chat_model(settings)

    async def close(self, app: FastAPI, resources: ApplicationResources) -> None:
        client = resources.listing_http_client
        if client is not None:
            await client.aclose()
            resources.listing_http_client = None
        resources.listing_chat_model = None

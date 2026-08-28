"""Central application service composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.core.config import Settings
from app.modules.ai.llm.runtime import LLMInstance, build_llm_instance
from app.modules.business.listing.generation.description import DescriptionGenerator
from app.modules.business.listing.generation.pair_address import PairAddressGenerator
from app.modules.business.listing.generation.prompt_provider import (
    FilePromptProvider,
    LangfusePromptProvider,
)
from app.modules.business.listing.integrations.nearby import NearbySearchService
from app.modules.business.listing.integrations.project import ProjectService
from app.modules.business.listing.services.generation import (
    DescriptionGenerationService,
    PairAddressGenerationService,
)
from app.modules.business.listing.services.listing import ListingService
from app.modules.business.listing.services.quota import build_listing_quota_service
from app.modules.business.listing.services.template_selection import (
    ListingTemplateSelectionService,
)
from app.modules.business.listing.stores.listing import ListingStore

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.bootstrap.resources import ApplicationResources
    from app.modules.platform.mongo.gateway import MongoGateway
    from app.modules.platform.quota.service import QuotaService

LISTING_SERVICE_NAME = "listing"


@dataclass
class ListingRuntime:
    service: ListingService
    http_client: Any

    async def close(self) -> None:
        await self.http_client.aclose()


def build_listing_llm_instance(settings: Settings) -> LLMInstance:
    def model_builder(target: str) -> Any:
        from langchain.chat_models import init_chat_model

        return init_chat_model(
            target,
            temperature=settings.LISTING_LLM_TEMPERATURE,
            top_p=settings.LISTING_LLM_TOP_P,
            model_kwargs={
                "presence_penalty": settings.LISTING_LLM_PRESENCE_PENALTY,
                "frequency_penalty": settings.LISTING_LLM_FREQUENCY_PENALTY,
            },
        )

    return build_llm_instance(
        settings,
        instance_id="listing",
        service_name="listing-generator",
        model_builder=model_builder,
    )


def build_listing_vertex_chat_model(settings: Settings) -> Any:
    """Build the Gemini/Vertex chat model via the SAME ``init_chat_model``
    factory as OpenAI — only the provider prefix differs.

    ``init_chat_model`` routes the ``google_vertexai:`` prefix to ``ChatVertexAI``
    and imports the Vertex SDK lazily, only when this provider is requested (i.e.
    when VERTEX_ENABLED). Auth + GCP project/region come from Application Default
    Credentials: set GOOGLE_APPLICATION_CREDENTIALS to the account_service.json
    path (the JSON carries the project; region uses the Vertex default).
    """
    from langchain.chat_models import init_chat_model

    return init_chat_model(
        f"google_vertexai:{settings.VERTEX_MODEL}",
        temperature=settings.LISTING_LLM_TEMPERATURE,
        top_p=settings.LISTING_LLM_TOP_P,
    )


def build_listing_http_client(settings: Settings) -> Any:
    import httpx

    return httpx.AsyncClient(timeout=settings.GMAP_PG_SEARCH_TIMEOUT)


def build_listing_runtime(
    *,
    settings: Settings,
    mongo: MongoGateway,
    quota: QuotaService,
    http_client: Any | None = None,
    chat_model: Any | None = None,
    gemini_chat_model: Any | None = None,
    tracker: Any | None = None,
    prompt_provider: Any | None = None,
) -> ListingRuntime:
    client = (
        http_client if http_client is not None else build_listing_http_client(settings)
    )
    if chat_model is None:
        llm = build_listing_llm_instance(settings)
        chat_model = llm.chat_model
        tracker = llm.tracker

    prompt_provider = prompt_provider or LangfusePromptProvider(
        tracker, fallback=FilePromptProvider()
    )
    trace_config = tracker.trace_config() if tracker is not None else {}
    store = ListingStore(mongo, settings)
    template_selection = ListingTemplateSelectionService(store, settings)
    nearby = NearbySearchService(client, settings)
    project = ProjectService(client, chat_model, mongo, settings, prompt_provider)
    description_generation = DescriptionGenerationService(
        generator=DescriptionGenerator(
            nearby_service=nearby,
            project_service=project,
            chat_model=chat_model,
            settings=settings,
            trace_config=trace_config,
        ),
        store=store,
        template_selection=template_selection,
        settings=settings,
    )
    pair_address_generation = PairAddressGenerationService(
        generator=PairAddressGenerator(
            nearby_service=nearby,
            project_service=project,
            chat_model=chat_model,
            settings=settings,
            trace_config=trace_config,
        ),
        store=store,
        template_selection=template_selection,
        settings=settings,
    )
    # Optional Gemini/Vertex variant powering POST /pair_address/stream/gemini.
    # Built when Vertex is enabled (or a model is injected for tests); reuses the
    # same context services + prompt, swapping only the chat model. Building is
    # best-effort: if VERTEX_ENABLED but creds/SDK are unavailable, log and leave
    # it off (the /gemini endpoint returns 501) rather than crash the whole app.
    pair_address_generation_gemini = None
    gemini_model = gemini_chat_model
    if gemini_model is None and settings.VERTEX_ENABLED:
        try:
            gemini_model = build_listing_vertex_chat_model(settings)
        except Exception as exc:
            logger.warning(
                "VERTEX_ENABLED but Gemini model unavailable "
                f"(check GOOGLE_APPLICATION_CREDENTIALS): {exc!r}; "
                "/pair_address/stream/gemini will return 501"
            )
            gemini_model = None
    if gemini_model is not None:
        pair_address_generation_gemini = PairAddressGenerationService(
            generator=PairAddressGenerator(
                nearby_service=nearby,
                project_service=project,
                chat_model=gemini_model,
                settings=settings,
                trace_config=trace_config,
            ),
            store=store,
            template_selection=template_selection,
            settings=settings,
        )
    return ListingRuntime(
        service=ListingService(
            store=store,
            quota=build_listing_quota_service(quota, settings),
            description_generation=description_generation,
            pair_address_generation=pair_address_generation,
            pair_address_generation_gemini=pair_address_generation_gemini,
            settings=settings,
        ),
        http_client=client,
    )


class ApplicationServicesAddon:
    name = "application_services"

    def is_enabled(self, settings: Settings) -> bool:
        # The listing runtime needs BOTH the Mongo store and the quota service,
        # so only compose it when both are enabled (gating on MONGO alone would
        # half-open and fail when QUOTA is off).
        return settings.MONGO_ENABLED and settings.QUOTA_ENABLED

    async def open(
        self,
        app: FastAPI,
        resources: ApplicationResources,
        settings: Settings,
    ) -> None:
        if resources.mongo is None:
            raise RuntimeError("ApplicationServicesAddon requires MONGO_ENABLED")
        if resources.quota is None:
            raise RuntimeError("ApplicationServicesAddon requires QUOTA_ENABLED")
        resources.services[LISTING_SERVICE_NAME] = build_listing_runtime(
            settings=settings,
            mongo=resources.mongo,
            quota=resources.quota,
        )

    async def close(self, app: FastAPI, resources: ApplicationResources) -> None:
        runtime = resources.services.pop(LISTING_SERVICE_NAME, None)
        if isinstance(runtime, ListingRuntime):
            await runtime.close()

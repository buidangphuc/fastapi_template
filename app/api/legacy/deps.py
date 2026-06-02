"""Service resolution for legacy DGL routes.

Services are built per-request from the lifespan-managed ``MongoGateway`` on
``app.state.resources``. If Mongo is not configured (``MONGO_ENABLED=false``),
``require`` raises a 503 — matching how other platform resources behave.
"""

from __future__ import annotations

from fastapi import Request

from app.bootstrap.state import get_app_resources, get_app_settings, require
from app.modules.business.listing.handlers.description import DescriptionGenerator
from app.modules.business.listing.handlers.pair_address import PairAddressGenerator
from app.modules.business.listing.services.listing_store import ListingStore
from app.modules.business.listing.services.nearby import NearbySearchService
from app.modules.business.listing.services.project import ProjectService
from app.modules.business.listing.services.usage import UsageService
from app.modules.platform.mongo.gateway import MongoGateway


def get_mongo_gateway(request: Request) -> MongoGateway:
    return require(
        get_app_resources(request.app).mongo,
        code="mongo_not_configured",
        message="MongoDB is not configured (MONGO_ENABLED=false)",
    )


def get_usage_service(request: Request) -> UsageService:
    return UsageService(get_mongo_gateway(request), get_app_settings(request.app))


def get_listing_store(request: Request) -> ListingStore:
    return ListingStore(get_mongo_gateway(request), get_app_settings(request.app))


def _build_generator_deps(request: Request):
    resources = get_app_resources(request.app)
    settings = get_app_settings(request.app)
    gateway = get_mongo_gateway(request)
    chat_model = require(
        resources.listing_chat_model,
        code="listing_generator_not_configured",
        message="Listing generator is not configured",
    )
    nearby = NearbySearchService(resources.listing_http_client, settings)
    project = ProjectService(
        resources.listing_http_client,
        chat_model,
        gateway,
        settings,
        resources.listing_prompt_provider,
    )
    tracker = resources.listing_tracker
    trace_config = tracker.trace_config() if tracker is not None else {}
    return nearby, project, chat_model, settings, trace_config


def get_description_generator(request: Request) -> DescriptionGenerator:
    nearby, project, chat_model, settings, trace_config = _build_generator_deps(request)
    return DescriptionGenerator(
        nearby_service=nearby,
        project_service=project,
        chat_model=chat_model,
        settings=settings,
        trace_config=trace_config,
    )


def get_pair_address_generator(request: Request) -> PairAddressGenerator:
    nearby, project, chat_model, settings, trace_config = _build_generator_deps(request)
    return PairAddressGenerator(
        nearby_service=nearby,
        project_service=project,
        chat_model=chat_model,
        settings=settings,
        trace_config=trace_config,
    )

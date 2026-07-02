"""FastAPI dependency adapters for the legacy listing surface."""

from __future__ import annotations

from fastapi import Request

from app.bootstrap.services import (
    LISTING_SERVICE_NAME,
    ListingRuntime,
)
from app.bootstrap.state import get_service_resource
from app.modules.business.listing.services.listing import ListingService


def get_listing_service(request: Request) -> ListingService:
    runtime = get_service_resource(request.app, LISTING_SERVICE_NAME, ListingRuntime)
    return runtime.service

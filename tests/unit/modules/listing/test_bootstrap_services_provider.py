from __future__ import annotations

from typing import cast

from fastapi import FastAPI
from starlette.requests import Request

from app.api.legacy.listing_dependencies import get_listing_service
from app.bootstrap import services as services_module
from app.bootstrap.resources import ApplicationResources
from app.bootstrap.services import (
    LISTING_SERVICE_NAME,
    ApplicationServicesAddon,
    ListingRuntime,
)
from app.modules.business.listing.services.listing import ListingService
from app.modules.platform.quota.service import QuotaService
from tests.factories import build_test_settings
from tests.mongo_fake import FakeMongoGateway


class _Client:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


def _request(app: FastAPI) -> Request:
    return Request({"type": "http", "app": app, "headers": []})


def test_listing_provider_returns_registered_product_service():
    app = FastAPI()
    service = cast(ListingService, object())
    app.state.resources = ApplicationResources(
        services={
            LISTING_SERVICE_NAME: ListingRuntime(
                service=service,
                http_client=_Client(),
            )
        }
    )

    assert get_listing_service(_request(app)) is service


async def test_listing_addon_registers_runtime_and_closes_it(monkeypatch):
    app = FastAPI()
    resources = ApplicationResources(
        mongo=FakeMongoGateway(),
        quota=cast(QuotaService, object()),
    )
    client = _Client()
    runtime = ListingRuntime(
        service=cast(ListingService, object()),
        http_client=client,
    )

    def _build_listing_runtime(**kwargs):
        return runtime

    monkeypatch.setattr(
        services_module,
        "build_listing_runtime",
        _build_listing_runtime,
    )
    addon = ApplicationServicesAddon()

    await addon.open(app, resources, build_test_settings(MONGO_ENABLED=True))
    assert resources.services[LISTING_SERVICE_NAME] is runtime

    await addon.close(app, resources)
    assert LISTING_SERVICE_NAME not in resources.services
    assert client.closed is True

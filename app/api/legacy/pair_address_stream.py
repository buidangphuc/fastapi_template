"""Experimental streaming variant of ``POST /description/pair_address`` (latency).

A separate endpoint that streams the generated content as Server-Sent Events so
the client can render text as soon as the model emits it (lower perceived
latency). This deliberately bypasses the structured-output + quota path used by
the production pair-address endpoint: it is an isolated experiment, not the
frozen contract.

``GET /description/pair_address/stream/demo`` serves a static HTML page that
drives the endpoint from the same origin (no CORS) and shows time-to-first-token
+ total latency.
"""

from __future__ import annotations

import json
import traceback
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from loguru import logger

from app.api.legacy.listing_dependencies import get_listing_service
from app.modules.business.listing.schemas import PairAddressParams
from app.modules.business.listing.services.listing import ListingService
from app.modules.business.listing.types import AddressVersionType, StyleType

router = APIRouter()

_DEMO_PAGE = Path(__file__).parent / "static" / "pair_address_stream.html"


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/pair_address/stream", summary="Generate Pair-Address (streaming)")
async def stream_pair_address(
    params: PairAddressParams,
    user_id: str = Query(description="User ID"),
    style: StyleType = Query(description="Style"),
    address_version: AddressVersionType = Query(default=AddressVersionType.OLD),
    service: ListingService = Depends(get_listing_service),
) -> StreamingResponse:
    async def event_source() -> AsyncIterator[str]:
        try:
            async for field, delta in service.astream_pair_address(
                user_id=user_id,
                style=style,
                params=params,
                address_version=address_version,
            ):
                yield _sse({"type": field, "delta": delta})
        except Exception:
            logger.error(f"Error streaming pair-address: {traceback.format_exc()}")
            yield _sse({"type": "error", "message": "generation_failed"})
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Disable proxy buffering so chunks flush immediately.
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/pair_address/stream/gemini",
    summary="Generate Pair-Address via Gemini/Vertex (streaming)",
)
async def stream_pair_address_gemini(
    params: PairAddressParams,
    user_id: str = Query(description="User ID"),
    style: StyleType = Query(description="Style"),
    address_version: AddressVersionType = Query(default=AddressVersionType.OLD),
    service: ListingService = Depends(get_listing_service),
) -> StreamingResponse:
    # Call outside the generator so a 501 (Vertex not configured) surfaces as a
    # proper HTTP error before the stream starts.
    field_stream = service.astream_pair_address_gemini(
        user_id=user_id,
        style=style,
        params=params,
        address_version=address_version,
    )

    async def event_source() -> AsyncIterator[str]:
        try:
            async for field, delta in field_stream:
                yield _sse({"type": field, "delta": delta})
        except Exception:
            logger.error(
                f"Error streaming pair-address (gemini): {traceback.format_exc()}"
            )
            yield _sse({"type": "error", "message": "generation_failed"})
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/pair_address/stream/demo", include_in_schema=False)
async def stream_demo() -> HTMLResponse:
    return HTMLResponse(_DEMO_PAGE.read_text(encoding="utf-8"))

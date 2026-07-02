"""Google Maps (PropertyGuru proxy) nearby search.

Ported behavior-frozen from bds-genai-dgl ``core/generator/service/nearby.py``.
Structural changes only:
- The HTTP client is injected (duck-typed; ``.request`` returning an httpx-like
  response) instead of an import-time global, and httpx is never imported here
  so the module stays importable without the optional dep.
- ``HEADERS`` are built per-instance from ``Settings`` (cookies if present, else
  the ``Referer`` header — both load-bearing for this API).
- The per-type result filtering is consolidated into ``_filter`` with None-safe
  score guards (legacy could raise on a missing rating).
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from loguru import logger
from pydantic import BaseModel

from app.core.config import Settings


class PlaceSearchDetail(BaseModel):
    place_id: str | None = None


class PlaceSearchResponse(BaseModel):
    predictions: list[PlaceSearchDetail] = []
    status: str | None = None


class PlaceDetailSearchResponse(BaseModel):
    lat: float
    lng: float


class Result(BaseModel):
    name: str | None = None
    place_id: str | None = None
    rating: float | None = None
    user_ratings_total: int | None = None
    types: list[str] | None = None


class NearbySearchResponse(BaseModel):
    nearby_type: str
    results: list[Result] | None = None
    status: str | None = None


_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hospital": ("bệnh viện", "hospital", "trạm y tế"),
    "park": ("công viên",),
    "supermarket": ("siêu thị", "winmart", "bách hóa xanh", "chợ"),
}


def build_nearby_headers(settings: Settings) -> dict[str, str]:
    if settings.GMAP_PG_COOKIES:
        return {
            "accept": "application/json",
            "cache-control": "no-cache",
            "cookie": settings.GMAP_PG_COOKIES,
            "referer": "https://gmaps.integration.propertyguru.com/",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            ),
        }
    return {"referer": settings.GMAP_PG_API_HEADER_REFERER}


class NearbySearchService:
    def __init__(self, client: Any, settings: Settings) -> None:
        self._client = client
        self._settings = settings
        self._headers = build_nearby_headers(settings)

    async def _get(self, url: str, params: dict[str, Any]) -> Any:
        return await self._client.request(
            "GET",
            url,
            params=params,
            headers=self._headers,
            timeout=self._settings.GMAP_PG_SEARCH_TIMEOUT,
        )

    async def place_search(
        self,
        query: str,
        language: str = "vn",
        component: str = "country:VN",
    ) -> PlaceSearchResponse:
        url = f"{self._settings.GMAP_PG_URL}/v2/placesAutoComplete"
        params = {"input": query, "language": language, "components": component}
        response = await self._get(url, params)
        if response.status_code != 200:
            logger.error(f"PlaceSearch error: {response.text} - params: {params}")
            return PlaceSearchResponse(predictions=[])
        return PlaceSearchResponse(**json.loads(response.text))

    async def place_detail(
        self,
        place_id: str,
        language: str = "vi",
    ) -> PlaceDetailSearchResponse | None:
        url = f"{self._settings.GMAP_PG_URL}/getDetails"
        params = {"placeId": place_id, "language": language}
        response = await self._get(url, params)
        if response.status_code != 200:
            logger.error(f"PlaceDetailSearch error: {response.text} - {place_id}")
            return None
        location = response.json()["result"]["geometry"]["location"]
        return PlaceDetailSearchResponse(lat=location["lat"], lng=location["lng"])

    async def nearby_search(
        self,
        lat: float,
        lng: float,
        radius: int,
        place_type: str,
        language: str = "vi",
        rankby: str = "prominence",
    ) -> NearbySearchResponse:
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "type": place_type,
            "language": language,
            "rankby": rankby,
        }
        response = await self._get(f"{self._settings.GMAP_PG_URL}/nearbySearch", params)
        data: dict[str, Any] = {"nearby_type": place_type}
        if response.status_code != 200:
            logger.error(f"NearbySearch error: {response.text} - params: {params}")
            return NearbySearchResponse(**data)
        data.update(json.loads(response.text))
        return NearbySearchResponse(**data)

    async def search(
        self,
        place: str | None,
        lat: float | None,
        lng: float | None,
        nearby_types: list[str],
        radius: int,
        language: str = "vn",
        rankby: str = "prominence",
    ) -> dict[str, list[str]] | None:
        all_names: dict[str, list[str]] = {}
        semaphore = asyncio.Semaphore(self._settings.GMAP_PG_CONCURRENCY)

        try:
            if (lat is None or lng is None) and place is not None:
                resolved = await self.place_search(place)
                if not resolved.predictions:
                    logger.error(f"Failed to resolve place_id for place {place}")
                    return {}
                place_id = resolved.predictions[0].place_id
                if place_id is None:
                    logger.error(f"Missing place_id for place {place}")
                    return {}
                detail = await self.place_detail(place_id)
                if detail is None:
                    return None
                lat, lng = detail.lat, detail.lng
            if lat is None or lng is None:
                return {}
            search_lat = lat
            search_lng = lng

            async def _one(place_type: str) -> NearbySearchResponse | None:
                async with semaphore:
                    try:
                        return await self.nearby_search(
                            search_lat,
                            search_lng,
                            radius,
                            place_type,
                            language,
                            rankby,
                        )
                    except Exception as exc:
                        logger.error(f"Nearby search failed for {place_type}: {exc}")
                        return None

            tasks = [asyncio.create_task(_one(t)) for t in nearby_types]
            start = time.time()
            for task in asyncio.as_completed(
                tasks, timeout=self._settings.ASYNC_TASK_TIMEOUT
            ):
                try:
                    nearby = await task
                    if nearby:
                        names = self._filter(nearby)
                        if names:
                            all_names[nearby.nearby_type] = names[
                                : self._settings.GMAP_PG_TOP_N_RESULTS
                            ]
                except TimeoutError:
                    logger.error("Timeout for nearby task")
                except Exception as exc:
                    logger.error(f"Error in nearby task: {exc}")
            logger.debug(f"Nearby search took {time.time() - start:.2f}s")
        except Exception as exc:
            logger.error(f"Nearby search error: {exc} - lat={lat} lng={lng}")

        return all_names

    def _filter(self, nearby: NearbySearchResponse) -> list[str]:
        keep = self._settings.GMAP_PG_NEARBY_KEEP_SCORE
        results = [r for r in (nearby.results or []) if r is not None and r.name]

        def score(result: Result) -> float:
            if result.rating is None or result.user_ratings_total is None:
                return 0.0
            return result.rating * result.user_ratings_total

        if nearby.nearby_type in _KEYWORDS:
            keywords = _KEYWORDS[nearby.nearby_type]
            filtered = [
                r
                for r in results
                if any(k in (r.name or "").lower() for k in keywords)
                and score(r) >= keep
            ]
        elif nearby.nearby_type == "school":
            filtered = [r for r in results if score(r) >= keep]
        else:
            filtered = []
        return [(r.name or "").lower() for r in filtered]

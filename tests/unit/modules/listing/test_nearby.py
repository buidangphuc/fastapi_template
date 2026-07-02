import httpx

from app.modules.business.listing.integrations.nearby import (
    NearbySearchService,
    build_nearby_headers,
)
from tests.factories import build_test_settings


def _service(handler, **settings_overrides):
    settings = build_test_settings(**settings_overrides)
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://gmap"
    )
    return NearbySearchService(client, settings)


def _nearby_handler(results):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/nearbySearch"):
            return httpx.Response(200, json={"results": results, "status": "OK"})
        if request.url.path.endswith("/v2/placesAutoComplete"):
            return httpx.Response(
                200, json={"predictions": [], "status": "ZERO_RESULTS"}
            )
        return httpx.Response(404, json={})

    return handler


async def test_filter_keeps_high_score_matching_name():
    results = [
        {
            "name": "Bệnh viện Chợ Rẫy",
            "place_id": "p1",
            "rating": 4.5,
            "user_ratings_total": 1000,
        }
    ]
    service = _service(_nearby_handler(results))
    found = await service.search(
        place=None, lat=10.0, lng=106.0, nearby_types=["hospital"], radius=2000
    )
    assert found == {"hospital": ["bệnh viện chợ rẫy"]}


async def test_filter_drops_low_composite_score():
    results = [
        {
            "name": "Bệnh viện Nhỏ",
            "place_id": "p1",
            "rating": 2.0,
            "user_ratings_total": 10,  # 20 < KEEP_SCORE(100)
        }
    ]
    service = _service(_nearby_handler(results))
    found = await service.search(
        place=None, lat=10.0, lng=106.0, nearby_types=["hospital"], radius=2000
    )
    assert "hospital" not in found


async def test_filter_drops_name_without_keyword():
    results = [
        {
            "name": "Quán Cà Phê",
            "place_id": "p1",
            "rating": 5.0,
            "user_ratings_total": 999,
        }
    ]
    service = _service(_nearby_handler(results))
    found = await service.search(
        place=None, lat=10.0, lng=106.0, nearby_types=["hospital"], radius=2000
    )
    assert found == {}


async def test_place_search_empty_returns_empty_dict():
    service = _service(_nearby_handler([]))
    found = await service.search(
        place="nowhere", lat=None, lng=None, nearby_types=["hospital"], radius=2000
    )
    assert found == {}


def test_build_headers_prefers_cookies_then_referer():
    with_cookies = build_nearby_headers(build_test_settings(GMAP_PG_COOKIES="abc"))
    assert with_cookies["cookie"] == "abc"

    with_referer = build_nearby_headers(
        build_test_settings(GMAP_PG_COOKIES="", GMAP_PG_API_HEADER_REFERER="http://x")
    )
    assert with_referer == {"referer": "http://x"}

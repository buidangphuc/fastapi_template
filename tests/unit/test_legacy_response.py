from app.api.legacy.response import LegacyResponseCode, legacy_response


async def test_legacy_success_response_uses_legacy_envelope():
    response = await legacy_response.success(data={"ok": True})

    assert response.code == 200
    assert response.message == "OK"
    assert response.data == {"ok": True}


async def test_legacy_success_response_allows_custom_message():
    response = await legacy_response.success(message="Listing not found")

    assert response.code == 200
    assert response.message == "Listing not found"
    assert response.data is None


async def test_legacy_fail_response_can_override_code_and_message():
    response = await legacy_response.fail(
        response_code=LegacyResponseCode.HTTP_429,
        message="Too many requests",
    )

    assert response.code == 429
    assert response.message == "Too many requests"

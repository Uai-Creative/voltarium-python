"""Regression tests: CCEE returns HTTP 204 No Content (empty body) instead of
a 200 with an empty array when a paginated list query matches zero results.
Before the `_parse_page` fix this crashed every list_* generator with a
JSONDecodeError on the unconditional `response.json()` call.

Uses httpx.MockTransport so these run offline, without the sandbox.
"""

from collections.abc import Callable

import httpx

from voltarium.client import VoltariumClient
from voltarium.models.token import Token


def _client_with_transport(handler: Callable[[httpx.Request], httpx.Response]) -> VoltariumClient:
    client = VoltariumClient(
        client_id="fake",
        client_secret="fake",
        base_url="https://fake.test",
    )
    # Pre-seed a valid token so the mock transport only has to handle the list call.
    client._token = Token(access_token="fake-token", expires_in=3600, token_type="Bearer")
    client._http_client = httpx.AsyncClient(base_url=client.base_url, transport=httpx.MockTransport(handler))
    return client


def _empty_204(_: httpx.Request) -> httpx.Response:
    return httpx.Response(204, content=b"")


async def test_list_contracts_handles_204_no_content() -> None:
    client = _client_with_transport(_empty_204)
    try:
        contracts = [
            c
            async for c in client.list_contracts(
                initial_reference_month="2026-01",
                final_reference_month="2026-01",
                agent_code="1",
                profile_code="1",
            )
        ]
        assert contracts == []
    finally:
        await client._http_client.aclose()


async def test_list_measurements_handles_204_no_content() -> None:
    client = _client_with_transport(_empty_204)
    try:
        measurements = [
            m
            async for m in client.list_measurements(
                consumer_unit_code="123",
                utility_agent_code="1",
                start_datetime="2026-01-01T00:00:00-03:00",
                end_datetime="2026-01-31T23:59:59-03:00",
                agent_code="1",
                profile_code="1",
            )
        ]
        assert measurements == []
    finally:
        await client._http_client.aclose()


async def test_list_migrations_handles_204_no_content() -> None:
    client = _client_with_transport(_empty_204)
    try:
        migrations = [
            m
            async for m in client.list_migrations(
                initial_reference_month="2026-01",
                final_reference_month="2026-01",
                agent_code="1",
                profile_code="1",
            )
        ]
        assert migrations == []
    finally:
        await client._http_client.aclose()


async def test_list_change_requests_handles_204_no_content() -> None:
    client = _client_with_transport(_empty_204)
    try:
        requests = [
            r
            async for r in client.list_change_requests(
                agent_code="1",
                profile_code="1",
                request_type="TROCA_TITULARIDADE",
                initial_reference_month="2026-01",
                final_reference_month="2026-01",
            )
        ]
        assert requests == []
    finally:
        await client._http_client.aclose()

from collections.abc import AsyncGenerator

import pytest

from voltarium.client import SANDBOX_BASE_URL, VoltariumClient
from voltarium.sandbox import RETAILERS, UTILITIES, SandboxAgentCredentials


@pytest.fixture()
def retailer() -> SandboxAgentCredentials:
    return RETAILERS[0]


@pytest.fixture()
def utility() -> SandboxAgentCredentials:
    return UTILITIES[0]


@pytest.fixture()
async def client(retailer: SandboxAgentCredentials) -> AsyncGenerator[VoltariumClient]:
    # Pinned to "v1" explicitly: these are the pre-existing integration tests, written
    # against V1 migrations behavior. VoltariumClient's own default is "v2" as of the
    # V1.1/V2 support work; version-specific behavior is covered by the client_v1_1/
    # client_v2 fixtures below.
    client = VoltariumClient(
        base_url=SANDBOX_BASE_URL,
        client_id=retailer.client_id,
        client_secret=retailer.client_secret,
        api_version="v1",
    )
    try:
        yield client
    finally:
        await client.__aexit__(None, None, None)


@pytest.fixture()
async def client_v1_1(retailer: SandboxAgentCredentials) -> AsyncGenerator[VoltariumClient]:
    client = VoltariumClient(
        base_url=SANDBOX_BASE_URL,
        client_id=retailer.client_id,
        client_secret=retailer.client_secret,
        api_version="v1.1",
    )
    try:
        yield client
    finally:
        await client.__aexit__(None, None, None)


@pytest.fixture()
async def client_v2(retailer: SandboxAgentCredentials) -> AsyncGenerator[VoltariumClient]:
    client = VoltariumClient(
        base_url=SANDBOX_BASE_URL,
        client_id=retailer.client_id,
        client_secret=retailer.client_secret,
        api_version="v2",
    )
    try:
        yield client
    finally:
        await client.__aexit__(None, None, None)

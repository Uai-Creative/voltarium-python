"""Tests for the V1/V1.1/V2 migrations API version selection and fallback logic."""

from datetime import timedelta

import pytest

from voltarium.client import MigrationApiVersion, VoltariumClient
from voltarium.factories import (
    CreateMigrationRequestFactory,
    CreateMigrationRequestV2Factory,
    UpdateMigrationRequestFactory,
)
from voltarium.models import CreateMigrationRequest, CreateMigrationRequestV2, MigrationItem, MigrationListItem
from voltarium.sandbox import SandboxAgentCredentials

# --- Offline unit tests: no network call is made, so no sandbox credentials needed ---


def _client(api_version: MigrationApiVersion) -> VoltariumClient:
    return VoltariumClient(client_id="unit-test", client_secret="unit-test", api_version=api_version)


def test_resolve_migration_version_v2_default_and_fallback() -> None:
    client = _client("v2")
    assert client._resolve_migration_version("list") == "v2"
    assert client._resolve_migration_version("create") == "v2"
    assert client._resolve_migration_version("get") == "v2"
    assert client._resolve_migration_version("update") == "v2"
    # No V2 (or V1.1) delete endpoint documented -> falls back all the way to v1
    assert client._resolve_migration_version("delete") == "v1"


def test_resolve_migration_version_v1_1_fallback() -> None:
    client = _client("v1.1")
    assert client._resolve_migration_version("list") == "v1.1"
    assert client._resolve_migration_version("create") == "v1.1"
    assert client._resolve_migration_version("get") == "v1.1"
    # No distinct V1.1 edit endpoint -> falls back to v1
    assert client._resolve_migration_version("update") == "v1"
    assert client._resolve_migration_version("delete") == "v1"


def test_resolve_migration_version_v1_no_fallback_needed() -> None:
    client = _client("v1")
    for operation in ("list", "create", "get", "update", "delete"):
        assert client._resolve_migration_version(operation) == "v1"


async def test_create_migration_v2_client_rejects_v1_request_shape() -> None:
    client = _client("v2")
    with pytest.raises(TypeError):
        await client.create_migration(
            CreateMigrationRequestFactory.build(),
            agent_code=1,
            profile_code=1,
        )


async def test_create_migration_v1_client_rejects_v2_request_shape() -> None:
    client = _client("v1")
    with pytest.raises(TypeError):
        await client.create_migration(
            CreateMigrationRequestV2Factory.build(),
            agent_code=1,
            profile_code=1,
        )


def test_create_migration_request_v2_model_shape() -> None:
    """Sanity-check the factory produces a model matching the documented V2 body."""
    request = CreateMigrationRequestV2Factory.build()
    assert isinstance(request, CreateMigrationRequestV2)
    dumped = request.model_dump(by_alias=True, exclude_none=True)
    assert "subGrupoTarifarioUnidadeConsumidora" in dumped
    assert "formalizacaoDistribuidora" in dumped
    assert "dataDenuncia" not in dumped  # dropped in V2


def test_create_migration_request_v1_still_requires_denunciation_date() -> None:
    request = CreateMigrationRequestFactory.build()
    assert isinstance(request, CreateMigrationRequest)
    dumped = request.model_dump(by_alias=True, exclude_none=True)
    assert "dataDenuncia" in dumped


# --- Sandbox integration tests: exercise the actual V1.1/V2 endpoints end-to-end ---


async def test_create_and_get_migration_v2(
    client_v2: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    """Create a migration via the V2 endpoint and confirm CP7 fields round-trip."""
    profile_id = retailer.profiles[0]

    created = await client_v2.create_migration(
        migration_data=CreateMigrationRequestV2Factory.build(
            retailer_agent_code=retailer.agent_code,
            retailer_profile_code=profile_id,
            utility_agent_code=utility.agent_code,
        ),
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )
    assert isinstance(created, MigrationItem)

    fetched = await client_v2.get_migration(
        migration_id=created.migration_id,
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )
    assert isinstance(fetched, MigrationItem)
    assert fetched.migration_id == created.migration_id


async def test_list_migrations_v1_1(
    client_v1_1: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    """V1.1 create/list share V1's request shape; only the path and response fields differ."""
    profile_id = retailer.profiles[0]

    created = await client_v1_1.create_migration(
        migration_data=CreateMigrationRequestFactory.build(
            retailer_agent_code=retailer.agent_code,
            retailer_profile_code=profile_id,
            utility_agent_code=utility.agent_code,
        ),
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )
    assert isinstance(created, MigrationItem)

    initial_month = created.reference_month.strftime("%Y-%m")
    results = [
        m
        async for m in client_v1_1.list_migrations(
            initial_reference_month=initial_month,
            final_reference_month=initial_month,
            agent_code=retailer.agent_code,
            profile_code=profile_id,
        )
    ]
    assert any(m.migration_id == created.migration_id for m in results)
    for m in results:
        assert isinstance(m, MigrationListItem)


async def test_update_migration_v1_1_falls_back_to_v1_endpoint(
    client_v1_1: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    """V1.1 has no distinct edit endpoint, so update_migration must still work via V1's."""
    profile_id = retailer.profiles[0]

    created = await client_v1_1.create_migration(
        migration_data=CreateMigrationRequestFactory.build(
            retailer_agent_code=retailer.agent_code,
            retailer_profile_code=profile_id,
            utility_agent_code=utility.agent_code,
        ),
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )

    future_month = created.reference_month + timedelta(days=60)
    updated = await client_v1_1.update_migration(
        migration_id=created.migration_id,
        migration_data=UpdateMigrationRequestFactory.build(
            retailer_profile_code=profile_id,
            reference_month=future_month.strftime("%Y-%m"),
        ),
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )
    assert isinstance(updated, MigrationItem)

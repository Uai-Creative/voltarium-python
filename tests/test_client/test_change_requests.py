"""Integration tests for change request (solicitacoes) endpoints against the CCEE sandbox.

Note on scope: `retorno-cativo`, `representante`, and the RESILICAO/RESOLUCAO variants of
`suspensao-fornecimento-*` all require an already-`CONCLUIDA` migration for the target consumer
unit. Migration approval isn't exposed by this API/client, so a freshly created migration (via
`create_migration`) is always `CRIADA`, never `CONCLUIDA` — a full creation-success round trip
isn't reachable deterministically from a clean test run. These tests instead assert the request
correctly reaches the API and is rejected with the expected, deterministic business-rule error,
which still exercises the full request/response cycle (headers, body shape, error parsing).
"""

from datetime import datetime, timedelta

import pytest

from voltarium.client import SANDBOX_BASE_URL, VoltariumClient
from voltarium.exceptions import ValidationError
from voltarium.factories import (
    CreateMigrationRequestFactory,
    CreateRepresentativeChangeRequestFactory,
    CreateReturnToCaptiveRequestFactory,
    CreateSupplySuspensionByRetailerRequestFactory,
    CreateSupplySuspensionByUtilityRequestFactory,
    UpdateChangeRequestStatusRequestFactory,
)
from voltarium.models import ChangeRequest, MigrationItem
from voltarium.sandbox import RETAILERS, SandboxAgentCredentials


async def _create_migration(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> MigrationItem:
    profile_id = retailer.profiles[0]
    return await client.create_migration(
        migration_data=CreateMigrationRequestFactory.build(
            retailer_agent_code=retailer.agent_code,
            retailer_profile_code=profile_id,
            utility_agent_code=utility.agent_code,
        ),
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )


def _client_for(credentials: SandboxAgentCredentials) -> VoltariumClient:
    """Build a client authenticated as `credentials` (the `client`/`retailer` fixtures are
    always the same retailer; several solicitacoes endpoints must be called as the
    counterparty — a utility or a different retailer — whose OAuth identity must match the
    `codigoAgente` header, or the sandbox rejects the call with ERR_CREDENCIAL_INVALID)."""
    return VoltariumClient(
        base_url=SANDBOX_BASE_URL,
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        api_version="v1",
    )


async def test_create_return_to_captive_request_requires_concluded_migration(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    migration = await _create_migration(client, retailer, utility)

    request = CreateReturnToCaptiveRequestFactory.build(
        consumer_unit_code=migration.consumer_unit_code,
        request_type="ALTERACAO_RETORNO_CATIVO_DESLIGAMENTO",
    )

    async with _client_for(utility) as utility_client:
        with pytest.raises(ValidationError) as exc_info:
            await utility_client.create_return_to_captive_request(
                request_data=request,
                agent_code=utility.agent_code,
                profile_code=utility.profiles[0],
            )
    assert exc_info.value.code == "ERR_MIGRACAO_CONCLUIDA_NAO_ENCONTRADA"


async def test_create_representative_change_request_rejects_unpermitted_uc(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    migration = await _create_migration(client, retailer, utility)
    new_retailer = RETAILERS[1]

    request = CreateRepresentativeChangeRequestFactory.build(
        consumer_unit_code=migration.consumer_unit_code,
        utility_agent_code=utility.agent_code,
        new_retailer_agent_code=new_retailer.agent_code,
        new_retailer_profile_code=new_retailer.profiles[0],
        request_type="ALTERACAO_ALFA_VAREJISTA_DESLIGAMENTO",
    )

    async with _client_for(new_retailer) as new_retailer_client:
        with pytest.raises(ValidationError):
            await new_retailer_client.create_representative_change_request(
                request_data=request,
                agent_code=new_retailer.agent_code,
                profile_code=new_retailer.profiles[0],
            )


async def test_create_supply_suspension_by_retailer_requires_concluded_migration(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    migration = await _create_migration(client, retailer, utility)

    request = CreateSupplySuspensionByRetailerRequestFactory.build(
        consumer_unit_code=migration.consumer_unit_code,
        utility_agent_code=utility.agent_code,
        request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
        notification_date=(datetime.now() - timedelta(days=95)).strftime("%Y-%m-%d"),
    )

    with pytest.raises(ValidationError) as exc_info:
        await client.create_supply_suspension_by_retailer(
            request_data=request,
            agent_code=retailer.agent_code,
            profile_code=retailer.profiles[0],
        )
    assert exc_info.value.code == "ERR_MIGRACAO_CONCLUIDA_NAO_ENCONTRADA"


async def test_create_supply_suspension_by_utility_requires_concluded_migration(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    migration = await _create_migration(client, retailer, utility)

    request = CreateSupplySuspensionByUtilityRequestFactory.build(
        consumer_unit_code=migration.consumer_unit_code,
        utility_agent_code=utility.agent_code,
    )

    async with _client_for(utility) as utility_client:
        with pytest.raises(ValidationError) as exc_info:
            await utility_client.create_supply_suspension_by_utility(
                request_data=request,
                agent_code=utility.agent_code,
                profile_code=utility.profiles[0],
            )
    assert exc_info.value.code == "ERR_MIGRACAO_CONCLUIDA_NAO_ENCONTRADA"


async def test_create_supply_suspension_by_utility_agent_code_defaults_from_client_arg(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    """Confirmed against the sandbox: omitting codigoAgenteConcessionaria from the body behaves
    identically to sending the calling agent's own code — the client must auto-fill it from
    `agent_code`, sparing the caller from passing the same value twice."""
    migration = await _create_migration(client, retailer, utility)

    request = CreateSupplySuspensionByUtilityRequestFactory.build(
        consumer_unit_code=migration.consumer_unit_code,
        utility_agent_code=None,
    )
    assert request.utility_agent_code is None

    async with _client_for(utility) as utility_client:
        with pytest.raises(ValidationError) as exc_info:
            await utility_client.create_supply_suspension_by_utility(
                request_data=request,
                agent_code=utility.agent_code,
                profile_code=utility.profiles[0],
            )
    # Same error the explicit-utility_agent_code test gets — proves the omitted field was
    # filled in correctly rather than causing a field-validation error.
    assert exc_info.value.code == "ERR_MIGRACAO_CONCLUIDA_NAO_ENCONTRADA"


async def test_update_change_request_status_unknown_id_raises_validation_error(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
) -> None:
    request = UpdateChangeRequestStatusRequestFactory.build(
        request_status="CONCLUIDA",
        request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
    )

    with pytest.raises(ValidationError) as exc_info:
        await client.update_change_request_status(
            change_request_id="00000000-0000-0000-0000-000000000000",
            request_data=request,
            agent_code=retailer.agent_code,
            profile_code=retailer.profiles[0],
        )
    assert exc_info.value.code == "ERR_SOLICITACAO_NAO_EXISTE_BASE_DADOS"


async def test_list_change_requests_by_reference_month(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
) -> None:
    now = datetime.now()
    results = [
        item
        async for item in client.list_change_requests(
            agent_code=retailer.agent_code,
            profile_code=retailer.profiles[0],
            request_status="CRIADA",
            request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
            initial_reference_month=(now - timedelta(days=300)).strftime("%Y-%m"),
            final_reference_month=now.strftime("%Y-%m"),
        )
    ]
    for item in results:
        assert isinstance(item, ChangeRequest)


async def test_list_change_requests_request_status_is_optional(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
) -> None:
    """Confirmed against the sandbox: omitting situacaoAlteracao returns 200 with results of
    every status, unlike tipoSolicitacao (which is genuinely required) — request_status must
    not be a required parameter."""
    now = datetime.now()
    results = [
        item
        async for item in client.list_change_requests(
            agent_code=retailer.agent_code,
            profile_code=retailer.profiles[0],
            request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
            initial_reference_month=(now - timedelta(days=300)).strftime("%Y-%m"),
            final_reference_month=now.strftime("%Y-%m"),
        )
    ]
    for item in results:
        assert isinstance(item, ChangeRequest)


async def test_list_change_requests_by_request_date(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
) -> None:
    now = datetime.now()
    results = [
        item
        async for item in client.list_change_requests(
            agent_code=retailer.agent_code,
            profile_code=retailer.profiles[0],
            request_status="CRIADA",
            request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
            initial_request_date=(now - timedelta(days=30)).strftime("%Y-%m-%d"),
            final_request_date=now.strftime("%Y-%m-%d"),
        )
    ]
    for item in results:
        assert isinstance(item, ChangeRequest)


async def test_list_change_requests_consumer_unit_filter(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    migration = await _create_migration(client, retailer, utility)
    now = datetime.now()

    results = [
        item
        async for item in client.list_change_requests(
            agent_code=retailer.agent_code,
            profile_code=retailer.profiles[0],
            request_status="CRIADA",
            request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
            initial_reference_month=(now - timedelta(days=300)).strftime("%Y-%m"),
            final_reference_month=now.strftime("%Y-%m"),
            consumer_unit_code=migration.consumer_unit_code,
        )
    ]
    # No change requests exist yet for a freshly created migration's consumer unit.
    assert results == []

import pytest

from voltarium.client import VoltariumClient
from voltarium.factories import CreateContractRequestFactory
from voltarium.models import Contract, ContractFile
from voltarium.sandbox import SandboxAgentCredentials, generate_consumer_unit_code


async def test_contracts_full_lifecycle_integration(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    profile_id = retailer.profiles[0]

    # 01. CREATE contract
    created: Contract | None = None

    create_req = CreateContractRequestFactory.build(
        retailer_agent_code=retailer.agent_code,
        retailer_profile_code=profile_id,
        utility_agent_code=utility.agent_code,
    )
    created = await client.create_contract(
        contract_data=create_req,
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )
    assert isinstance(created, Contract)
    assert created.contract_id

    # 02. GET contract by id
    fetched = await client.get_contract(
        contract_id=created.contract_id,
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )
    assert isinstance(fetched, Contract)
    assert fetched.contract_id == created.contract_id

    # 03. LIST contracts with utility filter
    contracts_iter = client.list_contracts(
        initial_reference_month="2020-01",
        final_reference_month="2030-12",
        agent_code=retailer.agent_code,
        profile_code=profile_id,
        utility_agent_code=utility.agent_code,
    )
    retrieved = [c async for c in contracts_iter]
    assert isinstance(retrieved, list)
    assert isinstance(retrieved[0], Contract)

    # 04. DOWNLOAD contract file (only for concluded contracts)
    concluded_contracts = [c for c in retrieved if c.contract_status == "CONCLUIDO"]
    if not concluded_contracts:
        pytest.skip("No concluded contracts available in sandbox to download file")

    concluded_contract = concluded_contracts[0]
    contract_file = await client.download_contract_file(
        contract_id=concluded_contract.contract_id,
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )

    assert isinstance(contract_file, ContractFile)
    assert contract_file.contract_id == concluded_contract.contract_id
    assert contract_file.content_base64
    assert contract_file.content
    assert contract_file.content_length
    import base64

    assert contract_file.content_length == len(base64.b64decode(contract_file.content_base64))


async def test_list_contracts_consumer_unit_filter(
    client: VoltariumClient,
    retailer: SandboxAgentCredentials,
    utility: SandboxAgentCredentials,
) -> None:
    """Regression: list_contracts must honour the consumer_unit_code filter.

    Previously, ListContractsParams used serialization_alias="codigoUC" which
    CCEE silently ignored, returning ALL contracts for the agent regardless of
    the requested UC. The correct alias is "codigoUnidadeConsumidora".

    Failure mode: if the filter is broken, both contract IDs appear in both
    result sets instead of each UC returning only its own contract.
    """
    profile_id = retailer.profiles[0]

    uc_a = generate_consumer_unit_code(f"{utility.agent_code}1001")
    uc_b = generate_consumer_unit_code(f"{utility.agent_code}2002")

    contract_a = await client.create_contract(
        contract_data=CreateContractRequestFactory.build(
            utility_agent_code=utility.agent_code,
            consumer_unit_code=uc_a,
        ),
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )
    contract_b = await client.create_contract(
        contract_data=CreateContractRequestFactory.build(
            utility_agent_code=utility.agent_code,
            consumer_unit_code=uc_b,
        ),
        agent_code=retailer.agent_code,
        profile_code=profile_id,
    )

    ids_a = {
        c.contract_id
        async for c in client.list_contracts(
            initial_reference_month="2020-01",
            final_reference_month="2030-12",
            agent_code=retailer.agent_code,
            profile_code=profile_id,
            utility_agent_code=utility.agent_code,
            consumer_unit_code=uc_a,
        )
    }
    ids_b = {
        c.contract_id
        async for c in client.list_contracts(
            initial_reference_month="2020-01",
            final_reference_month="2030-12",
            agent_code=retailer.agent_code,
            profile_code=profile_id,
            utility_agent_code=utility.agent_code,
            consumer_unit_code=uc_b,
        )
    }

    assert contract_a.contract_id in ids_a, "Contract for UC A not returned when filtering by UC A"
    assert contract_b.contract_id not in ids_a, "Contract for UC B leaked into UC A results (filter broken)"

    assert contract_b.contract_id in ids_b, "Contract for UC B not returned when filtering by UC B"
    assert contract_a.contract_id not in ids_b, "Contract for UC A leaked into UC B results (filter broken)"

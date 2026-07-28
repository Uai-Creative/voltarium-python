"""Pure Pydantic model tests for change request (solicitacoes) models — no network calls."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from voltarium.factories import (
    CreateRepresentativeChangeRequestFactory,
    CreateReturnToCaptiveRequestFactory,
    CreateSupplySuspensionByUtilityRequestFactory,
)
from voltarium.models import (
    ChangeRequest,
    CreateReturnToCaptiveRequest,
    CreateSupplySuspensionByRetailerRequest,
    UpdateChangeRequestStatusRequest,
)

# Captured verbatim from a real CCEE sandbox response (POST
# /v1/solicitacoes/suspensao-fornecimento-varejista, then approved via POST
# /v1/solicitacoes/{id}) while confirming the shapes documented in the Postman collection.
REAL_SANDBOX_RESPONSE = {
    "idSolicitacaoAlteracao": "e019da73-0d35-4766-9951-96435e0c4e30",
    "codigoUnidadeConsumidora": "0032765",
    "codigoAgenteConcessionaria": 100007,
    "tipoSolicitacao": "SUSPENSAO_FORNECIMENTO_RESILICAO",
    "mesReferencia": "2026-08-01T00:00:00-03:00",
    "situacaoAlteracao": "CONCLUIDA",
    "idMigracaoAlterada": "5e7121f0-fb26-43fb-9037-303c2a315189",
    "indicadorAntecedencia": None,
    "codigoAgenteVarejistaNovo": None,
    "codigoPerfilVarejistaNovo": None,
    "codigoAgenteVarejistaAtual": 200000,
    "codigoPerfilVarejistaAtual": 200100,
    "descricaoJustificativa": None,
    "dataAtraso": None,
    "dataNotificacao": "2026-04-23",
    "dataSolicitacao": "2026-07-27",
    "idCelebracaoCER": None,
}


def test_change_request_parses_real_sandbox_response() -> None:
    change_request = ChangeRequest.model_validate(REAL_SANDBOX_RESPONSE)

    assert change_request.change_request_id == "e019da73-0d35-4766-9951-96435e0c4e30"
    assert change_request.consumer_unit_code == "0032765"
    assert change_request.utility_agent_code == 100007
    assert change_request.request_type == "SUSPENSAO_FORNECIMENTO_RESILICAO"
    assert change_request.request_status == "CONCLUIDA"
    assert change_request.notification_date == "2026-04-23"
    assert change_request.current_retailer_agent_code == 200000
    assert change_request.new_retailer_agent_code is None


def test_change_request_tolerates_bare_creation_response() -> None:
    """The creation response (before approval) omits most optional fields entirely."""
    minimal = {
        **REAL_SANDBOX_RESPONSE,
        "situacaoAlteracao": "CRIADA",
        "mesReferencia": None,
    }
    change_request = ChangeRequest.model_validate(minimal)
    assert change_request.reference_month is None
    assert change_request.request_status == "CRIADA"


def test_create_return_to_captive_request_rejects_invalid_reference_month() -> None:
    with pytest.raises(PydanticValidationError, match="reference_month"):
        CreateReturnToCaptiveRequest(
            consumer_unit_code="UC123",
            reference_month="2024/01",
            cer_celebration_id="NAO",
            request_type="ALTERACAO_RETORNO_CATIVO_RESILICAO",
        )


def test_create_return_to_captive_request_dump_uses_portuguese_aliases() -> None:
    request = CreateReturnToCaptiveRequestFactory.build()
    dumped = request.model_dump(by_alias=True, exclude_none=True)
    assert "idCelebracaoCER" in dumped
    assert "mesReferencia" in dumped
    assert "tipoSolicitacao" in dumped


def test_create_representative_change_request_dump_uses_correct_field_names() -> None:
    """Regression guard: Postman's example body used `codigoConcessionaria`/
    `codigoVarejistaNovo`, but the real API expects `codigoAgenteConcessionaria`/
    `codigoAgenteVarejistaNovo` (confirmed against the sandbox)."""
    request = CreateRepresentativeChangeRequestFactory.build()
    dumped = request.model_dump(by_alias=True, exclude_none=True)
    assert "codigoAgenteConcessionaria" in dumped
    assert "codigoConcessionaria" not in dumped
    assert "codigoAgenteVarejistaNovo" in dumped
    assert "codigoVarejistaNovo" not in dumped


def test_create_supply_suspension_by_retailer_rejects_disconnection_type() -> None:
    """SUSPENSAO_FORNECIMENTO_DESLIGAMENTO is system-generated only — confirmed rejected by
    the sandbox (ERR_TIPO_SOLICITACAO_INVALIDO) — so it must not be a constructible value."""
    with pytest.raises(PydanticValidationError, match="request_type"):
        CreateSupplySuspensionByRetailerRequest.model_validate(
            {
                "consumer_unit_code": "UC123",
                "utility_agent_code": 100000,
                "request_type": "SUSPENSAO_FORNECIMENTO_DESLIGAMENTO",
                "notification_date": "2024-01-01",
            }
        )


def test_create_supply_suspension_by_retailer_requires_notification_date() -> None:
    with pytest.raises(PydanticValidationError, match="notification_date"):
        CreateSupplySuspensionByRetailerRequest.model_validate(
            {
                "consumer_unit_code": "UC123",
                "utility_agent_code": 100000,
                "request_type": "SUSPENSAO_FORNECIMENTO_RESILICAO",
            }
        )


def test_create_supply_suspension_by_retailer_rejects_invalid_notification_date_format() -> None:
    with pytest.raises(PydanticValidationError, match="notification_date"):
        CreateSupplySuspensionByRetailerRequest(
            consumer_unit_code="UC123",
            utility_agent_code=100000,
            request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
            notification_date="01/01/2024",
        )


def test_create_supply_suspension_by_utility_defaults_request_type() -> None:
    request = CreateSupplySuspensionByUtilityRequestFactory.build()
    assert request.request_type == "SUSPENSAO_FORNECIMENTO_RESOLUCAO_UC_CONCESSIONARIA"
    dumped = request.model_dump(by_alias=True, exclude_none=True)
    assert dumped["tipoSolicitacao"] == "SUSPENSAO_FORNECIMENTO_RESOLUCAO_UC_CONCESSIONARIA"
    assert "dataNotificacao" in dumped


def test_update_change_request_status_only_accepts_terminal_statuses() -> None:
    with pytest.raises(PydanticValidationError, match="request_status"):
        UpdateChangeRequestStatusRequest.model_validate(
            {
                "request_status": "CRIADA",
                "request_type": "SUSPENSAO_FORNECIMENTO_RESILICAO",
            }
        )


def test_update_change_request_status_dump_shape() -> None:
    request = UpdateChangeRequestStatusRequest(
        request_status="CONCLUIDA",
        request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
        justification="Approved automatically",
    )
    dumped = request.model_dump(by_alias=True, exclude_none=True)
    assert dumped == {
        "situacaoAlteracao": "CONCLUIDA",
        "tipoSolicitacao": "SUSPENSAO_FORNECIMENTO_RESILICAO",
        "descricaoJustificativa": "Approved automatically",
    }

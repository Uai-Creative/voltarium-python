"""Change request models for CCEE API (solicitacoes: troca de representante, retorno ao
cativo, suspensao de fornecimento)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from voltarium.models.constants import ChangeRequestStatus, ChangeRequestType


class ChangeRequest(BaseModel):
    """Change request model.

    Represents the result of any of the four creation endpoints (retorno-cativo,
    representante, suspensao-fornecimento-varejista, suspensao-fornecimento-concessionaria),
    the approve/reject endpoint, and items returned by the list endpoint. Most fields are
    optional since their presence depends on `request_type`.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    change_request_id: str = Field(alias="idSolicitacaoAlteracao", description="Change request ID")
    consumer_unit_code: str = Field(alias="codigoUnidadeConsumidora", description="Consumer unit code")
    utility_agent_code: int = Field(alias="codigoAgenteConcessionaria", description="Utility agent code")
    request_type: ChangeRequestType = Field(alias="tipoSolicitacao", description="Change request type")
    request_status: ChangeRequestStatus = Field(alias="situacaoAlteracao", description="Change request status")
    request_date: datetime = Field(alias="dataSolicitacao", description="Request date")
    reference_month: datetime | None = Field(default=None, alias="mesReferencia", description="Reference month")
    changed_migration_id: str | None = Field(
        default=None, alias="idMigracaoAlterada", description="ID of the migration this request affects"
    )
    advance_indicator: str | None = Field(
        default=None, alias="indicadorAntecedencia", description="Advance notice indicator"
    )
    new_retailer_agent_code: int | None = Field(
        default=None, alias="codigoAgenteVarejistaNovo", description="New retailer agent code"
    )
    new_retailer_profile_code: int | None = Field(
        default=None, alias="codigoPerfilVarejistaNovo", description="New retailer profile code"
    )
    current_retailer_agent_code: int | None = Field(
        default=None, alias="codigoAgenteVarejistaAtual", description="Current retailer agent code"
    )
    current_retailer_profile_code: int | None = Field(
        default=None, alias="codigoPerfilVarejistaAtual", description="Current retailer profile code"
    )
    justification: str | None = Field(default=None, alias="descricaoJustificativa", description="Justification")
    delay_date: str | None = Field(default=None, alias="dataAtraso", description="Delay date")
    notification_date: str | None = Field(default=None, alias="dataNotificacao", description="Notification date")
    cer_celebration_id: str | None = Field(default=None, alias="idCelebracaoCER", description="CER celebration ID")


class CreateReturnToCaptiveRequest(BaseModel):
    """Request model for a utility to request a consumer unit's return to the captive market
    (POST /v1/solicitacoes/retorno-cativo)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    consumer_unit_code: str = Field(serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code")
    reference_month: str = Field(serialization_alias="mesReferencia", description="Reference month (YYYY-MM)")
    cer_celebration_id: Literal["SIM", "NAO"] = Field(
        serialization_alias="idCelebracaoCER", description="Whether a CER was celebrated"
    )
    request_type: Literal[
        "ALTERACAO_RETORNO_CATIVO_RESILICAO",
        "ALTERACAO_RETORNO_CATIVO_RESOLUCAO",
        "ALTERACAO_RETORNO_CATIVO_DESLIGAMENTO",
    ] = Field(serialization_alias="tipoSolicitacao", description="Change request type")

    @field_validator("reference_month")
    def validate_reference_month(cls, v: str) -> str:
        """Validate reference month format."""
        try:
            datetime.strptime(v, "%Y-%m")
        except ValueError as exc:
            raise ValueError("reference_month must be in the format YYYY-MM") from exc
        return v


class CreateRepresentativeChangeRequest(BaseModel):
    """Request model for a new retailer to request becoming a consumer unit's representative
    (POST /v1/solicitacoes/representante)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    consumer_unit_code: str = Field(serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code")
    utility_agent_code: int | str = Field(
        serialization_alias="codigoAgenteConcessionaria", description="Utility agent code"
    )
    new_retailer_agent_code: int | str = Field(
        serialization_alias="codigoAgenteVarejistaNovo", description="New retailer agent code"
    )
    new_retailer_profile_code: int | str = Field(
        serialization_alias="codigoPerfilVarejistaNovo", description="New retailer profile code"
    )
    reference_month: str = Field(serialization_alias="mesReferencia", description="Reference month (YYYY-MM)")
    request_type: Literal[
        "ALTERACAO_ALFA_VAREJISTA_RESILICAO",
        "ALTERACAO_ALFA_VAREJISTA_RESOLUCAO",
        "ALTERACAO_ALFA_VAREJISTA_DESLIGAMENTO",
    ] = Field(serialization_alias="tipoSolicitacao", description="Change request type")

    @field_validator("reference_month")
    def validate_reference_month(cls, v: str) -> str:
        """Validate reference month format."""
        try:
            datetime.strptime(v, "%Y-%m")
        except ValueError as exc:
            raise ValueError("reference_month must be in the format YYYY-MM") from exc
        return v


class CreateSupplySuspensionByRetailerRequest(BaseModel):
    """Request model for a retailer to request supply suspension
    (POST /v1/solicitacoes/suspensao-fornecimento-varejista).

    Note: `SUSPENSAO_FORNECIMENTO_DESLIGAMENTO` is intentionally not an accepted value here —
    the CCEE API rejects it (ERR_TIPO_SOLICITACAO_INVALIDO), since that suspension is
    generated automatically by the system rather than requested.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    consumer_unit_code: str = Field(serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code")
    utility_agent_code: int | str = Field(
        serialization_alias="codigoAgenteConcessionaria", description="Utility agent code"
    )
    request_type: Literal["SUSPENSAO_FORNECIMENTO_RESILICAO", "SUSPENSAO_FORNECIMENTO_RESOLUCAO"] = Field(
        serialization_alias="tipoSolicitacao", description="Change request type"
    )
    notification_date: str = Field(serialization_alias="dataNotificacao", description="Notification date (YYYY-MM-DD)")

    @field_validator("notification_date")
    def validate_notification_date(cls, v: str) -> str:
        """Validate notification date format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("notification_date must be in the format YYYY-MM-DD") from exc
        return v


class CreateSupplySuspensionByUtilityRequest(BaseModel):
    """Request model for a utility to request supply suspension due to retailer delinquency
    (POST /v1/solicitacoes/suspensao-fornecimento-concessionaria).

    Unlike the other three creation endpoints, this one is always called by the utility
    itself (its identity is already carried by the `codigoAgente` header / the client
    method's `agent_code` argument), and the sandbox confirmed `codigoAgenteConcessionaria`
    in the body is optional: omitting it produces the exact same response as including the
    calling agent's own code. `utility_agent_code` is therefore optional here — pass it only
    to override the default (the client fills it in from `agent_code` if omitted).
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    consumer_unit_code: str = Field(serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code")
    utility_agent_code: int | str | None = Field(
        default=None,
        serialization_alias="codigoAgenteConcessionaria",
        description="Utility agent code (defaults to the calling agent_code if omitted)",
    )
    request_type: Literal["SUSPENSAO_FORNECIMENTO_RESOLUCAO_UC_CONCESSIONARIA"] = Field(
        default="SUSPENSAO_FORNECIMENTO_RESOLUCAO_UC_CONCESSIONARIA",
        serialization_alias="tipoSolicitacao",
        description="Change request type",
    )
    notification_date: str = Field(serialization_alias="dataNotificacao", description="Notification date (YYYY-MM-DD)")

    @field_validator("notification_date")
    def validate_notification_date(cls, v: str) -> str:
        """Validate notification date format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("notification_date must be in the format YYYY-MM-DD") from exc
        return v


class UpdateChangeRequestStatusRequest(BaseModel):
    """Request model for approving/rejecting a change request
    (POST /v1/solicitacoes/:idSolicitacaoAlteracao)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    request_status: Literal["CONCLUIDA", "REPROVADA"] = Field(
        serialization_alias="situacaoAlteracao", description="New change request status"
    )
    request_type: str = Field(
        serialization_alias="tipoSolicitacao", description="Change request type (echoes the original request)"
    )
    justification: str | None = Field(
        default=None, serialization_alias="descricaoJustificativa", description="Justification"
    )

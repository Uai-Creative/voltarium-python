"""Migration models for CCEE API."""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from voltarium.models.constants import MigrationStatus


class BaseMigration(BaseModel):
    """Base migration model with common fields."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    migration_id: str = Field(alias="idMigracao", description="Migration ID")
    consumer_unit_code: str = Field(alias="codigoUnidadeConsumidora", description="Consumer unit code")
    utility_agent_consumer_unit_code: str = Field(
        alias="codigoAgenteConcessionariaUnidadeConsumidora", description="Utility agent consumer unit code"
    )
    utility_agent_code: int = Field(alias="codigoAgenteConcessionaria", description="Utility agent code")
    document_type: Literal["CPF", "CNPJ"] | None = Field(
        default=None, alias="tipoDocumento", description="Document type"
    )
    document_number: str | None = Field(default=None, alias="numeroDocumento", description="Document number")
    retailer_agent_code: int = Field(alias="codigoAgenteVarejista", description="Retailer agent code")
    request_date: datetime = Field(alias="dataSolicitacao", description="Request date")
    retailer_profile_code: int = Field(alias="codigoPerfilVarejista", description="Retailer profile code")
    migration_status: MigrationStatus = Field(alias="statusMigracao", description="Migration status")
    submarket: str | None = Field(default=None, alias="submercado", description="Submarket")
    dhc_value: float | None = Field(default=None, alias="valorDHC", description="DHC value")
    musd_value: float | None = Field(default=None, alias="valorMusd", description="MUSD value")
    penalty_payment: Literal["SIM", "NAO"] | None = Field(
        default=None, alias="pagamentoMulta", description="Penalty payment"
    )
    justification: str | None = Field(default=None, alias="justificativa", description="Justification")
    validation_date: datetime | None = Field(default=None, alias="dataValidacao", description="Validation date")
    consumer_unit_email: str = Field(alias="emailUnidadeConsumidora", description="Consumer unit email")
    comment: str | None = Field(default=None, alias="comentario", description="Comment")

    # V1.1 fields (response-only; absent on V1 and V2 responses)
    process_siga_indicator: str | None = Field(
        default=None, alias="indicadorProcessoSiga", description="Siga process indicator (V1.1+)"
    )

    # V2 fields (response-only; absent on V1 and V1.1 responses)
    protocol_number: str | None = Field(
        default=None, alias="numeroProtocolo", description="Utility protocol number (V2+)"
    )
    intended_utility_month: str | None = Field(
        default=None, alias="mesPretendidoConcessionaria", description="Intended utility migration month (V2+)"
    )
    formalization_date: datetime | None = Field(
        default=None, alias="dataFormalizacao", description="Utility formalization date (V2+)"
    )
    migration_modality: Literal["REGULAR", "ANTECIPADA"] | None = Field(
        default=None, alias="modalidadeMigracao", description="Migration modality (V2+)"
    )
    consumer_unit_tariff_subgroup: Literal["A2", "A3", "A3a", "A4", "AS", "B1", "B2", "B3", "B4"] | None = Field(
        default=None, alias="subGrupoTarifarioUnidadeConsumidora", description="Consumer unit tariff subgroup (V2+)"
    )
    utility_formalized: Literal["SIM", "NAO"] | None = Field(
        default=None, alias="formalizacaoDistribuidora", description="Whether formalized with the utility (V2+)"
    )


class MigrationListItem(BaseMigration):
    """Migration list item model for list operations."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Fields specific to list representation
    supplier_agent_code: int | None = Field(
        default=None, alias="codigoAgenteSupridora", description="Supplier agent code"
    )
    reference_month: datetime = Field(alias="mesReferencia", description="Reference month")
    # Optional: absent on V1.1/V2 migrations created via the formalizacaoDistribuidora workflow,
    # which supersedes dataDenuncia (V2's create request drops the field entirely).
    denunciation_date: datetime | None = Field(default=None, alias="dataDenuncia", description="Denunciation date")
    cer_celebration_id: str | None = Field(default=None, alias="idCelebracaoCER", description="CER celebration ID")


class MigrationItem(BaseMigration):
    """Migration item model for detailed operations (CRUD)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Fields specific to detailed representation
    reference_month: datetime = Field(alias="dataReferencia", description="Reference month")
    denunciation_date: datetime | None = Field(default=None, alias="dataDenuncia", description="Denunciation date")
    connected_type: str | None = Field(default=None, alias="tipoConectado", description="Connected type")
    supplier_code: int | None = Field(default=None, alias="codigoSupridora", description="Supplier code")


class CreateMigrationRequest(BaseModel):
    """Request model for creating a migration."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    consumer_unit_code: str = Field(serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code")
    utility_agent_code: int | str = Field(
        serialization_alias="codigoAgenteConcessionaria", description="Utility agent code"
    )
    document_type: Literal["CPF", "CNPJ"] = Field(serialization_alias="tipoDocumento", description="Document type")
    document_number: str | None = Field(
        default=None,
        serialization_alias="numeroDocumento",
        description="Document number (omit for CPF requests)",
    )
    retailer_agent_code: int | str = Field(
        serialization_alias="codigoAgenteVarejista", description="Retailer agent code"
    )
    reference_month: str = Field(serialization_alias="mesReferencia", description="Reference month (YYYY-MM)")
    denunciation_date: str = Field(serialization_alias="dataDenuncia", description="Denunciation date")
    retailer_profile_code: int | str = Field(
        serialization_alias="codigoPerfilVarejista", description="Retailer profile code"
    )
    consumer_unit_email: str = Field(serialization_alias="emailUnidadeConsumidora", description="Consumer unit email")
    comment: str | None = Field(default=None, serialization_alias="comentario", description="Comment")

    @field_validator("document_number", mode="before")
    def normalize_document_number(cls, v: str | None) -> str | None:
        """Normalize document number format."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None

        digits = "".join(filter(str.isdigit, str(v)))
        if not digits:
            raise ValueError("document_number must be a number")
        return digits

    @model_validator(mode="after")
    def validate_document_length(self) -> Self:
        document_type = self.document_type
        document_number = self.document_number
        if document_type == "CPF":
            if document_number is not None:
                raise ValueError("document_number must be omitted when document_type is CPF")
            return self
        if document_type == "CNPJ" and (document_number is None or len(document_number) != 14):
            msg = "CNPJ numbers must contain exactly 14 digits"
            raise ValueError(msg)
        return self

    @field_validator("reference_month")
    def validate_reference_month(cls, v: str) -> str:
        """Validate reference month format."""
        try:
            datetime.strptime(v, "%Y-%m")
        except ValueError as exc:
            raise ValueError("reference_month must be in the format YYYY-MM") from exc
        return v

    @field_validator("denunciation_date")
    def validate_denunciation_date(cls, v: str) -> str:
        """Validate denunciation date format."""
        # Validate the date format (YYYY-MM-DD) and that it's a valid date
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("denunciation_date must be in the format YYYY-MM-DD") from exc
        return v


class CreateMigrationRequestV2(BaseModel):
    """Request model for creating a migration (V2, CP7 rules)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    consumer_unit_code: str = Field(serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code")
    utility_agent_code: int | str = Field(
        serialization_alias="codigoAgenteConcessionaria", description="Utility agent code"
    )
    document_type: Literal["CPF", "CNPJ"] = Field(serialization_alias="tipoDocumento", description="Document type")
    document_number: str | None = Field(
        default=None,
        serialization_alias="numeroDocumento",
        description="Document number (omit for CPF requests)",
    )
    retailer_agent_code: int | str = Field(
        serialization_alias="codigoAgenteVarejista", description="Retailer agent code"
    )
    reference_month: str = Field(serialization_alias="mesReferencia", description="Reference month (YYYY-MM)")
    retailer_profile_code: int | str = Field(
        serialization_alias="codigoPerfilVarejista", description="Retailer profile code"
    )
    consumer_unit_email: str = Field(serialization_alias="emailUnidadeConsumidora", description="Consumer unit email")
    consumer_unit_tariff_subgroup: Literal["A2", "A3", "A3a", "A4", "AS", "B1", "B2", "B3", "B4"] = Field(
        serialization_alias="subGrupoTarifarioUnidadeConsumidora", description="Consumer unit tariff subgroup"
    )
    utility_formalized: Literal["SIM", "NAO"] = Field(
        serialization_alias="formalizacaoDistribuidora", description="Whether formalized with the utility"
    )
    formalization_date: str | None = Field(
        default=None,
        serialization_alias="dataFormalizacao",
        description=(
            "Utility formalization date (YYYY-MM-DD); required when utility_formalized is 'SIM', "
            "must be omitted otherwise"
        ),
    )
    migration_modality: Literal["REGULAR", "ANTECIPADA"] | None = Field(
        default=None,
        serialization_alias="modalidadeMigracao",
        description="Migration modality; required when utility_formalized is 'NAO', must be omitted otherwise",
    )
    comment: str | None = Field(default=None, serialization_alias="comentario", description="Comment")

    @field_validator("document_number", mode="before")
    def normalize_document_number(cls, v: str | None) -> str | None:
        """Normalize document number format."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None

        digits = "".join(filter(str.isdigit, str(v)))
        if not digits:
            raise ValueError("document_number must be a number")
        return digits

    @model_validator(mode="after")
    def validate_document_length(self) -> Self:
        document_type = self.document_type
        document_number = self.document_number
        if document_type == "CPF":
            if document_number is not None:
                raise ValueError("document_number must be omitted when document_type is CPF")
            return self
        if document_type == "CNPJ" and (document_number is None or len(document_number) != 14):
            msg = "CNPJ numbers must contain exactly 14 digits"
            raise ValueError(msg)
        return self

    @field_validator("reference_month")
    def validate_reference_month(cls, v: str) -> str:
        """Validate reference month format."""
        try:
            datetime.strptime(v, "%Y-%m")
        except ValueError as exc:
            raise ValueError("reference_month must be in the format YYYY-MM") from exc
        return v

    @field_validator("formalization_date")
    def validate_formalization_date(cls, v: str | None) -> str | None:
        """Validate formalization date format."""
        if v is None:
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("formalization_date must be in the format YYYY-MM-DD") from exc
        return v

    @model_validator(mode="after")
    def validate_formalization_fields(self) -> Self:
        """Enforce the CP7 conditional rules tying formalization fields together."""
        if self.utility_formalized == "SIM":
            if self.formalization_date is None:
                raise ValueError("formalization_date is required when utility_formalized is 'SIM'")
            if self.migration_modality is not None:
                raise ValueError("migration_modality must be omitted when utility_formalized is 'SIM'")
        else:
            if self.migration_modality is None:
                raise ValueError("migration_modality is required when utility_formalized is 'NAO'")
            if self.formalization_date is not None:
                raise ValueError("formalization_date must be omitted when utility_formalized is 'NAO'")
        return self


class UpdateMigrationRequest(BaseModel):
    """Request model for updating a migration."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    reference_month: str = Field(serialization_alias="mesReferencia", description="Reference month (YYYY-MM)")
    retailer_profile_code: int | str = Field(
        serialization_alias="codigoPerfilVarejista", description="Retailer profile code"
    )
    document_type: Literal["CPF", "CNPJ"] = Field(serialization_alias="tipoDocumento", description="Document type")
    document_number: str | None = Field(
        default=None,
        serialization_alias="numeroDocumento",
        description="Document number (omit for CPF updates; required for CNPJ)",
    )
    consumer_unit_email: str = Field(serialization_alias="emailUnidadeConsumidora", description="Consumer unit email")

    @field_validator("document_number", mode="before")
    def validate_document_number(cls, v: str | None) -> str | None:
        """Normalize and validate document number format.

        The sandbox requires `numeroDocumento` for CNPJ updates, but rejects the
        field entirely for CPF. We therefore treat the field as optional and let
        the document-type validator enforce the right constraint."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        digits = "".join(filter(str.isdigit, str(v)))
        if not digits:
            raise ValueError("document_number must be a number")
        return digits

    @model_validator(mode="after")
    def validate_document_length(self) -> Self:
        document_type = self.document_type
        document_number = self.document_number
        if document_type == "CPF":
            if document_number is not None and len(document_number) != 11:
                msg = "CPF numbers must contain exactly 11 digits"
                raise ValueError(msg)
            # CPF updates must omit numeroDocumento entirely (API returns 400 otherwise)
            return self
        if document_type == "CNPJ" and (document_number is None or len(document_number) != 14):
            msg = "CNPJ numbers must contain exactly 14 digits"
            raise ValueError(msg)
        return self

    @field_validator("reference_month")
    def validate_reference_month(cls, v: str) -> str:
        """Validate reference month format."""
        try:
            datetime.strptime(v, "%Y-%m")
        except ValueError as exc:
            raise ValueError("reference_month must be in the format YYYY-MM") from exc
        return v

"""Contract models for CCEE API (varejista/contratos)."""

import base64
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class Contract(BaseModel):
    """Retailer contract model.

    This model is intentionally permissive to accommodate schema variations
    across environments. Known fields are declared with Portuguese aliases
    to match the CCEE API, and additional fields are accepted.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    contract_id: str = Field(alias="idContrato", description="Contract ID")
    consumer_unit_code: str | None = Field(
        default=None, alias="codigoUnidadeConsumidora", description="Consumer unit code"
    )
    consumer_unit_name: str | None = Field(
        default=None, alias="nomeUnidadeConsumidora", description="Consumer unit name"
    )
    consumer_unit_address: str | None = Field(
        default=None, alias="enderecoUnidadeConsumidora", description="Consumer unit address"
    )
    consumer_unit_phone: str | None = Field(
        default=None, alias="telefoneUnidadeConsumidora", description="Consumer unit phone"
    )
    document_type: str | None = Field(default=None, alias="tipoDocumento", description="Document type")
    document_number: str | None = Field(default=None, alias="numeroDocumento", description="Document number")
    authenticity_code: str | None = Field(
        default=None, alias="codigoAutenticidade", description="Authenticity code for signed contract"
    )
    representatives: list[LegalRepresentative] | None = Field(
        default=None, alias="representantesLegais", description="Legal representatives"
    )
    branch_consumer_unit_cnpj: str | None = Field(
        default=None,
        alias="cnpjFilialUnidadeConsumidora",
        description="Branch CNPJ for the consumer unit",
    )
    branch_consumer_unit_address: str | None = Field(
        default=None,
        alias="enderecoFilialUnidadeConsumidora",
        description="Branch address for the consumer unit",
    )
    contract_status: str | None = Field(default=None, alias="situacaoCcv", description="Contract status")


class LegalRepresentative(BaseModel):
    """Legal representative information returned by the contracts API."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    contact_name: str | None = Field(default=None, alias="nomeContato", description="Contact name")
    contact_type: Literal["UNIDADE_CONSUMIDORA", "VAREJISTA"] | None = Field(
        default=None, alias="tipoContato", description="Contact type"
    )
    retailer_contact_code: int | None = Field(
        default=None, alias="codigoContatoVarejista", description="Retailer contact code"
    )
    signature_status: str | None = Field(default=None, alias="situacaoAssinatura", description="Signature status")
    updated_at: datetime | None = Field(default=None, alias="dataAtualizacao", description="Last update timestamp")
    contract_code: str | None = Field(default=None, alias="codigoContrato", description="Contract code reference")


class LegalRepresentativeWrite(BaseModel):
    """Legal representative payload for contract creation (write model)."""

    model_config = ConfigDict(populate_by_name=True)

    contact_name: str = Field(serialization_alias="nomeContato", description="Contact name")
    contact_email: str = Field(serialization_alias="nomeEmail", description="Contact email")
    document_number: str = Field(serialization_alias="numeroDocumento", description="Document number")
    contact_type: Literal["UNIDADE_CONSUMIDORA", "VAREJISTA"] = Field(
        serialization_alias="tipoContato", description="Contact type"
    )
    document_type: Literal["CPF", "CNPJ"] = Field(serialization_alias="tipoDocumento", description="Document type")

    @field_validator("document_number")
    def validate_document_number(cls, v: str) -> str:
        v = "".join(filter(str.isdigit, v))
        if not v.isdigit():
            raise ValueError("document_number must be a number")
        return v


class ContractFile(BaseModel):
    """Base64-encoded contract file payload returned by the contracts API."""

    model_config = ConfigDict(populate_by_name=True)

    contract_id: str = Field(description="Contract identifier")
    filename: str = Field(description="Suggested filename for the document")
    content_type: str = Field(description="MIME type declared by the API")
    content_base64: str = Field(description="Base64-encoded representation of the contract", repr=False)

    @computed_field(return_type=bytes, repr=False)
    def content(self) -> bytes:
        """Return the decoded contract contents as raw bytes."""
        return base64.b64decode(self.content_base64)

    @computed_field(return_type=int)
    def content_length(self) -> int:
        """Return the size of the decoded payload in bytes."""
        return len(base64.b64decode(self.content_base64))


class CreateContractRequest(BaseModel):
    """Request body for creating a retailer contract.

    Uses Portuguese field aliases to match the CCEE API and allows
    extra fields for forward compatibility across environments.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    utility_agent_code: int | str = Field(
        serialization_alias="codigoAgenteConcessionaria", description="Utility agent code"
    )
    consumer_unit_code: str = Field(serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code")
    consumer_unit_address: str | None = Field(
        default=None,
        serialization_alias="enderecoUnidadeConsumidora",
        description="Consumer unit address (free text)",
    )
    consumer_unit_name: str | None = Field(
        default=None, serialization_alias="nomeUnidadeConsumidora", description="Consumer unit name"
    )
    # Legal representatives (english attribute name; serialized to representantesLegais)
    legal_representatives: list[LegalRepresentativeWrite] | None = Field(
        default=None,
        serialization_alias="representantesLegais",
        description="List of legal representatives",
    )
    document_type: Literal["CNPJ", "CPF"] = Field(serialization_alias="tipoDocumento", description="Document type")
    document_number: str = Field(serialization_alias="numeroDocumento", description="Document number")
    # Additional optional fields per docs
    consumer_unit_phone: str | None = Field(
        default=None, serialization_alias="telefoneUnidadeConsumidora", description="Consumer unit phone"
    )
    branch_consumer_unit_cnpj: str | None = Field(
        default=None,
        serialization_alias="cnpjFilialUnidadeConsumidora",
        description="Branch CNPJ for consumer unit",
    )
    branch_consumer_unit_address: str | None = Field(
        default=None,
        serialization_alias="enderecoFilialUnidadeConsumidora",
        description="Branch address for consumer unit",
    )

    @field_validator("document_number")
    def validate_document_number(cls, v: str) -> str:
        v = "".join(filter(str.isdigit, v))
        if not v.isdigit():
            raise ValueError("document_number must be a number")
        return v

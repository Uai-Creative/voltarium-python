"""Request models for API headers and query parameters."""

from pydantic import BaseModel, ConfigDict, Field


class ApiHeaders(BaseModel):
    """Headers required for Brazilian API requests."""

    model_config = ConfigDict(populate_by_name=True)

    agent_code: str = Field(serialization_alias="codigoAgente", description="Agent code")
    profile_code: str = Field(serialization_alias="codigoPerfil", description="Profile code")


class ListMigrationsParams(BaseModel):
    """Query parameters for listing migrations."""

    model_config = ConfigDict(populate_by_name=True)

    initial_reference_month: str = Field(
        serialization_alias="mesReferenciaInicial", description="Start reference month (YYYY-MM)"
    )
    final_reference_month: str = Field(
        serialization_alias="mesReferenciaFinal", description="End reference month (YYYY-MM)"
    )
    retailer_profile_code: str = Field(serialization_alias="codigoPerfilVarejista", description="Retailer profile code")
    consumer_unit_code: str | None = Field(
        default=None, serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code filter"
    )
    migration_status: str | None = Field(
        default=None, serialization_alias="statusMigracao", description="Migration status filter"
    )
    next_page_index: str | None = Field(
        default=None, serialization_alias="indexProximaPagina", description="Next page index for pagination"
    )


class ListContractsParams(BaseModel):
    """Query parameters for listing retailer contracts."""

    model_config = ConfigDict(populate_by_name=True)

    initial_reference_month: str = Field(
        serialization_alias="mesReferenciaInicial", description="Start reference month (YYYY-MM)"
    )
    final_reference_month: str = Field(
        serialization_alias="mesReferenciaFinal", description="End reference month (YYYY-MM)"
    )
    retailer_profile_code: str = Field(serialization_alias="codigoPerfilVarejista", description="Retailer profile code")
    utility_agent_code: str | None = Field(
        default=None, serialization_alias="codigoAgenteConcessionaria", description="Utility agent code filter"
    )
    consumer_unit_code: str | None = Field(
        default=None, serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code filter"
    )
    contract_status: str | None = Field(
        default=None, serialization_alias="statusContrato", description="Contract status filter"
    )
    next_page_index: str | None = Field(
        default=None, serialization_alias="indexProximaPagina", description="Next page index for pagination"
    )


class ListMeasurementsParams(BaseModel):
    """Query parameters for listing consumption measurements (medicoes)."""

    model_config = ConfigDict(populate_by_name=True)

    consumer_unit_code: str = Field(serialization_alias="codigoUnidadeConsumidora", description="Consumer unit code")
    utility_agent_code: str = Field(serialization_alias="codigoAgenteConcessionaria", description="Utility agent code")
    start_datetime: str = Field(
        serialization_alias="dataInicio",
        description="Start datetime (ISO 8601 with timezone, e.g., 2024-09-01T00:00:00-03:00)",
    )
    end_datetime: str = Field(
        serialization_alias="dataFim",
        description="End datetime (ISO 8601 with timezone, e.g., 2024-09-30T23:59:59-03:00)",
    )
    measurement_status: str | None = Field(
        default=None,
        serialization_alias="situacaoMedicao",
        description="Measurement status filter (CONSISTIDA, REJEITADA)",
    )
    next_page_index: str | None = Field(
        default=None, serialization_alias="indexProximaPagina", description="Next page index for pagination"
    )

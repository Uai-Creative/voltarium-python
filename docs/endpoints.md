# Supported Endpoints

Voltarium currently supports the retailer migration, contracts, measurements, and change request (solicitações) endpoints of the CCEE API. These endpoints allow you to manage the complete lifecycle of energy retailer migrations, contracts, and post-migration requests (representative changes, return to captive market, supply suspension) in Brazil.

## Client Setup

### VoltariumClient

The main client class for interacting with the CCEE API.

#### Constructor

```python
def __init__(
    self,
    *,
    base_url: str,
    client_id: str,
    client_secret: str,
    api_version: Literal["v1", "v1.1", "v2"] = "v2",
    timeout: float = 30.0,
    max_retries: int = 3,
) -> None:
```

**Parameters:**

- `base_url` (str): Base URL for the API
- `client_id` (str): OAuth2 client ID
- `client_secret` (str): OAuth2 client secret
- `api_version` (`Literal["v1", "v1.1", "v2"]`, optional): CCEE migrations API generation to
  target. Defaults to `"v2"` (the latest). See [API Versioning](#api-versioning-migrations) below.
- `timeout` (float, optional): Request timeout in seconds. Defaults to 30.0
- `max_retries` (int, optional): Maximum number of retries for failed requests. Defaults to 3

**Example:**
```python
client = VoltariumClient(
    base_url="https://api.ccee.org.br",
    client_id="your_client_id",
    client_secret="your_client_secret",
    timeout=60.0,
    max_retries=5
)
```

#### Context Manager

VoltariumClient supports async context management:

```python
async with VoltariumClient(...) as client:
    # Use client here
    pass
```

## API Versioning (Migrations)

CCEE's migrations API has three generations: `"v1"`, `"v1.1"`, and `"v2"`. Only the migrations
endpoints (create/list/get/update/delete) are versioned — contracts and measurements are always
`v1`. Pick a version once, at construction time, via `api_version`:

```python
client = VoltariumClient(..., api_version="v2")   # default
client = VoltariumClient(..., api_version="v1.1")
client = VoltariumClient(..., api_version="v1")    # pre-2.0 behavior
```

**`api_version` defaults to `"v2"` as of 2.0 — this is a breaking change from 1.x, which only
supported `v1`.** Pass `api_version="v1"` to keep the old behavior.

Not every operation has an endpoint at every version. Calls transparently fall back to the closest
older version that does have one:

| Operation | v1 | v1.1 | v2 |
|-----------|----|----|----|
| List | ✅ | ✅ | ✅ |
| Create | ✅ | ✅ (same body as v1) | ✅ (`CreateMigrationRequestV2`) |
| Get | ✅ | ✅ | ✅ |
| Update | ✅ | falls back to v1 | ✅ (same body as v1) |
| Delete | ✅ | falls back to v1 | falls back to v1 |

**V1 → V1.1**: no request-shape change. Makes the standardized consumer-unit code mandatory and
adds response-only fields (`process_siga_indicator`, on both `MigrationListItem` and `MigrationItem`).

**V1 → V2 (CP7 rules)**: the create request shape changes — `denunciation_date` is removed and
replaced by a required `utility_formalized` (`formalizacaoDistribuidora`, `"SIM"` or `"NAO"`) plus a
required `consumer_unit_tariff_subgroup` (`subGrupoTarifarioUnidadeConsumidora`). Two more fields are
conditionally required based on `utility_formalized`:

- `formalization_date` (`dataFormalizacao`) — required when `utility_formalized="SIM"`, must be
  omitted otherwise.
- `migration_modality` (`modalidadeMigracao`, `"REGULAR"` or `"ANTECIPADA"`) — required when
  `utility_formalized="NAO"`, must be omitted otherwise.

Because the shape genuinely differs, V2 creates use a separate `CreateMigrationRequestV2` model
(see [Create Migration (V2)](#create-migration-v2) below) instead of `CreateMigrationRequest`.
`create_migration` raises `TypeError` if you pass the wrong model for the client's resolved version.
Responses also gain `protocol_number`, `intended_utility_month`, `formalization_date`,
`migration_modality`, `consumer_unit_tariff_subgroup`, and `utility_formalized`.

## Migration Endpoints (🇧🇷 Migracoes)

The migration endpoints provide full CRUD (Create, Read, Update, Delete) operations for managing retailer migrations. All endpoints are asynchronous and include automatic authentication, error handling, and retry logic.

### Overview

The path prefix (`/v1/`, `/v1.1/`, or `/v2/`) is chosen automatically based on the client's
`api_version` — see [API Versioning](#api-versioning-migrations) above.

| Operation | Method | Endpoint | Description |
|-----------|--------|----------|-------------|
| [List Migrations](#list-migrations) | GET | `/{version}/varejista/migracoes` | List migrations with filtering and pagination |
| [Create Migration](#create-migration) | POST | `/{version}/varejista/migracoes` | Create a new migration |
| [Get Migration](#get-migration) | GET | `/{version}/varejista/migracoes/{id}` | Get a specific migration by ID |
| [Update Migration](#update-migration) | PUT | `/{version}/varejista/migracoes/{id}` | Update an existing migration |
| [Delete Migration](#delete-migration) | DELETE | `/v1/varejista/migracoes/{id}` | Delete a migration (no v1.1/v2 endpoint exists) |
| [List Contracts](#list-contracts) | GET | `/v1/varejista/contratos` | List retailer contracts with filtering and pagination |
| [Get Contract](#get-contract) | GET | `/v1/varejista/contratos/{id}` | Get a specific contract by ID |
| [Create Contract](#create-contract) | POST | `/v1/varejista/contratos` | Create a retailer contract |
| [Download Contract File](#download-contract-file) | GET | `/v1/varejista/contratos/{id}/arquivo` | Retrieve the signed contract document |

## List Migrations

Retrieve a paginated list of migrations with optional filtering.

### Usage

```python
async with VoltariumClient(...) as client:
    # Get all migrations for a date range
    migrations = client.list_migrations(
        initial_reference_month="2024-01",
        final_reference_month="2024-12",
        agent_code="12345",
        profile_code="67890"
    )

    # Process each migration
    async for migration in migrations:
        print(f"Migration {migration.migration_id}: {migration.migration_status}")
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `initial_reference_month` | `str` | Yes | Start reference month (YYYY-MM format) |
| `final_reference_month` | `str` | Yes | End reference month (YYYY-MM format) |
| `agent_code` | `str` | Yes | Agent code for the request |
| `profile_code` | `str` | Yes | Profile code for the request |
| `consumer_unit_code` | `str` | No | Filter by consumer unit code |
| `migration_status` | `str` | No | Filter by migration status |

### Response

Returns an async generator of `MigrationListItem` objects with the following fields:

```python
class MigrationListItem:
    migration_id: str
    consumer_unit_code: str
    utility_agent_consumer_unit_code: str
    utility_agent_code: int
    document_type: str
    document_number: str
    retailer_agent_code: int
    request_date: datetime
    retailer_profile_code: int
    migration_status: str
    submarket: str | None
    dhc_value: float | None
    musd_value: float | None
    penalty_payment: str | None
    justification: str | None
    validation_date: datetime | None
    consumer_unit_email: str
    comment: str | None
    supplier_agent_code: int | None
    reference_month: datetime
    denunciation_date: datetime | None  # absent on v1.1/v2 migrations formalized with the utility
    cer_celebration_id: str | None
    # V1.1+
    process_siga_indicator: str | None
    # V2+ (CP7)
    protocol_number: str | None
    intended_utility_month: str | None
    formalization_date: datetime | None
    migration_modality: Literal["REGULAR", "ANTECIPADA"] | None
    consumer_unit_tariff_subgroup: Literal["A2", "A3", "A3a", "A4", "AS", "B1", "B2", "B3", "B4"] | None
    utility_formalized: Literal["SIM", "NAO"] | None
```

## Contracts Endpoints (🇧🇷 Contratos)

### List Contracts

Retrieve a paginated list of retailer contracts with optional filtering.

```python
async with VoltariumClient(...) as client:
    # Filtering by utility is required in sandbox and often in production
    contracts = client.list_contracts(
        initial_reference_month="2024-01",
        final_reference_month="2024-12",
        agent_code="12345",
        profile_code="67890",
        utility_agent_code="100004",  # codigoAgenteConcessionaria
        consumer_unit_code=None,        # optional
        contract_status=None            # optional
    )

    async for contract in contracts:
        print(contract.contract_id)
```

Parameters mirror migration listing with `ListContractsParams`. Notable filters:

- `utility_agent_code` (`codigoAgenteConcessionaria`): utility filter (recommended/required)
- `consumer_unit_code` (`codigoUC`): optional
- `contract_status` (`statusContrato`): optional

### Get Contract

Retrieve a specific contract by its ID.

```python
async with VoltariumClient(...) as client:
    contract = await client.get_contract(
        contract_id="CONTRACT_ID_123",
        agent_code="12345",
        profile_code="67890",
    )

    print(contract.contract_id, contract.contract_status)
```

### Create Contract

Create a retailer contract.

```python
from voltarium.models import CreateContractRequest

async with VoltariumClient(...) as client:
    request = CreateContractRequest(
        codigoAgenteConcessionaria=100004,         # utility_agent_code
        codigoUnidadeConsumidora="UC123456",      # consumer_unit_code
        enderecoUnidadeConsumidora="Rua Exemplo, 123, Bairro Exemplo",  # consumer_unit_address
        nomeUnidadeConsumidora="Empresa XYZ",     # consumer_unit_name
        numeroDocumento="12345678901",            # document_number (CPF or CNPJ numeric)
        representantesLegais=[
            {
                "nomeContato": "Joao Silva",
                "nomeEmail": "email@exemplo.com",
                "numeroDocumento": "12345678901",
                "tipoContato": "UNIDADE_CONSUMIDORA",
                "tipoDocumento": "CPF",
            }
        ],
        tipoDocumento="CPF",                       # document_type
        telefoneUnidadeConsumidora="(11) 98765-4321",  # consumer_unit_phone
        cnpjFilialUnidadeConsumidora=None,               # branch CNPJ (omit for CPF)
        enderecoFilialUnidadeConsumidora=None,           # branch address (omit for CPF)
    )

    contract = await client.create_contract(
        contract_data=request,
        agent_code="12345",
        profile_code="67890",
    )

    print(contract.contract_id)
```

### Download Contract File

Download the generated PDF for a concluded contract. Contracts in status `CONCLUIDO` return a binary payload with headers indicating `content-type: application/pdf` and `content-disposition` containing the suggested filename.

```python
contract_file = await client.download_contract_file(
    contract_id="1cdf0c2f-332a-4d50-9939-7db74be62924",
    agent_code="12345",
    profile_code="67890",
)

with open(contract_file.filename, "wb") as fp:
    fp.write(contract_file.content)

```

**Response shape**

```python
ContractFile(
    contract_id="1cdf0c2f-332a-4d50-9939-7db74be62924",
    filename="1cdf0c2f-332a-4d50-9939-7db74be62924.pdf",
    content_type="application/pdf",
    content_base64="JVBERi0xLjUNCi4uLg==",
    content_length=78448,
)
```

## Measurements Endpoints (🇧🇷 Medições)

The measurements endpoints provide access to consumption measurements sent by utilities to retailers. These measurements represent energy consumption data for consumer units.

### Overview

| Operation | Method | Endpoint | Description |
|-----------|--------|----------|-------------|
| [List Measurements](#list-measurements) | GET | `/v1/varejista/consumo/medicoes` | List consumption measurements with filtering and pagination |

### List Measurements

Retrieve a paginated list of consumption measurements for a specific consumer unit.

```python
async with VoltariumClient(...) as client:
    # List measurements for a consumer unit
    measurements = client.list_measurements(
        consumer_unit_code="UC123456",
        utility_agent_code="100004",
        start_datetime="2024-09-01T00:00:00-03:00",
        end_datetime="2024-09-30T23:59:59-03:00",
        agent_code="12345",
        profile_code="67890"
    )

    async for measurement in measurements:
        print(f"Measurement {measurement.measurement_consumption_id}: {measurement.consumption} kWh")
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `consumer_unit_code` | `str` | Yes | Consumer unit code |
| `utility_agent_code` | `str \| int` | Yes | Utility agent code (concessionária) |
| `start_datetime` | `str` | Yes | Start datetime (ISO 8601 with timezone) |
| `end_datetime` | `str` | Yes | End datetime (ISO 8601 with timezone) |
| `agent_code` | `str \| int` | Yes | Agent code for the request |
| `profile_code` | `str \| int` | Yes | Profile code for the request |
| `measurement_status` | `str` | No | Filter by measurement status (CONSISTIDA, REJEITADA) |

### Important Constraints

- **Multi-Month Ranges**: The client automatically splits date ranges spanning multiple months into same-month chunks (CCEE API requirement). You can pass any range (e.g., last 30 days) and it will be handled transparently.
- **Date Range**: Only dates from August 2024 onwards are supported
- **Datetime Format**: Must be ISO 8601 with timezone (e.g., "2024-09-01T00:00:00-03:00")

### Response

Returns an async generator of `Measurement` objects with the following fields:

```python
class Measurement:
    measurement_consumption_id: str  # Unique measurement identifier
    consumer_unit_code: str          # Consumer unit code
    utility_agent_code: int          # Utility agent code
    reference_day: str               # Reference day (date)
    consumption_reference_date: str  # Consumption reference datetime
    consumption: float               # Consumption value in kWh
    consumption_type: str            # Type (AJUSTADO, MEDIDO, ESTIMADO)
    update_date: str                 # Last update datetime
    measurement_status: str          # Status (CONSISTIDA, REJEITADA)
```

### Example with Status Filter

```python
async def list_validated_measurements():
    async with VoltariumClient(...) as client:
        # Get only validated measurements (CONSISTIDA)
        measurements = client.list_measurements(
            consumer_unit_code="UC123456",
            utility_agent_code="100004",
            start_datetime="2024-09-01T00:00:00-03:00",
            end_datetime="2024-09-30T23:59:59-03:00",
            agent_code="12345",
            profile_code="67890",
            measurement_status="CONSISTIDA"
        )

        total_consumption = 0.0
        async for measurement in measurements:
            total_consumption += measurement.consumption
            print(f"Date: {measurement.reference_day}, "
                  f"Consumption: {measurement.consumption} kWh, "
                  f"Type: {measurement.consumption_type}")

        print(f"Total consumption: {total_consumption} kWh")
```

### Test Fixtures and Samples

Real API response samples are stored in `tests/fixtures/measurements/`:

- `raw_api_response.json` – Full response with multiple measurements (CONSISTIDA, REJEITADA)
- `paginated_response_page1.json` – Paginated response with `indexProximaPagina`
- `empty_response.json` – Empty medicoes array

To capture real samples when fetching:

```bash
uv run python scripts/fetch_measurements_past_30_days.py UC-TESTE 100004 --dump
```

### Error Handling

The measurements endpoint includes specific error codes:

- **`ERR_PERIODO_INVALIDO_MEDICOES`**: Dates are not within the same month/year (the client handles this automatically by splitting ranges)
- **`ERR_SISTEMA_MIGRACAO_IMPLATADO_MEDICOES`**: Dates are before system implementation (08/2024)
- **`ERR_VALIDACAO_CAMPOS`**: Missing or invalid required fields

```python
from voltarium.exceptions import ValidationError

async def safe_list_measurements():
    async with VoltariumClient(...) as client:
        try:
            measurements = client.list_measurements(
                consumer_unit_code="UC123456",
                utility_agent_code="100004",
                start_datetime="2024-09-01T00:00:00-03:00",
                end_datetime="2024-09-30T23:59:59-03:00",
                agent_code="12345",
                profile_code="67890"
            )

            measurement_list = []
            async for measurement in measurements:
                measurement_list.append(measurement)

            return measurement_list

        except ValidationError as e:
            if "ERR_PERIODO_INVALIDO_MEDICOES" in e.code:
                print("Error: Start and end dates must be in the same month")
            elif "ERR_SISTEMA_MIGRACAO_IMPLATADO_MEDICOES" in e.code:
                print("Error: Dates must be from August 2024 onwards")
            else:
                print(f"Validation error: {e.message}")
            raise
```

### Example

```python
async def list_all_migrations():
    async with VoltariumClient(...) as client:
        # List migrations with filtering
        migrations = client.list_migrations(
            initial_reference_month="2024-01",
            final_reference_month="2024-03",
            agent_code="12345",
            profile_code="67890",
            consumer_unit_code="UC123456",  # Optional filter
            migration_status="PENDING"      # Optional filter
        )

        migration_list = []
        async for migration in migrations:
            migration_list.append(migration)
            print(f"Found migration: {migration.migration_id}")

        print(f"Total migrations found: {len(migration_list)}")
        return migration_list
```

## Create Migration

Create a new retailer migration.

### Usage

```python
from voltarium import CreateMigrationRequest

async with VoltariumClient(...) as client:
    # Create a migration request
    request = CreateMigrationRequest(
        consumer_unit_code="12345",
        utility_agent_code=123,
        document_type="CNPJ",
        document_number="12345678901234",
        retailer_agent_code=456,
        reference_month="2024-01",
        denunciation_date="2024-01-15",
        retailer_profile_code=789,
        consumer_unit_email="contact@example.com",
        comment="Migration request comment"
    )

    # Create the migration
    migration = await client.create_migration(
        migration_data=request,
        agent_code="12345",
        profile_code="67890"
    )

    print(f"Created migration: {migration.migration_id}")
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `migration_data` | `CreateMigrationRequest` | Yes | Migration data object |
| `agent_code` | `str` | Yes | Agent code for the request |
| `profile_code` | `str` | Yes | Profile code for the request |

### CreateMigrationRequest Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `consumer_unit_code` | `str` | Yes | Consumer unit code |
| `utility_agent_code` | `int \| str` | Yes | Utility agent code |
| `document_type` | `Literal["CNPJ"]` | Yes | Document type (only CNPJ supported) |
| `document_number` | `str` | Yes | Document number (will be validated) |
| `retailer_agent_code` | `int \| str` | Yes | Retailer agent code |
| `reference_month` | `str` | Yes | Reference month (YYYY-MM format) |
| `denunciation_date` | `str` | Yes | Denunciation date (YYYY-MM-DD format) |
| `retailer_profile_code` | `int \| str` | Yes | Retailer profile code |
| `consumer_unit_email` | `str` | Yes | Consumer unit email |
| `comment` | `str` | No | Optional comment |

### Response

Returns a `MigrationItem` object with the created migration details.

### Example

```python
async def create_migration():
    async with VoltariumClient(...) as client:
        try:
            request = CreateMigrationRequest(
                consumer_unit_code="UC123456",
                utility_agent_code=100,
                document_type="CNPJ",
                document_number="12.345.678/0001-90",  # Will be automatically cleaned
                retailer_agent_code=200,
                reference_month="2024-06",
                denunciation_date="2024-06-15",
                retailer_profile_code=300,
                consumer_unit_email="billing@company.com",
                comment="Quarterly migration request"
            )

            migration = await client.create_migration(
                migration_data=request,
                agent_code="12345",
                profile_code="67890"
            )

            print(f"✅ Migration created successfully!")
            print(f"   ID: {migration.migration_id}")
            print(f"   Status: {migration.migration_status}")
            print(f"   Request Date: {migration.request_date}")

            return migration

        except ValidationError as e:
            print(f"❌ Validation error: {e.message}")
        except AuthenticationError:
            print("❌ Authentication failed")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
```

## Create Migration (V2)

When the client resolves to `api_version="v2"` for creates (the default), `create_migration`
expects a `CreateMigrationRequestV2` instead of `CreateMigrationRequest`.

### Usage

```python
from voltarium import CreateMigrationRequestV2

async with VoltariumClient(...) as client:  # api_version="v2" by default
    request = CreateMigrationRequestV2(
        consumer_unit_code="12345",
        utility_agent_code=123,
        document_type="CNPJ",
        document_number="12345678901234",
        retailer_agent_code=456,
        reference_month="2024-01",
        retailer_profile_code=789,
        consumer_unit_email="contact@example.com",
        consumer_unit_tariff_subgroup="A3a",
        utility_formalized="SIM",
        formalization_date="2024-01-15",   # required because utility_formalized == "SIM"
        # migration_modality omitted — forbidden when utility_formalized == "SIM"
        comment="Migration request comment",
    )

    migration = await client.create_migration(
        migration_data=request,
        agent_code="12345",
        profile_code="67890"
    )

    print(f"Created migration: {migration.migration_id}")
```

### CreateMigrationRequestV2 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `consumer_unit_code` | `str` | Yes | Consumer unit code |
| `utility_agent_code` | `int \| str` | Yes | Utility agent code |
| `document_type` | `Literal["CPF", "CNPJ"]` | Yes | Document type |
| `document_number` | `str` | Conditional | Required for CNPJ, omit for CPF |
| `retailer_agent_code` | `int \| str` | Yes | Retailer agent code |
| `reference_month` | `str` | Yes | Reference month (YYYY-MM format) |
| `retailer_profile_code` | `int \| str` | Yes | Retailer profile code |
| `consumer_unit_email` | `str` | Yes | Consumer unit email |
| `consumer_unit_tariff_subgroup` | `Literal["A2","A3","A3a","A4","AS","B1","B2","B3","B4"]` | Yes | Consumer unit tariff subgroup |
| `utility_formalized` | `Literal["SIM", "NAO"]` | Yes | Whether formalized with the utility |
| `formalization_date` | `str` | Conditional | Required (YYYY-MM-DD) when `utility_formalized="SIM"`; must be omitted otherwise |
| `migration_modality` | `Literal["REGULAR", "ANTECIPADA"]` | Conditional | Required when `utility_formalized="NAO"`; must be omitted otherwise |
| `comment` | `str` | No | Optional comment |

Note: unlike `CreateMigrationRequest` (v1/v1.1), there is no `denunciation_date` field — CCEE
replaced it with the `utility_formalized`/`formalization_date`/`migration_modality` workflow above.

## Get Migration

Retrieve a specific migration by its ID.

### Usage

```python
async with VoltariumClient(...) as client:
    migration = await client.get_migration(
        migration_id="MIGRATION_ID_123",
        agent_code="12345",
        profile_code="67890"
    )

    print(f"Migration status: {migration.migration_status}")
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `migration_id` | `str` | Yes | Unique migration ID |
| `agent_code` | `str` | Yes | Agent code for the request |
| `profile_code` | `str` | Yes | Profile code for the request |

### Response

Returns a `MigrationItem` object with detailed migration information.

### Example

```python
async def get_migration_details(migration_id: str):
    async with VoltariumClient(...) as client:
        try:
            migration = await client.get_migration(
                migration_id=migration_id,
                agent_code="12345",
                profile_code="67890"
            )

            print(f"📋 Migration Details:")
            print(f"   ID: {migration.migration_id}")
            print(f"   Status: {migration.migration_status}")
            print(f"   Consumer Unit: {migration.consumer_unit_code}")
            print(f"   Email: {migration.consumer_unit_email}")
            print(f"   Request Date: {migration.request_date}")

            if migration.validation_date:
                print(f"   Validation Date: {migration.validation_date}")

            if migration.comment:
                print(f"   Comment: {migration.comment}")

            return migration

        except NotFoundError:
            print(f"❌ Migration {migration_id} not found")
        except AuthenticationError:
            print("❌ Authentication failed")
```

## Update Migration

Update an existing migration.

### Usage

```python
from voltarium import UpdateMigrationRequest

async with VoltariumClient(...) as client:
    # Create update request
    update_request = UpdateMigrationRequest(
        reference_month="2024-02",
        retailer_profile_code=789,
        document_type="CNPJ",
        document_number="12345678901234",
        consumer_unit_email="updated@example.com"
    )

    # Update the migration
    migration = await client.update_migration(
        migration_id="MIGRATION_ID_123",
        migration_data=update_request,
        agent_code="12345",
        profile_code="67890"
    )

    print(f"Updated migration: {migration.migration_id}")
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `migration_id` | `str` | Yes | Unique migration ID |
| `migration_data` | `UpdateMigrationRequest` | Yes | Updated migration data |
| `agent_code` | `str` | Yes | Agent code for the request |
| `profile_code` | `str` | Yes | Profile code for the request |

### UpdateMigrationRequest Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reference_month` | `str` | Yes | Reference month (YYYY-MM format) |
| `retailer_profile_code` | `int \| str` | Yes | Retailer profile code |
| `document_type` | `Literal["CPF", "CNPJ"]` | Yes | Document type |
| `document_number` | `str` | Yes | Document number (will be validated) |
| `consumer_unit_email` | `str` | Yes | Consumer unit email |

### Response

Returns a `MigrationItem` object with the updated migration details.

## Delete Migration

Delete an existing migration.

### Usage

```python
async with VoltariumClient(...) as client:
    await client.delete_migration(
        migration_id="MIGRATION_ID_123",
        agent_code="12345",
        profile_code="67890"
    )

    print("Migration deleted successfully")
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `migration_id` | `str` | Yes | Unique migration ID |
| `agent_code` | `str` | Yes | Agent code for the request |
| `profile_code` | `str` | Yes | Profile code for the request |

### Response

Returns `None` on successful deletion.

### Example

```python
async def delete_migration_safely(migration_id: str):
    async with VoltariumClient(...) as client:
        try:
            # First, get the migration to confirm it exists
            migration = await client.get_migration(
                migration_id=migration_id,
                agent_code="12345",
                profile_code="67890"
            )

            print(f"⚠️  About to delete migration:")
            print(f"   ID: {migration.migration_id}")
            print(f"   Status: {migration.migration_status}")
            print(f"   Consumer Unit: {migration.consumer_unit_code}")

            # Delete the migration
            await client.delete_migration(
                migration_id=migration_id,
                agent_code="12345",
                profile_code="67890"
            )

            print("✅ Migration deleted successfully")

        except NotFoundError:
            print(f"❌ Migration {migration_id} not found")
        except AuthenticationError:
            print("❌ Authentication failed")
```

## Change Request Endpoints (🇧🇷 Solicitações)

After a migration is concluded, either party can request further changes: a new retailer can
request to become the consumer unit's representative (troca de representante), the utility can
request the consumer unit's return to the captive market (retorno ao cativo), and either the
retailer or the utility can request supply suspension. The counterparty then approves or rejects
the request via a single generic endpoint. All change-request endpoints require an already
`CONCLUIDA` migration for the target consumer unit.

### Overview

| Operation | Method | Endpoint | Description |
|-----------|--------|----------|-------------|
| [Create Return-to-Captive Request](#create-return-to-captive-request) | POST | `/v1/solicitacoes/retorno-cativo` | Utility requests a consumer unit's return to the captive market |
| [Create Representative Change Request](#create-representative-change-request) | POST | `/v1/solicitacoes/representante` | New retailer requests to become the consumer unit's representative |
| [Create Supply Suspension (Retailer)](#create-supply-suspension-by-retailer) | POST | `/v1/solicitacoes/suspensao-fornecimento-varejista` | Retailer requests supply suspension |
| [Create Supply Suspension (Utility)](#create-supply-suspension-by-utility) | POST | `/v1/solicitacoes/suspensao-fornecimento-concessionaria` | Utility requests supply suspension (delinquency) |
| [Update Change Request Status](#update-change-request-status) | POST | `/v1/solicitacoes/{id}` | Counterparty approves or rejects a change request |
| [List Change Requests](#list-change-requests) | GET | `/v1/solicitacoes` | List/query change requests with filtering and pagination |

### Create Return-to-Captive Request

```python
from voltarium import CreateReturnToCaptiveRequest

async with VoltariumClient(...) as client:
    request = CreateReturnToCaptiveRequest(
        consumer_unit_code="UC123456",
        reference_month="2024-06",
        cer_celebration_id="NAO",
        request_type="ALTERACAO_RETORNO_CATIVO_DESLIGAMENTO",
    )

    change_request = await client.create_return_to_captive_request(
        request_data=request,
        agent_code="100004",   # utility agent code
        profile_code="100004",
    )

    print(change_request.change_request_id, change_request.request_status)
```

`request_type` accepts `ALTERACAO_RETORNO_CATIVO_RESILICAO` (auto-approved after 90 days from
the reference month if the current retailer doesn't respond), `ALTERACAO_RETORNO_CATIVO_RESOLUCAO`
(same, 15 days), or `ALTERACAO_RETORNO_CATIVO_DESLIGAMENTO` (auto-approved immediately, for a
retailer disconnection).

### Create Representative Change Request

```python
from voltarium import CreateRepresentativeChangeRequest

async with VoltariumClient(...) as client:
    request = CreateRepresentativeChangeRequest(
        consumer_unit_code="UC123456",
        utility_agent_code=100004,
        new_retailer_agent_code=200001,
        new_retailer_profile_code=200110,
        reference_month="2024-06",
        request_type="ALTERACAO_ALFA_VAREJISTA_RESILICAO",
    )

    change_request = await client.create_representative_change_request(
        request_data=request,
        agent_code="200001",   # new retailer's own agent code
        profile_code="200110",
    )

    print(change_request.change_request_id)
```

`request_type` accepts `ALTERACAO_ALFA_VAREJISTA_RESILICAO` (90-day auto-approval),
`ALTERACAO_ALFA_VAREJISTA_RESOLUCAO` (15-day auto-approval), or
`ALTERACAO_ALFA_VAREJISTA_DESLIGAMENTO` (auto-approved, current retailer disconnection).

### Create Supply Suspension (by Retailer)

```python
from voltarium import CreateSupplySuspensionByRetailerRequest

async with VoltariumClient(...) as client:
    request = CreateSupplySuspensionByRetailerRequest(
        consumer_unit_code="UC123456",
        utility_agent_code=100004,
        request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
        notification_date="2024-03-01",
    )

    change_request = await client.create_supply_suspension_by_retailer(
        request_data=request,
        agent_code="200001",
        profile_code="200110",
    )
```

`request_type` only accepts `SUSPENSAO_FORNECIMENTO_RESILICAO` or
`SUSPENSAO_FORNECIMENTO_RESOLUCAO` — `SUSPENSAO_FORNECIMENTO_DESLIGAMENTO` is generated
automatically by CCEE on retailer disconnection and cannot be submitted (confirmed against the
sandbox: `ERR_TIPO_SOLICITACAO_INVALIDO`). `notification_date` (`YYYY-MM-DD`) is required for
every submittable type.

### Create Supply Suspension (by Utility)

```python
from voltarium import CreateSupplySuspensionByUtilityRequest

async with VoltariumClient(...) as client:
    request = CreateSupplySuspensionByUtilityRequest(
        consumer_unit_code="UC123456",
        notification_date="2024-03-01",
        # utility_agent_code omitted — this endpoint is always called by the utility itself,
        # so it defaults to `agent_code` below; pass it explicitly only to override that.
    )

    change_request = await client.create_supply_suspension_by_utility(
        request_data=request,
        agent_code="100004",
        profile_code="100004",
    )
```

Used by the utility when the retailer becomes delinquent; `request_type` defaults to (and only
accepts) `SUSPENSAO_FORNECIMENTO_RESOLUCAO_UC_CONCESSIONARIA`. `notification_date` is required.
`utility_agent_code` is optional — confirmed against the sandbox that omitting
`codigoAgenteConcessionaria` produces identical behavior to sending the calling agent's own
code, so `create_supply_suspension_by_utility` fills it in from `agent_code` when not set.

### Update Change Request Status

Approve or reject a pending change request. Called by the counterparty of whoever created it
(e.g. the current retailer approves/rejects a representative-change request from a new retailer).

```python
from voltarium import UpdateChangeRequestStatusRequest

async with VoltariumClient(...) as client:
    update = UpdateChangeRequestStatusRequest(
        request_status="CONCLUIDA",   # or "REPROVADA" to reject
        request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",  # must match the original request
        justification="Approved after manual review",
    )

    change_request = await client.update_change_request_status(
        change_request_id=change_request.change_request_id,
        request_data=update,
        agent_code="100004",
        profile_code="100004",
    )

    print(change_request.request_status)
```

### List Change Requests

```python
async with VoltariumClient(...) as client:
    # Either a reference-month range OR a request-date range is required (not both, not neither)
    change_requests = client.list_change_requests(
        agent_code="200001",
        profile_code="200110",
        request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
        initial_reference_month="2024-01",
        final_reference_month="2024-12",
        request_status="CRIADA",       # optional — omit it to match every status
        consumer_unit_code=None,       # optional
    )

    async for change_request in change_requests:
        print(change_request.change_request_id, change_request.request_status)
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_code` | `str \| int` | Yes | Agent code for the request |
| `profile_code` | `str \| int` | Yes | Profile code for the request |
| `request_type` | `str` | Yes | Change request type filter (tipoSolicitacao) — confirmed required by the sandbox |
| `request_status` | `str` | No | Change request status filter (situacaoAlteracao) — confirmed optional against the sandbox; omitting it returns requests of every status |
| `initial_reference_month` / `final_reference_month` | `str` | Conditional | Reference month range (YYYY-MM); mutually exclusive with the request-date range |
| `initial_request_date` / `final_request_date` | `str` | Conditional | Request date range (YYYY-MM-DD); mutually exclusive with the reference-month range |
| `consumer_unit_code` | `str` | No | Filter by consumer unit code |

Like `list_migrations`/`list_contracts`, ranges spanning more than 12 months are automatically
split into ≤12-month windows and paginated transparently.

### Response

Every change-request operation returns (or yields, for `list_change_requests`) a `ChangeRequest`:

```python
class ChangeRequest:
    change_request_id: str
    consumer_unit_code: str
    utility_agent_code: int
    request_type: str
    request_status: str
    request_date: datetime
    reference_month: datetime | None
    changed_migration_id: str | None
    advance_indicator: str | None
    new_retailer_agent_code: int | None
    new_retailer_profile_code: int | None
    current_retailer_agent_code: int | None
    current_retailer_profile_code: int | None
    justification: str | None
    delay_date: str | None
    notification_date: str | None
    cer_celebration_id: str | None
```

Most fields are optional since which ones are populated depends on `request_type` — e.g.
`new_retailer_agent_code`/`new_retailer_profile_code` are only set for representative-change
requests.

## Error Handling

All endpoints include comprehensive error handling:

### Common Exceptions

- **`AuthenticationError`**: Invalid credentials or expired tokens
- **`ValidationError`**: Invalid request data or parameters
- **`NotFoundError`**: Migration or resource not found
- **`RateLimitError`**: API rate limit exceeded
- **`ServerError`**: Internal server error

### Best Practices

1. **Always use try-catch blocks** for production code
2. **Handle specific exception types** rather than generic exceptions
3. **Implement retry logic** for transient failures
4. **Log errors appropriately** for debugging

```python
from voltarium.exceptions import (
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    ServerError
)

async def robust_migration_operation():
    async with VoltariumClient(...) as client:
        try:
            # Your migration operation here
            result = await client.create_migration(...)
            return result

        except ValidationError as e:
            logger.error(f"Validation failed: {e.message}")
            raise
        except AuthenticationError:
            logger.error("Authentication failed - check credentials")
            raise
        except NotFoundError:
            logger.warning("Resource not found")
            return None
        except RateLimitError:
            logger.warning("Rate limit exceeded - retrying later")
            await asyncio.sleep(60)  # Wait and retry
            return await robust_migration_operation()
        except ServerError as e:
            logger.error(f"Server error: {e.status_code}")
            raise
```

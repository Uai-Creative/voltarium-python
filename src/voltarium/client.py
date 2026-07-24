"""Main Voltarium client for CCEE API."""

import time
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from types import TracebackType
from typing import Any, Literal, Self

import httpx
from httpx import Response
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from voltarium.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from voltarium.models import (
    ApiHeaders,
    Contract,
    ContractFile,
    CreateContractRequest,
    CreateMigrationRequest,
    CreateMigrationRequestV2,
    ListContractsParams,
    ListMeasurementsParams,
    ListMigrationsParams,
    Measurement,
    MigrationItem,
    MigrationListItem,
    Token,
    UpdateMigrationRequest,
)

PRODUCTION_BASE_URL = "https://api-abm.ccee.org.br"
SANDBOX_BASE_URL = "https://sandbox-api-abm.ccee.org.br"

# The three CCEE migrations API generations this client understands. Kept as a closed
# Literal (not a bare str) so IDEs/type checkers surface the exact choices and reject typos.
MigrationApiVersion = Literal["v1", "v1.1", "v2"]

# Which migrations operations exist at each API version, per the CCEE Postman collection.
# V1.1 has no distinct edit endpoint; neither V1.1 nor V2 documents a delete endpoint.
_MIGRATION_ENDPOINT_VERSIONS: dict[str, tuple[MigrationApiVersion, ...]] = {
    "list": ("v1", "v1.1", "v2"),
    "create": ("v1", "v1.1", "v2"),
    "get": ("v1", "v1.1", "v2"),
    "update": ("v1", "v2"),
    "delete": ("v1",),
}
_MIGRATION_VERSION_ORDER: tuple[MigrationApiVersion, ...] = ("v2", "v1.1", "v1")


def _split_datetime_range_by_month(start_str: str, end_str: str) -> list[tuple[str, str]]:
    """Split a datetime range into same-month chunks (CCEE API requirement).

    The measurements endpoint requires start and end datetimes to be within
    the same month/year. This helper splits arbitrary ranges accordingly.
    """
    start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
    if start > end:
        raise ValueError("start_datetime must be before or equal to end_datetime")

    ranges: list[tuple[str, str]] = []
    current_start = start
    tz = start.tzinfo

    while current_start <= end:
        year, month = current_start.year, current_start.month
        next_month = datetime(year + 1, 1, 1, tzinfo=tz) if month == 12 else datetime(year, month + 1, 1, tzinfo=tz)
        month_end = next_month - timedelta(seconds=1)
        range_end = min(month_end, end)
        ranges.append((current_start.isoformat(), range_end.isoformat()))
        current_start = month_end + timedelta(seconds=1)

    return ranges


def _split_month_range(initial_month: str, final_month: str, max_months: int = 12) -> list[tuple[str, str]]:
    """Split a YYYY-MM range into chunks of at most *max_months* months.

    CCEE's migrations and contracts endpoints reject requests whose date range
    exceeds 12 months (ERR_MES_REFERENCIA_INICIAL_DIFERENCA).  This helper
    transparently chunks the caller's range so the client can issue multiple
    requests without the caller needing to know about the limit.

    Raises:
        ValueError: if max_months < 1 or initial_month is after final_month.
    """
    if max_months < 1:
        raise ValueError(f"max_months must be >= 1, got {max_months}")

    from datetime import date  # noqa: PLC0415

    def _parse(s: str) -> date:
        y, m = map(int, s.split("-"))
        return date(y, m, 1)

    def _add_months(d: date, n: int) -> date:
        """Advance a first-of-month date by n months."""
        result = d
        for _ in range(n):
            result = (result.replace(day=28) + timedelta(days=4)).replace(day=1)
        return result

    start = _parse(initial_month)
    end = _parse(final_month)

    if start > end:
        raise ValueError(f"initial_month ({initial_month}) must be <= final_month ({final_month})")

    ranges: list[tuple[str, str]] = []
    cur = start
    while cur <= end:
        window_end = min(_add_months(cur, max_months - 1), end)
        ranges.append((cur.strftime("%Y-%m"), window_end.strftime("%Y-%m")))
        cur = _add_months(window_end, 1)

    return ranges


class VoltariumClient:
    """Asynchronous client for CCEE API."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = PRODUCTION_BASE_URL,
        api_version: MigrationApiVersion = "v2",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Base URL for the API
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            api_version: CCEE migrations API generation to target ("v1", "v1.1", or "v2").
                Defaults to "v2" (the latest). Operations without an endpoint at the
                configured version transparently fall back to the closest older version
                that has one (see `_MIGRATION_ENDPOINT_VERSIONS`). Pass "v1" to keep the
                pre-2.0 behavior of this client.
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        # Remove trailing slashes
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries

        # Internal state
        self._http_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
        )
        self._token: Token | None = None

    def _resolve_migration_version(self, operation: str) -> MigrationApiVersion:
        """Resolve the actual API version to use for a migrations operation.

        Falls back from `self.api_version` toward "v1" until it finds a version that
        actually has an endpoint for this operation.
        """
        supported = _MIGRATION_ENDPOINT_VERSIONS[operation]
        start = _MIGRATION_VERSION_ORDER.index(self.api_version)
        for candidate in _MIGRATION_VERSION_ORDER[start:]:
            if candidate in supported:
                return candidate
        return "v1"  # unreachable in practice: v1 supports every operation

    async def _refresh_token(self) -> None:
        """Get access token, refreshing if needed."""
        try:
            response = await self._http_client.post(
                "/sso/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid credentials") from e
            raise

        token_data = response.json()
        self._token = Token.model_validate(token_data)

    async def _get_access_token(self) -> str:
        # Check if we have a valid cached token
        if self._token and time.time() < self._token.expires_at - 30:  # 30s buffer
            return self._token.access_token
        # If no valid token, refresh it
        await self._refresh_token()
        assert self._token is not None  # refresh_token sets this
        return self._token.access_token

    async def _get_auth_header(self) -> dict[str, str]:
        """Get authorization header."""
        token = await self._get_access_token()
        return {"Authorization": f"Bearer {token}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Response:
        """Make an authenticated request to the API.

        Args:
            method: HTTP method
            path: API path
            headers: Additional headers
            params: Query parameters
            json: JSON body

        Returns:
            Response object

        Raises:
            AuthenticationError: If authentication fails
            ValidationError: If request validation fails
            NotFoundError: If resource not found
            RateLimitError: If rate limit exceeded
            ServerError: If server error occurs
            VoltariumError: For other API errors
        """
        is_retry = False

        retry_strategy = AsyncRetrying(
            reraise=True,
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type(AuthenticationError),
        )
        async for attempt in retry_strategy:
            with attempt:
                if is_retry:
                    # Force token refresh on retries
                    self._token = None
                    await self._refresh_token()
                is_retry = True

                auth_headers = await self._get_auth_header()
                request_headers = {
                    "Accept": "application/json",
                    **auth_headers,
                }
                if json is not None:
                    request_headers["Content-Type"] = "application/json"
                if headers:
                    request_headers.update(headers)

                response = await self._http_client.request(
                    method=method,
                    url=path,
                    headers=request_headers,
                    params=params,
                    json=json,
                )
                self._raise_for_status(response=response)
        return response

    def _raise_for_status(self, response: Response) -> None:
        """Handle API response and raise appropriate exceptions."""

        if response.status_code < 400:
            response.raise_for_status()
            return

        try:
            content = response.json()
        except ValueError:
            content = {}

        if response.status_code == 401:
            raise AuthenticationError("???")
        if response.status_code == 403:
            if "ERR_CREDENCIAL_INVALID" in content.get("error", ""):
                raise AuthenticationError("Invalid credentials")
        elif response.status_code == 404:
            raise NotFoundError("Resource not found")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code == 400:
            raw_code = content.get("error")
            error_code = raw_code if isinstance(raw_code, str) else str(raw_code or "unknown_error")

            raw_message = content.get("message")
            error_message = (
                raw_message if isinstance(raw_message, str) else str(raw_message or "Unknown validation error")
            )

            raise ValidationError(code=error_code, message=error_message)
        response.raise_for_status()

    # Migration endpoints

    async def list_migrations(
        self,
        initial_reference_month: str,
        final_reference_month: str,
        agent_code: str | int,
        profile_code: str | int,
        consumer_unit_code: str | None = None,
        migration_status: str | None = None,
    ) -> AsyncGenerator[MigrationListItem]:
        """List migrations for a retailer.

        Args:
            initial_reference_month: Start reference month (YYYY-MM)
            final_reference_month: End reference month (YYYY-MM)
            agent_code: Agent code
            profile_code: Profile code
            consumer_unit_code: Optional consumer unit code filter
            migration_status: Optional migration status filter

        Returns:
            AsyncGenerator of migrations
        """
        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )
        version = self._resolve_migration_version("list")

        for window_start, window_end in _split_month_range(initial_reference_month, final_reference_month):
            params_model = ListMigrationsParams(
                initial_reference_month=window_start,
                final_reference_month=window_end,
                retailer_profile_code=str(profile_code),
                consumer_unit_code=consumer_unit_code,
                migration_status=migration_status,
            )

            async def _get_page(page_index: str | None = None, _params=params_model) -> Response:
                _params.next_page_index = page_index
                return await self._request(
                    method="GET",
                    path=f"/{version}/varejista/migracoes",
                    headers=headers_model.model_dump(by_alias=True),
                    params=_params.model_dump(by_alias=True, exclude_none=True),
                )

            page_index = None
            while True:
                response = await _get_page(page_index)
                data = response.json()

                for migration_data in data.get("migracao", []):
                    yield MigrationListItem.model_validate(migration_data)

                page_index = data.get("indexProximaPagina")
                if page_index is None:
                    break

    async def create_migration(
        self,
        migration_data: CreateMigrationRequest | CreateMigrationRequestV2,
        agent_code: str | int,
        profile_code: str | int,
    ) -> MigrationItem:
        """Create a new migration.

        Args:
            migration_data: Migration data. Must be a `CreateMigrationRequestV2` when this
                client resolves to API version "v2" for the create operation, or a
                `CreateMigrationRequest` otherwise (v1/v1.1 share the same request shape).
            agent_code: Agent code
            profile_code: Profile code

        Returns:
            Created migration

        Raises:
            TypeError: If migration_data's type doesn't match the resolved API version.
        """
        # Create headers model
        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )
        version = self._resolve_migration_version("create")

        if version == "v2" and not isinstance(migration_data, CreateMigrationRequestV2):
            raise TypeError(
                "api_version resolved to 'v2' for create_migration; migration_data must be a "
                "CreateMigrationRequestV2 instance."
            )
        if version != "v2" and not isinstance(migration_data, CreateMigrationRequest):
            raise TypeError(
                f"api_version resolved to {version!r} for create_migration; migration_data must be a "
                "CreateMigrationRequest instance."
            )

        # Use model_dump with by_alias=True to get Portuguese field names for the API
        json_data = migration_data.model_dump(by_alias=True, exclude_none=True)

        response = await self._request(
            method="POST",
            path=f"/{version}/varejista/migracoes",
            headers=headers_model.model_dump(by_alias=True),
            json=json_data,
        )

        return MigrationItem.model_validate(response.json())

    async def get_migration(
        self,
        agent_code: str | int,
        profile_code: str | int,
        migration_id: str,
    ) -> MigrationItem:
        """Get a migration by ID.

        Args:
            agent_code: Agent code
            profile_code: Profile code
            migration_id: Migration ID

        Returns:
            Migration details
        """
        # Create headers model
        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )
        version = self._resolve_migration_version("get")

        response = await self._request(
            method="GET",
            path=f"/{version}/varejista/migracoes/{migration_id}",
            headers=headers_model.model_dump(by_alias=True),
        )

        data = response.json()
        if isinstance(data, list) and data:
            return MigrationItem.model_validate(data[0])
        return MigrationItem.model_validate(data)

    async def update_migration(
        self,
        migration_id: str,
        migration_data: UpdateMigrationRequest,
        agent_code: str | int,
        profile_code: str | int,
    ) -> MigrationItem:
        """Update a migration.

        Args:
            migration_id: Migration ID
            migration_data: Updated migration data
            agent_code: Agent code
            profile_code: Profile code

        Returns:
            Updated migration
        """
        # Create headers model
        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )
        version = self._resolve_migration_version("update")

        # Use model_dump with by_alias=True to get Portuguese field names for the API
        json_data = migration_data.model_dump(by_alias=True, exclude_none=True)

        response = await self._request(
            method="PUT",
            path=f"/{version}/varejista/migracoes/{migration_id}",
            headers=headers_model.model_dump(by_alias=True),
            json=json_data,
        )

        return MigrationItem.model_validate(response.json())

    async def delete_migration(
        self,
        migration_id: str,
        agent_code: str | int,
        profile_code: str | int,
    ) -> None:
        """Delete a migration.

        Args:
            migration_id: Migration ID
            agent_code: Agent code
            profile_code: Profile code
        """
        # Create headers model
        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )
        version = self._resolve_migration_version("delete")

        await self._request(
            method="DELETE",
            path=f"/{version}/varejista/migracoes/{migration_id}",
            headers=headers_model.model_dump(by_alias=True),
        )

    # Contracts endpoints

    async def list_contracts(
        self,
        initial_reference_month: str,
        final_reference_month: str,
        agent_code: str | int,
        profile_code: str | int,
        utility_agent_code: str | int | None = None,
        consumer_unit_code: str | None = None,
        contract_status: str | None = None,
    ) -> AsyncGenerator[Contract]:
        """List retailer contracts with filtering and pagination.

        Mirrors list_migrations pattern.
        """
        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )

        for window_start, window_end in _split_month_range(initial_reference_month, final_reference_month):
            params_model = ListContractsParams(
                initial_reference_month=window_start,
                final_reference_month=window_end,
                retailer_profile_code=str(profile_code),
                utility_agent_code=str(utility_agent_code) if utility_agent_code is not None else None,
                consumer_unit_code=consumer_unit_code,
                contract_status=contract_status,
            )

            async def _get_page(page_index: str | None = None, _params=params_model) -> Response:
                _params.next_page_index = page_index
                return await self._request(
                    method="GET",
                    path="/v1/varejista/contratos",
                    headers=headers_model.model_dump(by_alias=True),
                    params=_params.model_dump(by_alias=True, exclude_none=True),
                )

            page_index = None
            while True:
                response = await _get_page(page_index)
                data = response.json()

                for contract_data in data.get("contratos", data.get("contrato", [])):
                    yield Contract.model_validate(contract_data)

                page_index = data.get("indexProximaPagina")
                if page_index is None:
                    break

    async def get_contract(
        self,
        contract_id: str,
        agent_code: str | int,
        profile_code: str | int,
    ) -> Contract:
        """Get a contract by ID."""
        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )

        response = await self._request(
            method="GET",
            path=f"/v1/varejista/contratos/{contract_id}",
            headers=headers_model.model_dump(by_alias=True),
        )

        body = response.json()
        # Some endpoints return array for single item; support both
        if isinstance(body, list) and body:
            return Contract.model_validate(body[0])
        return Contract.model_validate(body)

    async def create_contract(
        self,
        contract_data: CreateContractRequest,
        agent_code: str | int,
        profile_code: str | int,
    ) -> Contract:
        """Create a retailer contract (POST /v1/varejista/contratos)."""
        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )

        # Use model_dump with by_alias=True to match Portuguese field names
        json_data = contract_data.model_dump(by_alias=True, exclude_none=True)

        response = await self._request(
            method="POST",
            path="/v1/varejista/contratos",
            headers=headers_model.model_dump(by_alias=True),
            json=json_data,
        )

        body = response.json()
        if isinstance(body, list) and body:
            return Contract.model_validate(body[0])
        return Contract.model_validate(body)

    async def download_contract_file(
        self,
        contract_id: str,
        agent_code: str | int,
        profile_code: str | int,
    ) -> ContractFile:
        """Download the binary file for a concluded contract.

        Returns metadata and base64-encoded payload compatible with tests and
        callers that need to persist the document locally.
        """

        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )

        response = await self._request(
            method="GET",
            path=f"/v1/varejista/contratos/{contract_id}/arquivo",
            headers=headers_model.model_dump(by_alias=True),
        )

        content_disposition = response.headers.get("content-disposition", "")
        filename = contract_id
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[-1].strip('"')

        return ContractFile(
            contract_id=contract_id,
            filename=filename,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            content_base64=response.text,
        )

    # Measurements endpoints

    async def list_measurements(
        self,
        consumer_unit_code: str,
        utility_agent_code: str | int,
        start_datetime: str,
        end_datetime: str,
        agent_code: str | int,
        profile_code: str | int,
        measurement_status: str | None = None,
    ) -> AsyncGenerator[Measurement]:
        """List consumption measurements for a retailer.

        Args:
            consumer_unit_code: Consumer unit code
            utility_agent_code: Utility agent code
            start_datetime: Start datetime (ISO 8601 with timezone, e.g., 2024-09-01T00:00:00-03:00)
            end_datetime: End datetime (ISO 8601 with timezone, e.g., 2024-09-30T23:59:59-03:00)
            agent_code: Agent code
            profile_code: Profile code
            measurement_status: Optional measurement status filter (CONSISTIDA, REJEITADA)

        Returns:
            AsyncGenerator of measurements

        Note:
            Ranges spanning multiple months are automatically split into same-month chunks
            (CCEE API requirement). Only dates from 08/2024 onwards are supported.
        """
        # Create headers model
        headers_model = ApiHeaders(
            agent_code=str(agent_code),
            profile_code=str(profile_code),
        )

        # Split range into same-month chunks (API requires start/end within same month)
        ranges = _split_datetime_range_by_month(start_datetime, end_datetime)

        for range_start, range_end in ranges:
            params_model = ListMeasurementsParams(
                consumer_unit_code=consumer_unit_code,
                utility_agent_code=str(utility_agent_code),
                start_datetime=range_start,
                end_datetime=range_end,
                measurement_status=measurement_status,
            )

            async def _get_page(
                params: ListMeasurementsParams,
                page_index: str | None = None,
            ) -> Response:
                if page_index is not None:
                    params.next_page_index = page_index
                else:
                    params.next_page_index = None
                return await self._request(
                    method="GET",
                    path="/v1/varejista/consumo/medicoes",
                    headers=headers_model.model_dump(by_alias=True),
                    params=params.model_dump(by_alias=True, exclude_none=True),
                )

            page_index = None
            while True:
                response = await _get_page(params_model, page_index)
                data = response.json()

                for measurement_data in data.get("medicoes", []):
                    yield Measurement.model_validate(measurement_data)

                page_index = data.get("indexProximaPagina")
                if page_index is None:
                    break

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self._http_client.aclose()

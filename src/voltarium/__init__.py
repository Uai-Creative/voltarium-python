"""Voltarium: Asynchronous Python client for CCEE API.

This package provides an asynchronous Python client for the CCEE
(Brazilian Electric Energy Commercialization Chamber) API.
"""

from voltarium.client import (
    PRODUCTION_BASE_URL,
    SANDBOX_BASE_URL,
    MigrationApiVersion,
    VoltariumClient,
)
from voltarium.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
    VoltariumError,
)
from voltarium.models import (
    ChangeRequest,
    Contract,
    CreateContractRequest,
    CreateMigrationRequest,
    CreateMigrationRequestV2,
    CreateRepresentativeChangeRequest,
    CreateReturnToCaptiveRequest,
    CreateSupplySuspensionByRetailerRequest,
    CreateSupplySuspensionByUtilityRequest,
    ListChangeRequestsParams,
    ListContractsParams,
    ListMigrationsParams,
    MigrationItem,
    MigrationListItem,
    Token,
    UpdateChangeRequestStatusRequest,
    UpdateMigrationRequest,
)
from voltarium.models.constants import ChangeRequestStatus, ChangeRequestType, MigrationStatus, Submarket

__all__ = [
    # Client
    "VoltariumClient",
    "PRODUCTION_BASE_URL",
    "SANDBOX_BASE_URL",
    "MigrationApiVersion",
    # Models
    "ChangeRequest",
    "Contract",
    "CreateContractRequest",
    "CreateMigrationRequest",
    "CreateMigrationRequestV2",
    "CreateRepresentativeChangeRequest",
    "CreateReturnToCaptiveRequest",
    "CreateSupplySuspensionByRetailerRequest",
    "CreateSupplySuspensionByUtilityRequest",
    "ListChangeRequestsParams",
    "ListContractsParams",
    "ListMigrationsParams",
    "MigrationItem",
    "MigrationListItem",
    "Token",
    "UpdateChangeRequestStatusRequest",
    "UpdateMigrationRequest",
    # Constants
    "ChangeRequestStatus",
    "ChangeRequestType",
    "MigrationStatus",
    "Submarket",
    # Exceptions
    "VoltariumError",
    "AuthenticationError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
]

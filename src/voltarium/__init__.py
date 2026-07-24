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
    Contract,
    CreateContractRequest,
    CreateMigrationRequest,
    CreateMigrationRequestV2,
    ListContractsParams,
    ListMigrationsParams,
    MigrationItem,
    MigrationListItem,
    Token,
    UpdateMigrationRequest,
)
from voltarium.models.constants import MigrationStatus, Submarket

__all__ = [
    # Client
    "VoltariumClient",
    "PRODUCTION_BASE_URL",
    "SANDBOX_BASE_URL",
    "MigrationApiVersion",
    # Models
    "Contract",
    "CreateContractRequest",
    "CreateMigrationRequest",
    "CreateMigrationRequestV2",
    "ListContractsParams",
    "ListMigrationsParams",
    "MigrationItem",
    "MigrationListItem",
    "Token",
    "UpdateMigrationRequest",
    # Constants
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

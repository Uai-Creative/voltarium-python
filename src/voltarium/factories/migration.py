"""Migration model factories for testing."""

import random
from datetime import datetime, timedelta
from typing import Any

import factory
from factory.fuzzy import FuzzyChoice
from faker import Faker

from voltarium.models.constants import Submarket
from voltarium.models.migration import (
    BaseMigration,
    CreateMigrationRequest,
    MigrationItem,
    MigrationListItem,
    UpdateMigrationRequest,
)
from voltarium.sandbox import RETAILERS, UTILITIES, generate_consumer_unit_code

fake_br = Faker("pt_BR")


class BaseMigrationFactory(factory.Factory):
    """Base factory for migration models with common fields."""

    class Meta:
        model = BaseMigration

    class Params:
        sandbox_agent_credentials = FuzzyChoice(RETAILERS)

    # Generate real agent credentials for testing
    @factory.lazy_attribute
    def retailer_agent_code(obj: Any) -> int:
        return obj.sandbox_agent_credentials.agent_code

    @factory.lazy_attribute
    def retailer_profile_code(obj: Any) -> int:
        return random.choice(obj.sandbox_agent_credentials.profiles)

    @factory.lazy_attribute
    def utility_agent_code(obj: Any) -> int:
        utility = random.choice(UTILITIES)
        return utility.agent_code

    # Required fields
    migration_id = factory.Faker("uuid4")
    consumer_unit_code = factory.LazyAttribute(
        lambda obj: generate_consumer_unit_code(f"{obj.utility_agent_code}{random.randint(1000, 9999)}")
    )
    utility_agent_consumer_unit_code = factory.Faker("numerify", text="###")
    document_type = factory.Faker("random_element", elements=("CPF", "CNPJ"))

    @factory.lazy_attribute
    def document_number(obj: Any) -> str | None:
        doc_type = getattr(obj, "document_type", None)
        if doc_type == "CPF":
            return fake_br.cpf().replace(".", "").replace("-", "")
        if doc_type == "CNPJ":
            return fake_br.cnpj().replace(".", "").replace("/", "").replace("-", "")
        return None

    request_date = factory.Faker("date_time_this_year")
    migration_status = factory.Faker("random_element", elements=("PENDENTE", "APROVADA", "REJEITADA"))
    consumer_unit_email = factory.Faker("email")
    submarket = FuzzyChoice(Submarket)

    # Optional fields
    dhc_value = factory.Faker("pyfloat", positive=True, max_value=10000)
    musd_value = factory.Faker("pyfloat", positive=True, max_value=1000)
    penalty_payment = factory.Faker("random_element", elements=("SIM", "NAO"))
    justification = factory.Faker("text", max_nb_chars=200)
    validation_date = factory.Faker("date_time_this_year")
    comment = factory.Faker("text", max_nb_chars=500)


class MigrationListItemFactory(BaseMigrationFactory):
    """Factory for MigrationListItem model."""

    class Meta:
        model = MigrationListItem

    # MigrationListItem specific fields
    supplier_agent_code = factory.Faker("pyint", min_value=1000, max_value=9999)

    @factory.lazy_attribute
    def reference_month(obj: Any) -> datetime:
        # Generate a future month (1-3 months ahead)
        future_date = datetime.now() + timedelta(days=random.randint(30, 90))
        return future_date.replace(day=1)  # First day of the month

    @factory.lazy_attribute
    def denunciation_date(obj: Any) -> datetime:
        # Generate a future date (1-2 months ahead)
        return datetime.now() + timedelta(days=random.randint(30, 60))

    cer_celebration_id = factory.Faker("uuid4")


class MigrationItemFactory(BaseMigrationFactory):
    """Factory for MigrationItem model."""

    class Meta:
        model = MigrationItem

    # MigrationItem specific fields
    @factory.lazy_attribute
    def reference_date(obj: Any) -> datetime:
        # Generate a future month (1-3 months ahead)
        future_date = datetime.now() + timedelta(days=random.randint(30, 90))
        return future_date.replace(day=1)  # First day of the month

    @factory.lazy_attribute
    def denunciation_date(obj: Any) -> datetime:
        # Generate a future date (1-2 months ahead), optional for detail context
        return datetime.now() + timedelta(days=random.randint(30, 60))

    connected_type = factory.Faker("random_element", elements=("CONECTADO", "DESCONECTADO"))
    supplier_code = factory.Faker("pyint", min_value=1000, max_value=9999)


class CreateMigrationRequestFactory(factory.Factory):
    """Factory for CreateMigrationRequest model."""

    class Meta:
        model = CreateMigrationRequest

    class Params:
        sandbox_agent_credentials = FuzzyChoice(RETAILERS)

    # Generate real agent credentials for testing
    @factory.lazy_attribute
    def retailer_agent_code(obj: Any) -> int:
        return obj.sandbox_agent_credentials.agent_code

    @factory.lazy_attribute
    def retailer_profile_code(obj: Any) -> int:
        return random.choice(obj.sandbox_agent_credentials.profiles)

    @factory.lazy_attribute
    def utility_agent_code(obj: Any) -> int:
        utility = random.choice(UTILITIES)
        return utility.agent_code

    consumer_unit_code = factory.LazyAttribute(
        lambda obj: generate_consumer_unit_code(f"{obj.utility_agent_code}{random.randint(1000, 9999)}")
    )
    document_type = FuzzyChoice(["CNPJ", "CPF"])

    @factory.lazy_attribute
    def document_number(obj: Any) -> str | None:
        if obj.document_type == "CPF":
            return None
        return fake_br.cnpj().replace(".", "").replace("/", "").replace("-", "")

    @factory.lazy_attribute
    def reference_month(obj: Any) -> str:
        # Generate a future month (1-3 months ahead) in YYYY-MM format
        future_date = datetime.now() + timedelta(days=random.randint(30, 90))
        return future_date.strftime("%Y-%m")

    @factory.lazy_attribute
    def denunciation_date(obj: Any) -> str:
        # Generate a future date (1-2 months ahead) in YYYY-MM-DD format
        future_date = datetime.now() + timedelta(days=random.randint(30, 60))
        return future_date.strftime("%Y-%m-%d")

    consumer_unit_email = factory.Faker("email")
    comment = factory.Faker("text", max_nb_chars=500)


class UpdateMigrationRequestFactory(factory.Factory):
    """Factory for UpdateMigrationRequest model."""

    class Meta:
        model = UpdateMigrationRequest

    class Params:
        sandbox_agent_credentials = FuzzyChoice(RETAILERS)

    # Generate real agent credentials for testing
    @factory.lazy_attribute
    def retailer_profile_code(obj: Any) -> int:
        return random.choice(obj.sandbox_agent_credentials.profiles)

    @factory.lazy_attribute
    def reference_month(obj: Any) -> str:
        # Generate a future month (1-3 months ahead) in YYYY-MM format
        future_date = datetime.now() + timedelta(days=random.randint(30, 90))
        return future_date.strftime("%Y-%m")

    document_type = FuzzyChoice(["CNPJ", "CPF"])

    @factory.lazy_attribute
    def document_number(obj: Any) -> str | None:
        if obj.document_type == "CPF":
            return None
        return fake_br.cnpj().replace(".", "").replace("/", "").replace("-", "")

    consumer_unit_email = factory.Faker("email")

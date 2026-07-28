"""Factories for change request (solicitacoes) models."""

import random
from datetime import datetime, timedelta
from typing import Any

import factory
from factory.fuzzy import FuzzyChoice

from voltarium.models.change_requests import (
    ChangeRequest,
    CreateRepresentativeChangeRequest,
    CreateReturnToCaptiveRequest,
    CreateSupplySuspensionByRetailerRequest,
    CreateSupplySuspensionByUtilityRequest,
    UpdateChangeRequestStatusRequest,
)
from voltarium.models.constants import ChangeRequestStatus, ChangeRequestType
from voltarium.sandbox import RETAILERS, UTILITIES, generate_consumer_unit_code


class ChangeRequestFactory(factory.Factory):
    """Factory for ChangeRequest (read model)."""

    class Meta:
        model = ChangeRequest

    class Params:
        sandbox_retailer = FuzzyChoice(RETAILERS)
        sandbox_utility = FuzzyChoice(UTILITIES)

    change_request_id = factory.Faker("uuid4")
    consumer_unit_code = factory.LazyAttribute(
        lambda obj: generate_consumer_unit_code(
            f"{obj.sandbox_utility.agent_code}{random.randint(1_000_000, 9_999_999)}"
        )
    )
    utility_agent_code = factory.LazyAttribute(lambda obj: obj.sandbox_utility.agent_code)
    request_type = FuzzyChoice(ChangeRequestType)
    request_status = FuzzyChoice(ChangeRequestStatus)
    request_date = factory.Faker("date_time_this_year")
    reference_month = factory.LazyFunction(
        lambda: (datetime.now() + timedelta(days=random.randint(30, 90))).replace(day=1)
    )
    changed_migration_id = factory.Faker("uuid4")
    advance_indicator = factory.Faker("word")
    new_retailer_agent_code = factory.LazyAttribute(lambda obj: obj.sandbox_retailer.agent_code)
    new_retailer_profile_code = factory.LazyAttribute(lambda obj: random.choice(obj.sandbox_retailer.profiles))
    current_retailer_agent_code = factory.LazyAttribute(lambda obj: obj.sandbox_retailer.agent_code)
    current_retailer_profile_code = factory.LazyAttribute(lambda obj: random.choice(obj.sandbox_retailer.profiles))
    justification = factory.Faker("text", max_nb_chars=200)
    delay_date = factory.LazyFunction(lambda: datetime.now().strftime("%Y-%m-%d"))
    notification_date = factory.LazyFunction(lambda: datetime.now().strftime("%Y-%m-%d"))
    cer_celebration_id = factory.Faker("uuid4")


class CreateReturnToCaptiveRequestFactory(factory.Factory):
    """Factory for CreateReturnToCaptiveRequest using sandbox data."""

    class Meta:
        model = CreateReturnToCaptiveRequest

    class Params:
        sandbox_utility = FuzzyChoice(UTILITIES)

    consumer_unit_code = factory.LazyAttribute(
        lambda obj: generate_consumer_unit_code(
            f"{obj.sandbox_utility.agent_code}{random.randint(1_000_000, 9_999_999)}"
        )
    )

    @factory.lazy_attribute
    def reference_month(obj: Any) -> str:
        future_date = datetime.now() + timedelta(days=random.randint(30, 90))
        return future_date.strftime("%Y-%m")

    cer_celebration_id = FuzzyChoice(["SIM", "NAO"])
    request_type = FuzzyChoice(
        [
            "ALTERACAO_RETORNO_CATIVO_RESILICAO",
            "ALTERACAO_RETORNO_CATIVO_RESOLUCAO",
            "ALTERACAO_RETORNO_CATIVO_DESLIGAMENTO",
        ]
    )


class CreateRepresentativeChangeRequestFactory(factory.Factory):
    """Factory for CreateRepresentativeChangeRequest using sandbox data."""

    class Meta:
        model = CreateRepresentativeChangeRequest

    class Params:
        sandbox_new_retailer = FuzzyChoice(RETAILERS)
        sandbox_utility = FuzzyChoice(UTILITIES)

    consumer_unit_code = factory.LazyAttribute(
        lambda obj: generate_consumer_unit_code(
            f"{obj.sandbox_utility.agent_code}{random.randint(1_000_000, 9_999_999)}"
        )
    )
    utility_agent_code = factory.LazyAttribute(lambda obj: obj.sandbox_utility.agent_code)
    new_retailer_agent_code = factory.LazyAttribute(lambda obj: obj.sandbox_new_retailer.agent_code)
    new_retailer_profile_code = factory.LazyAttribute(lambda obj: random.choice(obj.sandbox_new_retailer.profiles))

    @factory.lazy_attribute
    def reference_month(obj: Any) -> str:
        future_date = datetime.now() + timedelta(days=random.randint(30, 90))
        return future_date.strftime("%Y-%m")

    request_type = FuzzyChoice(
        [
            "ALTERACAO_ALFA_VAREJISTA_RESILICAO",
            "ALTERACAO_ALFA_VAREJISTA_RESOLUCAO",
            "ALTERACAO_ALFA_VAREJISTA_DESLIGAMENTO",
        ]
    )


class CreateSupplySuspensionByRetailerRequestFactory(factory.Factory):
    """Factory for CreateSupplySuspensionByRetailerRequest using sandbox data."""

    class Meta:
        model = CreateSupplySuspensionByRetailerRequest

    class Params:
        sandbox_utility = FuzzyChoice(UTILITIES)

    consumer_unit_code = factory.LazyAttribute(
        lambda obj: generate_consumer_unit_code(
            f"{obj.sandbox_utility.agent_code}{random.randint(1_000_000, 9_999_999)}"
        )
    )
    utility_agent_code = factory.LazyAttribute(lambda obj: obj.sandbox_utility.agent_code)
    request_type = FuzzyChoice(["SUSPENSAO_FORNECIMENTO_RESILICAO", "SUSPENSAO_FORNECIMENTO_RESOLUCAO"])
    notification_date = factory.LazyFunction(lambda: datetime.now().strftime("%Y-%m-%d"))


class CreateSupplySuspensionByUtilityRequestFactory(factory.Factory):
    """Factory for CreateSupplySuspensionByUtilityRequest using sandbox data."""

    class Meta:
        model = CreateSupplySuspensionByUtilityRequest

    class Params:
        sandbox_utility = FuzzyChoice(UTILITIES)

    consumer_unit_code = factory.LazyAttribute(
        lambda obj: generate_consumer_unit_code(
            f"{obj.sandbox_utility.agent_code}{random.randint(1_000_000, 9_999_999)}"
        )
    )
    utility_agent_code = factory.LazyAttribute(lambda obj: obj.sandbox_utility.agent_code)
    notification_date = factory.LazyFunction(lambda: datetime.now().strftime("%Y-%m-%d"))


class UpdateChangeRequestStatusRequestFactory(factory.Factory):
    """Factory for UpdateChangeRequestStatusRequest (approve/reject)."""

    class Meta:
        model = UpdateChangeRequestStatusRequest

    request_status = FuzzyChoice(["CONCLUIDA", "REPROVADA"])
    request_type = FuzzyChoice([member.value for member in ChangeRequestType])
    justification = factory.Faker("text", max_nb_chars=200)

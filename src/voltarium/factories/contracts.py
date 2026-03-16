"""Factories for contract-related models."""

import random
from typing import Any

import factory
from factory.fuzzy import FuzzyChoice
from faker import Faker

from voltarium.models import CreateContractRequest, LegalRepresentativeWrite
from voltarium.sandbox import RETAILERS, UTILITIES, generate_consumer_unit_code


class CreateContractRequestFactory(factory.Factory):
    """Factory for CreateContractRequest using sandbox data."""

    class Meta:
        model = CreateContractRequest

    class Params:
        sandbox_retailer = FuzzyChoice(RETAILERS)
        sandbox_utility = FuzzyChoice(UTILITIES)

    utility_agent_code = factory.LazyAttribute(lambda obj: obj.sandbox_utility.agent_code)
    consumer_unit_code = factory.LazyAttribute(
        lambda obj: generate_consumer_unit_code(f"{obj.sandbox_utility.agent_code}{random.randint(1000, 9999)}")
    )
    consumer_unit_address = factory.Faker("address")
    consumer_unit_name = factory.Faker("company")
    document_type = factory.Faker("random_element", elements=["CPF", "CNPJ"])
    document_number = factory.LazyAttribute(
        lambda obj: "".join(
            filter(str.isdigit, (Faker("pt_BR").cpf() if obj.document_type == "CPF" else Faker("pt_BR").cnpj()))
        )
    )

    @factory.lazy_attribute
    def legal_representatives(obj: Any) -> list[LegalRepresentativeWrite]:
        faker = Faker("pt_BR")
        doc = "".join(filter(str.isdigit, faker.cpf()))
        return [
            LegalRepresentativeWrite(
                contact_name=faker.first_name() + " " + faker.last_name(),
                contact_email=faker.email(),
                document_number=doc,
                contact_type="UNIDADE_CONSUMIDORA",
                document_type="CPF",
            )
        ]

    consumer_unit_phone = factory.LazyAttribute(
        lambda obj: f"({random.randint(11, 99):02d}) {random.randint(10000, 99999)}-{random.randint(0, 9999):04d}"
    )
    branch_consumer_unit_cnpj = factory.LazyAttribute(
        lambda obj: "".join(filter(str.isdigit, Faker("pt_BR").cnpj())) if obj.document_type == "CNPJ" else None
    )
    branch_consumer_unit_address = factory.LazyAttribute(
        lambda obj: Faker("pt_BR").address() if obj.document_type == "CNPJ" else None
    )

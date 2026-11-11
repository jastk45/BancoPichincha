"""Puertos (interfaces) que el núcleo necesita. Los adaptadores los implementan."""
from typing import Protocol

from app.domain.models import OnboardingState


class IdentityVerifierPort(Protocol):
    def verify_identity(self, document_id: str) -> dict: ...


class RiskListsPort(Protocol):
    def check_risk_lists(self, name: str, document_id: str) -> dict: ...


class DocumentationPort(Protocol):
    def prepare_documentation(self, product: str, client_data: dict) -> dict: ...


class StateRepositoryPort(Protocol):
    def save(self, state: OnboardingState) -> None: ...
    def get(self, onboarding_id: str) -> OnboardingState | None: ...

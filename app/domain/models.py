"""Entidades del dominio. Python puro: sin frameworks ni I/O."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.domain.validators import is_valid_cedula, is_valid_name


class StepStatus(str, Enum):
    OK = "ok"
    RECHAZAR = "rechazar"  # la verificación falló de forma concluyente
    ESCALAR = "escalar"    # resultado ambiguo, riesgo alto o error técnico


class Decision(str, Enum):
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    ESCALADO = "ESCALADO"  # pendiente de revisión humana


@dataclass(frozen=True)
class Prospect:
    name: str
    document_id: str
    product: str

    def __post_init__(self):  # invariantes: el dominio nunca acepta datos inválidos
        if not is_valid_name(self.name):
            raise ValueError(f"Nombre de prospecto inválido: {self.name!r}")
        if not is_valid_cedula(self.document_id):
            raise ValueError(f"Cédula inválida: {self.document_id!r}")


@dataclass
class StepResult:
    agent: str
    tool: str
    status: StepStatus
    output: dict
    reason: str | None = None
    solution: str | None = None  # acción propuesta cuando status != OK


@dataclass
class OnboardingState:
    """Estado conversacional compartido entre los pasos del onboarding."""
    prospect: Prospect
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context: dict = field(default_factory=dict)  # salida de cada agente, por nombre
    steps: list[StepResult] = field(default_factory=list)
    decision: Decision | None = None
    message: str | None = None

    @property
    def blocking_step(self) -> StepResult | None:
        return next((s for s in self.steps if s.status is not StepStatus.OK), None)

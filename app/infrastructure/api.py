"""Adaptador HTTP (FastAPI). Traduce JSON <-> dominio y delega en el orquestador."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator

from app.application.orchestrator import OnboardingOrchestrator
from app.domain.models import Decision, OnboardingState, Prospect
from app.domain.validators import is_valid_cedula, is_valid_name


class OnboardingRequest(BaseModel):
    prospect_name: str = Field(examples=["Juan Perez"])
    document_id: str = Field(examples=["1712345675"])
    product: str = Field(min_length=1, examples=["cuenta_ahorros"])

    @field_validator("prospect_name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        value = " ".join(value.split())  # normaliza espacios
        if not is_valid_name(value):
            raise ValueError("Debe incluir nombre y apellido, solo con letras.")
        return value

    @field_validator("document_id")
    @classmethod
    def _check_cedula(cls, value: str) -> str:
        if not is_valid_cedula(value):
            raise ValueError("Cédula ecuatoriana inválida: verifique los 10 dígitos, "
                             "el código de provincia y el dígito verificador.")
        return value


_APTO = {Decision.APROBADO: True, Decision.RECHAZADO: False, Decision.ESCALADO: None}


def to_response(state: OnboardingState) -> dict:
    blocking = state.blocking_step
    return {
        "onboarding_id": state.id,
        "created_at": state.created_at,
        "prospect": {"name": state.prospect.name, "document_id": state.prospect.document_id,
                     "product": state.prospect.product},
        "status": state.decision.value,
        "apto": _APTO[state.decision],
        "message": state.message,
        "required_documents": state.context.get("documentation", {}).get("required_documents", []),
        "proposed_solution": blocking.solution if blocking else None,
        "trace": [
            {"agent": s.agent, "tool": s.tool, "status": s.status.value,
             "output": s.output, "reason": s.reason}
            for s in state.steps
        ],
    }


def create_router(orchestrator: OnboardingOrchestrator, api_key: str) -> APIRouter:
    header = APIKeyHeader(name="X-API-Key", auto_error=False)

    def require_api_key(key: str | None = Security(header)) -> None:
        if not key or not secrets.compare_digest(key.encode(), api_key.encode()):
            raise HTTPException(401, "API key inválida o ausente")

    router = APIRouter(prefix="/api/v1/onboarding", dependencies=[Depends(require_api_key)])

    @router.post("/start")
    def start(req: OnboardingRequest) -> dict:
        prospect = Prospect(req.prospect_name, req.document_id, req.product)
        return to_response(orchestrator.start(prospect))

    @router.get("/{onboarding_id}")
    def get(onboarding_id: str) -> dict:
        state = orchestrator.get(onboarding_id)
        if state is None:
            raise HTTPException(404, "Onboarding no encontrado")
        return to_response(state)

    return router

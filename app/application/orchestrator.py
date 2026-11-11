"""Agente orquestador: coordina sub-agentes, gestiona el estado y decide."""
import logging

from app.application.agents import ResponseAgent, SubAgent
from app.application.ports import StateRepositoryPort
from app.domain import policies
from app.domain.models import OnboardingState, Prospect, StepStatus

log = logging.getLogger("onboarding")


class OnboardingOrchestrator:
    def __init__(self, agents: list[SubAgent], responder: ResponseAgent,
                 repository: StateRepositoryPort):
        self._agents = agents  # orden del plan: identidad -> riesgo -> documentación
        self._responder = responder
        self._repository = repository

    def start(self, prospect: Prospect) -> OnboardingState:
        state = OnboardingState(prospect=prospect)
        for agent in self._agents:
            result = agent.run(state)
            state.steps.append(result)
            state.context[agent.name] = result.output
            log.info("onboarding=%s agent=%s status=%s", state.id, agent.name, result.status.value)
            if result.status is not StepStatus.OK:
                break  # corta el flujo ante rechazo o incertidumbre
        state.decision = policies.decide(state.steps)
        state.message = self._responder.compose(state)
        self._repository.save(state)  # trazabilidad
        return state

    def get(self, onboarding_id: str) -> OnboardingState | None:
        return self._repository.get(onboarding_id)

"""Conversión OnboardingState <-> JSON, compartida por los repositorios."""
import json
from dataclasses import asdict

from app.domain.models import Decision, OnboardingState, Prospect, StepResult, StepStatus


def state_to_json(state: OnboardingState) -> str:
    return json.dumps(asdict(state), ensure_ascii=False)


def state_from_dict(d: dict) -> OnboardingState:
    return OnboardingState(
        prospect=Prospect(**d["prospect"]),
        id=d["id"],
        created_at=d["created_at"],
        context=d["context"],
        steps=[StepResult(**{**s, "status": StepStatus(s["status"])}) for s in d["steps"]],
        decision=Decision(d["decision"]) if d["decision"] else None,
        message=d["message"],
    )

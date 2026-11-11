"""Composition root: conecta adaptadores con el núcleo.

Se ejecuta como factory: uvicorn app.main:build_app --factory
"""
import logging
import os

from fastapi import FastAPI

from app.application.agents import DocumentationAgent, IdentityAgent, ResponseAgent, RiskAgent
from app.application.orchestrator import OnboardingOrchestrator
from app.infrastructure.api import create_router
from app.infrastructure.mock_tools import MockDocumentation, MockIdentityVerifier, MockRiskLists
from app.infrastructure.sqlite_repository import SQLiteStateRepository

logging.basicConfig(format="%(asctime)s %(name)s %(message)s")
logging.getLogger("onboarding").setLevel(logging.INFO)  # trazabilidad por paso


def build_app(api_key=None, db_path=None, identity=None, risk_lists=None,
              documentation=None) -> FastAPI:
    api_key = api_key or os.environ.get("ONBOARDING_API_KEY")
    if not api_key:
        raise RuntimeError("Falta ONBOARDING_API_KEY (ver .env.example).")
    db_path = db_path or os.environ.get("ONBOARDING_DB_PATH", "onboarding.db")

    orchestrator = OnboardingOrchestrator(
        agents=[
            IdentityAgent(identity or MockIdentityVerifier()),
            RiskAgent(risk_lists or MockRiskLists()),
            DocumentationAgent(documentation or MockDocumentation()),
        ],
        responder=ResponseAgent(),
        repository=SQLiteStateRepository(db_path),
    )
    app = FastAPI(title="Onboarding Digital - Agente Orquestador")
    app.include_router(create_router(orchestrator, api_key))
    return app

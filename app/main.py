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
from app.infrastructure.web import create_web_router

logging.basicConfig(format="%(asctime)s %(name)s %(message)s")
logging.getLogger("onboarding").setLevel(logging.INFO)  # trazabilidad por paso


def _build_repository(db_path: str | None):
    """Neon/Postgres si hay DATABASE_URL (Vercel la inyecta); si no, SQLite local."""
    if db_path is None:
        database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        if database_url:
            from app.infrastructure.postgres_repository import PostgresStateRepository
            return PostgresStateRepository(database_url)
        db_path = os.environ.get("ONBOARDING_DB_PATH", "onboarding.db")
    return SQLiteStateRepository(db_path)


def build_app(api_key=None, db_path=None, identity=None, risk_lists=None,
              documentation=None) -> FastAPI:
    api_key = api_key or os.environ.get("ONBOARDING_API_KEY")
    if not api_key:
        raise RuntimeError("Falta ONBOARDING_API_KEY (ver .env.example).")
    orchestrator = OnboardingOrchestrator(
        agents=[
            IdentityAgent(identity or MockIdentityVerifier()),
            RiskAgent(risk_lists or MockRiskLists()),
            DocumentationAgent(documentation or MockDocumentation()),
        ],
        responder=ResponseAgent(),
        repository=_build_repository(db_path),
    )
    app = FastAPI(title="Onboarding Digital - Agente Orquestador")
    app.include_router(create_router(orchestrator, api_key))
    app.include_router(create_web_router())
    return app

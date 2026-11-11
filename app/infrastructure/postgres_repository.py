"""Persistencia del estado en Postgres (Neon). Se activa con DATABASE_URL.

Una conexión por operación: encaja con funciones serverless (Vercel) y con el
pooler de Neon (usar la cadena de conexión "pooled").
"""
import psycopg

from app.domain.models import OnboardingState
from app.infrastructure.serialization import state_from_dict, state_to_json


class PostgresStateRepository:
    def __init__(self, url: str):
        self._url = url
        with psycopg.connect(url) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS onboarding ("
                " id TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL,"
                " decision TEXT, data JSONB NOT NULL)"
            )

    def save(self, state: OnboardingState) -> None:
        decision = state.decision.value if state.decision else None
        with psycopg.connect(self._url) as conn:
            conn.execute(
                "INSERT INTO onboarding (id, created_at, decision, data)"
                " VALUES (%s, %s, %s, %s::jsonb)"
                " ON CONFLICT (id) DO UPDATE"
                " SET decision = EXCLUDED.decision, data = EXCLUDED.data",
                (state.id, state.created_at, decision, state_to_json(state)),
            )

    def get(self, onboarding_id: str) -> OnboardingState | None:
        with psycopg.connect(self._url) as conn:
            row = conn.execute("SELECT data FROM onboarding WHERE id = %s",
                               (onboarding_id,)).fetchone()
        return state_from_dict(row[0]) if row else None  # JSONB llega como dict

"""Persistencia del estado en SQLite (stdlib). Sobrevive reinicios del servidor.

Para Postgres (p. ej. Neon) basta otro adaptador con la misma interfaz save/get.
"""
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict

from app.domain.models import Decision, OnboardingState, Prospect, StepResult, StepStatus


class SQLiteStateRepository:
    def __init__(self, path: str):
        self._path = path
        with closing(sqlite3.connect(path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS onboarding ("
                " id TEXT PRIMARY KEY, created_at TEXT NOT NULL,"
                " decision TEXT, data TEXT NOT NULL)"
            )

    def save(self, state: OnboardingState) -> None:
        data = json.dumps(asdict(state), ensure_ascii=False)
        decision = state.decision.value if state.decision else None
        with closing(sqlite3.connect(self._path)) as db, db:
            db.execute("INSERT OR REPLACE INTO onboarding VALUES (?, ?, ?, ?)",
                       (state.id, state.created_at, decision, data))

    def get(self, onboarding_id: str) -> OnboardingState | None:
        with closing(sqlite3.connect(self._path)) as db:
            row = db.execute("SELECT data FROM onboarding WHERE id = ?",
                             (onboarding_id,)).fetchone()
        return _from_dict(json.loads(row[0])) if row else None


def _from_dict(d: dict) -> OnboardingState:
    return OnboardingState(
        prospect=Prospect(**d["prospect"]),
        id=d["id"],
        created_at=d["created_at"],
        context=d["context"],
        steps=[StepResult(**{**s, "status": StepStatus(s["status"])}) for s in d["steps"]],
        decision=Decision(d["decision"]) if d["decision"] else None,
        message=d["message"],
    )

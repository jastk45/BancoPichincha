"""Persistencia del estado en SQLite (stdlib). Para desarrollo local y tests."""
import json
import sqlite3
from contextlib import closing

from app.domain.models import OnboardingState
from app.infrastructure.serialization import state_from_dict, state_to_json


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
        decision = state.decision.value if state.decision else None
        with closing(sqlite3.connect(self._path)) as db, db:
            db.execute("INSERT OR REPLACE INTO onboarding VALUES (?, ?, ?, ?)",
                       (state.id, state.created_at, decision, state_to_json(state)))

    def get(self, onboarding_id: str) -> OnboardingState | None:
        with closing(sqlite3.connect(self._path)) as db:
            row = db.execute("SELECT data FROM onboarding WHERE id = ?",
                             (onboarding_id,)).fetchone()
        return state_from_dict(json.loads(row[0])) if row else None

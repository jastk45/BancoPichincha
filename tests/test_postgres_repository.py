"""Test de integración contra Postgres/Neon. Se omite si no hay TEST_DATABASE_URL."""
import os
import unittest

from app.domain.models import Decision, OnboardingState, Prospect, StepResult, StepStatus

URL = os.environ.get("TEST_DATABASE_URL")


@unittest.skipUnless(URL, "Define TEST_DATABASE_URL para probar contra Neon")
class PostgresRepositoryTests(unittest.TestCase):
    def test_guarda_y_recupera_estado(self):
        from app.infrastructure.postgres_repository import PostgresStateRepository

        repo = PostgresStateRepository(URL)
        state = OnboardingState(prospect=Prospect("Juan Perez", "1712345675", "cuenta_ahorros"))
        state.steps.append(StepResult("identity", "verify_identity", StepStatus.OK,
                                      {"verified": True, "confidence": 0.95}))
        state.decision = Decision.APROBADO
        repo.save(state)

        loaded = repo.get(state.id)
        self.assertEqual(loaded.decision, Decision.APROBADO)
        self.assertEqual(loaded.steps[0].status, StepStatus.OK)
        self.assertIsNone(repo.get("no-existe"))


if __name__ == "__main__":
    unittest.main()

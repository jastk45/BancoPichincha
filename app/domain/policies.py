"""Políticas del banco para el onboarding. Reglas puras y testeables."""
from app.domain.models import Decision, StepResult, StepStatus

MIN_IDENTITY_CONFIDENCE = 0.8

Evaluation = tuple[StepStatus, str | None, str | None]  # (status, reason, solution)


def evaluate_identity(verified: bool, confidence: float) -> Evaluation:
    if not verified:
        return (
            StepStatus.RECHAZAR,
            "La identidad no pudo ser verificada.",
            "Solicitar al prospecto acudir a una agencia con su documento original "
            "para validación presencial.",
        )
    if confidence < MIN_IDENTITY_CONFIDENCE:
        return (
            StepStatus.ESCALAR,
            f"Confianza de identidad {confidence:.2f} menor al umbral {MIN_IDENTITY_CONFIDENCE}.",
            "Escalar a un analista y solicitar validación biométrica adicional "
            "(selfie con prueba de vida).",
        )
    return StepStatus.OK, None, None


def evaluate_risk(risk_level: str, matches: list) -> Evaluation:
    if risk_level == "high":
        return (
            StepStatus.ESCALAR,
            f"Riesgo alto en listas restrictivas: {matches}.",
            "Escalar al Oficial de Cumplimiento para revisión manual antes de vincular.",
        )
    if risk_level not in ("low", "medium"):
        return (
            StepStatus.ESCALAR,
            f"Nivel de riesgo desconocido: {risk_level!r}.",
            "Repetir la consulta de listas; si persiste, revisión manual de Cumplimiento.",
        )
    return StepStatus.OK, None, None  # medium se aprueba con debida diligencia reforzada


def evaluate_documentation(documents: list) -> Evaluation:
    if not documents:
        return (
            StepStatus.RECHAZAR,
            "El producto solicitado no está disponible en el catálogo vigente.",
            "Ofrecer al prospecto un producto del catálogo vigente del banco.",
        )
    return StepStatus.OK, None, None


def decide(steps: list[StepResult]) -> Decision:
    statuses = {s.status for s in steps}
    if StepStatus.RECHAZAR in statuses:
        return Decision.RECHAZADO
    if StepStatus.ESCALAR in statuses:
        return Decision.ESCALADO
    return Decision.APROBADO

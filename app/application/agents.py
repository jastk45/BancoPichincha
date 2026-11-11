"""Sub-agentes especializados.

Control de herramientas: cada agente recibe por inyección ÚNICAMENTE el puerto
de la herramienta que tiene permitido usar; no tiene acceso a ninguna otra.
"""
from app.application.ports import DocumentationPort, IdentityVerifierPort, RiskListsPort
from app.domain import policies
from app.domain.models import Decision, OnboardingState, StepResult, StepStatus


class SubAgent:
    name: str
    tool: str

    def run(self, state: OnboardingState) -> StepResult:
        try:
            output = self._call_tool(state)
            status, reason, solution = self._evaluate(output)
        except Exception as exc:  # un fallo técnico nunca aprueba: se escala
            output = {"error": str(exc)}
            status = StepStatus.ESCALAR
            reason = f"Error técnico al ejecutar {self.tool}: {exc}"
            solution = "Reintentar el paso; si persiste, derivar a revisión manual."
        return StepResult(self.name, self.tool, status, output, reason, solution)

    def _call_tool(self, state: OnboardingState) -> dict:
        raise NotImplementedError

    def _evaluate(self, output: dict) -> policies.Evaluation:
        raise NotImplementedError


class IdentityAgent(SubAgent):
    name, tool = "identity", "verify_identity"

    def __init__(self, verifier: IdentityVerifierPort):
        self._verifier = verifier

    def _call_tool(self, state):
        return self._verifier.verify_identity(state.prospect.document_id)

    def _evaluate(self, output):
        return policies.evaluate_identity(bool(output["verified"]), float(output["confidence"]))


class RiskAgent(SubAgent):
    name, tool = "risk", "check_risk_lists"

    def __init__(self, risk_lists: RiskListsPort):
        self._risk_lists = risk_lists

    def _call_tool(self, state):
        return self._risk_lists.check_risk_lists(state.prospect.name, state.prospect.document_id)

    def _evaluate(self, output):
        return policies.evaluate_risk(output["risk_level"], output.get("matches", []))


class DocumentationAgent(SubAgent):
    name, tool = "documentation", "prepare_documentation"

    def __init__(self, documentation: DocumentationPort):
        self._documentation = documentation

    def _call_tool(self, state):
        # Usa el estado acumulado de pasos previos para preparar la documentación.
        client_data = {
            "name": state.prospect.name,
            "document_id": state.prospect.document_id,
            "identity_confidence": state.context["identity"]["confidence"],
            "risk_level": state.context["risk"]["risk_level"],
        }
        return self._documentation.prepare_documentation(state.prospect.product, client_data)

    def _evaluate(self, output):
        return policies.evaluate_documentation(output.get("required_documents", []))


class ResponseAgent:
    """Redacta la respuesta al cliente. No usa herramientas externas.

    No revela al cliente detalles internos (p. ej. coincidencias en listas).
    """

    def compose(self, state: OnboardingState) -> str:
        first_name = state.prospect.name.split()[0]
        product = state.prospect.product.replace("_", " ")
        if state.decision is Decision.APROBADO:
            docs = ", ".join(d.replace("_", " ")
                             for d in state.context["documentation"]["required_documents"])
            return (f"Hola {first_name}, tu solicitud de {product} fue aprobada. "
                    f"Para finalizar, por favor carga: {docs}.")
        if state.decision is Decision.ESCALADO:
            return (f"Hola {first_name}, tu solicitud de {product} está en revisión. "
                    "Un asesor se comunicará contigo en un máximo de 48 horas.")
        return (f"Hola {first_name}, no pudimos completar tu solicitud de {product}. "
                f"{state.blocking_step.reason} Un asesor te indicará los siguientes pasos.")

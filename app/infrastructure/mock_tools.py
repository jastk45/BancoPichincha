"""Adaptadores simulados (mocks) de las herramientas externas.

Respuestas deterministas según el document_id para poder reproducir cada escenario.
Todas las cédulas de prueba son válidas (dígito verificador módulo 10).
"""

# document_id -> (verified, confidence)
_IDENTITY_SCENARIOS = {
    "1700000001": (False, 0.30),  # identidad no verificada
    "1711111110": (True, 0.65),   # confianza baja -> escalamiento
}

# document_id -> (risk_level, matches)
_RISK_SCENARIOS = {
    "1722222229": ("high", ["OFAC-SDN"]),  # riesgo alto -> escalamiento
    "1733333338": ("medium", ["PEP"]),     # persona expuesta políticamente
}

_PRODUCT_DOCUMENTS = {
    "cuenta_ahorros": ["copia_cedula", "planilla_servicio_basico", "contrato_cuenta_ahorros"],
    "cuenta_corriente": ["copia_cedula", "planilla_servicio_basico", "referencia_bancaria",
                         "contrato_cuenta_corriente"],
    "tarjeta_credito": ["copia_cedula", "certificado_ingresos", "solicitud_tarjeta_credito"],
}

_ENHANCED_DUE_DILIGENCE = ["declaracion_origen_fondos", "formulario_debida_diligencia_reforzada"]


class MockIdentityVerifier:
    def verify_identity(self, document_id: str) -> dict:
        verified, confidence = _IDENTITY_SCENARIOS.get(document_id, (True, 0.95))
        return {"verified": verified, "confidence": confidence}


class MockRiskLists:
    def check_risk_lists(self, name: str, document_id: str) -> dict:
        risk_level, matches = _RISK_SCENARIOS.get(document_id, ("low", []))
        return {"risk_level": risk_level, "matches": matches}


class MockDocumentation:
    def prepare_documentation(self, product: str, client_data: dict) -> dict:
        documents = list(_PRODUCT_DOCUMENTS.get(product, []))
        if documents and client_data.get("risk_level") == "medium":
            documents += _ENHANCED_DUE_DILIGENCE  # política: debida diligencia reforzada
        return {"product": product, "required_documents": documents}

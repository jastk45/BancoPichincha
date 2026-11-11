import os
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app.domain.models import Prospect
from app.main import build_app

URL = "/api/v1/onboarding/start"
API_KEY = "test-key"


def payload(document_id="1712345675", product="cuenta_ahorros", name="Juan Perez"):
    return {"prospect_name": name, "document_id": document_id, "product": product}


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db_path = os.path.join(tmp.name, "test.db")
        self.client = self.make_client()

    def make_client(self, **overrides):
        app = build_app(api_key=API_KEY, db_path=self.db_path, **overrides)
        return TestClient(app, headers={"X-API-Key": API_KEY})

    def start(self, **kw):
        res = self.client.post(URL, json=payload(**kw))
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    # --- Aprobación -------------------------------------------------------
    def test_aprobado_cliente_limpio(self):
        body = self.start()
        self.assertEqual(body["status"], "APROBADO")
        self.assertTrue(body["apto"])
        self.assertIsNone(body["proposed_solution"])
        self.assertEqual([s["tool"] for s in body["trace"]],
                         ["verify_identity", "check_risk_lists", "prepare_documentation"])
        self.assertIn("contrato_cuenta_ahorros", body["required_documents"])

    def test_aprobado_riesgo_medio_exige_debida_diligencia(self):
        body = self.start(document_id="1733333338")
        self.assertEqual(body["status"], "APROBADO")
        self.assertIn("declaracion_origen_fondos", body["required_documents"])

    # --- Rechazo ----------------------------------------------------------
    def test_rechazado_identidad_no_verificada(self):
        body = self.start(document_id="1700000001")
        self.assertEqual(body["status"], "RECHAZADO")
        self.assertFalse(body["apto"])
        self.assertIsNotNone(body["proposed_solution"])
        self.assertEqual(len(body["trace"]), 1)  # corta el flujo en el primer paso

    def test_rechazado_producto_inexistente(self):
        body = self.start(product="hipoteca")
        self.assertEqual(body["status"], "RECHAZADO")
        self.assertEqual(body["trace"][-1]["tool"], "prepare_documentation")

    # --- Escalamiento (incertidumbre) ------------------------------------
    def test_escalado_confianza_baja(self):
        body = self.start(document_id="1711111110")
        self.assertEqual(body["status"], "ESCALADO")
        self.assertIsNone(body["apto"])
        self.assertIn("biométrica", body["proposed_solution"])

    def test_escalado_riesgo_alto_no_revela_listas_al_cliente(self):
        body = self.start(document_id="1722222229")
        self.assertEqual(body["status"], "ESCALADO")
        self.assertIn("Cumplimiento", body["proposed_solution"])
        self.assertNotIn("OFAC", body["message"])

    def test_escalado_si_la_tool_falla(self):
        class BrokenRiskLists:
            def check_risk_lists(self, name, document_id):
                raise TimeoutError("servicio de listas no responde")

        body = self.make_client(risk_lists=BrokenRiskLists()).post(URL, json=payload()).json()
        self.assertEqual(body["status"], "ESCALADO")
        self.assertEqual(body["trace"][-1]["status"], "escalar")

    # --- Estado y validación ---------------------------------------------
    def test_estado_consultable_por_id(self):
        body = self.start()
        res = self.client.get(f"/api/v1/onboarding/{body['onboarding_id']}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "APROBADO")
        self.assertEqual(self.client.get("/api/v1/onboarding/no-existe").status_code, 404)

    def test_estado_persiste_tras_reinicio(self):
        onboarding_id = self.start(document_id="1711111110")["onboarding_id"]
        restarted = self.make_client()  # nueva app, misma BD
        res = restarted.get(f"/api/v1/onboarding/{onboarding_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ESCALADO")
        self.assertEqual(res.json()["trace"][0]["status"], "escalar")

    # --- Validación de datos de entrada ---------------------------------
    def test_cedulas_invalidas_retornan_422(self):
        casos = {
            "abc": "no numérica",
            "171234567": "9 dígitos",
            "1712345678": "dígito verificador incorrecto (ejemplo del enunciado)",
            "2512345678": "provincia inexistente",
            "1762345678": "tercer dígito >= 6",
        }
        for cedula, motivo in casos.items():
            with self.subTest(motivo):
                res = self.client.post(URL, json=payload(document_id=cedula))
                self.assertEqual(res.status_code, 422)
                self.assertIn("Cédula", res.text)

    def test_nombres_invalidos_retornan_422(self):
        for nombre in ["Juan", "Juan P3rez", "", "<script> x"]:
            with self.subTest(nombre):
                self.assertEqual(self.client.post(URL, json=payload(name=nombre)).status_code, 422)

    def test_nombre_con_tildes_y_espacios_extra_se_normaliza(self):
        body = self.start(name="  María   José  Núñez ")
        self.assertEqual(body["status"], "APROBADO")
        self.assertTrue(body["message"].startswith("Hola María,"))

    def test_cedula_extranjero_provincia_30_es_valida(self):
        self.assertEqual(self.start(document_id="3012345678")["status"], "APROBADO")

    def test_dominio_rechaza_prospecto_invalido_sin_pasar_por_api(self):
        with self.assertRaises(ValueError):
            Prospect("Juan Perez", "1712345678", "cuenta_ahorros")

    def test_respuesta_incluye_datos_del_prospecto(self):
        body = self.start()
        self.assertEqual(body["prospect"], {"name": "Juan Perez", "document_id": "1712345675",
                                            "product": "cuenta_ahorros"})

    def test_frontend_se_sirve_sin_api_key(self):
        res = TestClient(build_app(api_key=API_KEY, db_path=self.db_path)).get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers["content-type"])
        self.assertIn("Onboarding digital", res.text)

    # --- Seguridad --------------------------------------------------------
    def test_sin_api_key_o_incorrecta_retorna_401(self):
        app = build_app(api_key=API_KEY, db_path=self.db_path)
        self.assertEqual(TestClient(app).post(URL, json=payload()).status_code, 401)
        wrong = TestClient(app, headers={"X-API-Key": "otra"})
        self.assertEqual(wrong.post(URL, json=payload()).status_code, 401)

    def test_no_arranca_sin_api_key_configurada(self):
        with mock.patch.dict(os.environ, {"ONBOARDING_API_KEY": ""}):
            with self.assertRaises(RuntimeError):
                build_app(db_path=self.db_path)


if __name__ == "__main__":
    unittest.main()

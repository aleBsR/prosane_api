"""Tests de integraciones directas Federador/Bus MSAL (todo mockeado, sin red)."""
import io
import json
import urllib.error
from unittest.mock import patch

import jwt
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.integraciones import bus_msal as B
from apps.integraciones import federador as F
from apps.usuarios.models import Usuario


def _ok(payload):
    body = json.dumps(payload).encode()

    class R:
        status = 200

        def read(self):
            return body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return R()


def _http_error(code):
    return urllib.error.HTTPError(
        "http://x", code, "err", {}, io.BytesIO(b""))


def _parche(respuestas):
    it = iter(respuestas)

    def fake(req, timeout=None):
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r

    return patch("urllib.request.urlopen", side_effect=fake)


@override_settings(
    FEDERADOR_BASE_URL="https://federador.test/api",
    FEDERADOR_DOMINIO="DOM",
    FEDERADOR_USUARIO="u",
    FEDERADOR_CLAVE="p",
)
class FederadorTest(TestCase):
    def setUp(self):
        F._limpiar_cache()

    def test_login_cachea_token(self):
        with _parche([_ok({"token": "T1"}), _ok({"a": 1}), _ok({"a": 1})]) as m:
            F._get("/x")
            F._get("/x")
            self.assertEqual(m.call_count, 3)  # 1 login + 2 gets

    def test_headers_llevan_token_y_dominio(self):
        vistos = {}

        def fake(req, timeout=None):
            vistos["token"] = req.get_header("Token")
            vistos["dominio"] = req.get_header("Coddominio")
            vistos["auth"] = req.get_header("Authorization")
            if req.full_url.endswith("/usuarios/aplicacion/login"):
                return _ok({"token": "T"})
            return _ok({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake):
            F._get("/personas/renaper?nroDocumento=1&idSexo=1")
        self.assertEqual(vistos["token"], "T")
        self.assertEqual(vistos["dominio"], "DOM")
        self.assertIsNone(vistos["auth"])  # NO Bearer en el Federador

    def test_login_body_lleva_dominio(self):
        cuerpos = {}

        def fake(req, timeout=None):
            if req.full_url.endswith("/usuarios/aplicacion/login"):
                cuerpos["login"] = json.loads(req.data.decode())
                return _ok({"token": "T"})
            return _ok({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake):
            F._get("/x")
        self.assertEqual(
            cuerpos["login"],
            {"nombre": "u", "clave": "p", "codDominio": "DOM"})

    def test_401_reloguea_y_reintenta(self):
        with _parche([
            _ok({"token": "VIEJO"}),
            _http_error(401),
            _ok({"token": "NUEVO"}),
            _ok({"ok": True}),
        ]):
            self.assertEqual(F._get("/x"), {"ok": True})

    def test_persona_204_devuelve_none(self):
        with _parche([_ok({"token": "T"}), _http_error(204), _http_error(204)]):
            self.assertIsNone(F.renaper_persona("999", "M"))

    def test_persona_200_vacio_devuelve_none(self):
        with _parche([_ok({"token": "T"}), _ok({}), _ok({})]):
            self.assertIsNone(F.renaper_persona("999", "M"))

    def test_persona_reintenta_sexo_opuesto(self):
        with _parche([
            _ok({"token": "T"}),
            _http_error(204),
            _ok({"apellido": "Perez"}),
        ]) as m:
            data = F.renaper_persona("123", "M")
            self.assertEqual(data, {"apellido": "Perez"})
            urls = [c.args[0].full_url for c in m.call_args_list]
            self.assertIn("idSexo=1", urls[1])
            self.assertIn("idSexo=2", urls[2])

    def test_sin_sexo_prueba_1_y_2(self):
        with _parche([
            _ok({"token": "T"}),
            _http_error(404),
            _ok({"apellido": "Perez"}),
        ]):
            self.assertEqual(F.renaper_persona("123", ""), {"apellido": "Perez"})

    def test_cobertura_ok(self):
        with _parche([_ok({"token": "T"}), _ok({"obras": []})]):
            self.assertEqual(F.renaper_cobertura("123", "F"), {"obras": []})

    @override_settings(FEDERADOR_USUARIO="", FEDERADOR_CLAVE="")
    def test_sin_credenciales_error_claro(self):
        with self.assertRaises(F.FederadorNoConfigurado):
            F.renaper_persona("123", "M")


@override_settings(
    BUS_BASE_URL="https://bus.test",
    BUS_ISSUER="https://prosane.test",
    BUS_SECRET="secreto-test",
    BUS_SCOPE="Practitioner/*.read",
    BUS_NAME="n",
    BUS_IDENT="i",
    BUS_ROLE="r",
)
class BusTest(TestCase):
    def setUp(self):
        B._limpiar_cache()

    def _login_ok(self):
        return _ok({"accessToken": "AT"})

    def test_assertion_minima_sin_jti(self):
        vistos = {}

        def fake(req, timeout=None):
            if req.full_url.endswith("/bus-auth/v2/auth"):
                vistos["ct"] = req.get_header("Content-type")
                vistos["body"] = json.loads(req.data.decode())
                return self._login_ok()
            return _ok({"total": 0})

        with patch("urllib.request.urlopen", side_effect=fake):
            B.refeps_por_matricula("999")
        claims = jwt.decode(vistos["body"]["clientAssertion"],
                            options={"verify_signature": False})
        self.assertEqual(claims["iss"], "https://prosane.test")
        self.assertEqual(claims["sub"], "https://prosane.test")
        self.assertEqual(claims["aud"], "https://bus.test/bus-auth/v2/auth")
        self.assertEqual(claims["exp"] - claims["iat"], 600)
        self.assertNotIn("jti", claims)
        self.assertNotIn("organization", claims)
        self.assertEqual(claims["name"], "n")
        self.assertEqual(claims["ident"], "i")
        self.assertEqual(claims["role"], "r")
        self.assertEqual(vistos["body"]["grantType"], "client_credentials")
        self.assertIn("Practitioner", vistos["body"]["scope"])
        self.assertEqual(vistos["ct"], "application/json")

    def test_token_cacheado(self):
        with _parche([self._login_ok(), _ok({"total": 0}), _ok({"total": 0})]) as m:
            B.refeps_por_matricula("1")
            B.refeps_por_matricula("2")
            self.assertEqual(m.call_count, 3)  # 1 login + 2 búsquedas

    def test_mapea_practitioner_fhir(self):
        bundle = {
            "resourceType": "Bundle", "total": 1,
            "entry": [{
                "resource": {
                    "resourceType": "Practitioner", "id": "abc",
                    "identifier": [
                        {"system": "https://www.renaper.org.ar/dni", "value": "30123456"},
                        {"system": "https://sisa.msal.gov.ar/REFEPS", "value": "999"},
                        {"system": "https://www.anses.org.ar/cuil", "value": "20-30123456-1"},
                    ],
                    "name": [{"family": "Pérez", "given": ["Juan", "Carlos"]}],
                    "gender": "male", "active": True,
                    "qualification": [{
                        "code": {"coding": [{"code": "MED", "display": "Médico"}]},
                        "identifier": [{"value": "MN 1"}],
                        "period": {"start": "2010-01-01"},
                    }],
                },
            }],
        }
        with _parche([self._login_ok(), _ok(bundle)]):
            data = B.refeps_por_matricula("999")
        self.assertEqual(data["nombre"], "Juan")
        self.assertEqual(data["apellido"], "Pérez")
        self.assertEqual(data["dni"], "30123456")
        self.assertEqual(data["refeps"], "999")
        self.assertEqual(data["matricula"], "MN 1")
        self.assertEqual(data["profesion"], "Médico")
        self.assertEqual(len(data["matriculas"]), 1)

    def test_acepta_access_token_snake(self):
        with _parche([_ok({"access_token": "AT"}), _ok({"total": 0})]):
            self.assertIsNone(B.refeps_por_matricula("000"))

    def test_bundle_vacio_none(self):
        with _parche([self._login_ok(), _ok({"resourceType": "Bundle", "total": 0})]):
            self.assertIsNone(B.refeps_por_matricula("000"))

    def test_404_none(self):
        with _parche([self._login_ok(), _http_error(404)]):
            self.assertIsNone(B.refeps_por_matricula("000"))

    def test_query_identifier_y_gender(self):
        with _parche([self._login_ok(), _ok({"total": 0})]) as m:
            B.refeps_profesional(tipo="dni", valor="123", genero="female")
            url = m.call_args_list[1].args[0].full_url
            self.assertIn("identifier=", url)
            self.assertIn("renaper.org.ar", url)
            self.assertIn("gender=female", url)

    @override_settings(BUS_ISSUER="", BUS_SECRET="")
    def test_sin_credenciales_error_claro(self):
        with self.assertRaises(B.BusNoConfigurado):
            B.refeps_por_matricula("123")


class ValidarDniViewTest(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email="admin@test.com", password="test1234")
        self.plano = Usuario.objects.create_user(
            email="plano@test.com", password="test1234")

    def test_200_con_datos(self):
        self.client.force_authenticate(user=self.admin)
        with patch("apps.integraciones.views.renaper_persona",
                   return_value={"apellido": "Perez"}):
            res = self.client.get("/api/v1/validar-dni/?dni=30111222&sexo=M")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["apellido"], "Perez")

    def test_200_con_cobertura(self):
        self.client.force_authenticate(user=self.admin)
        with patch("apps.integraciones.views.renaper_persona",
                   return_value={"apellido": "Perez"}), \
             patch("apps.integraciones.views.renaper_cobertura",
                   return_value={"obras": []}):
            res = self.client.get("/api/v1/validar-dni/?dni=30111222&sexo=M&cobertura=1")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["cobertura"], {"obras": []})

    def test_404_si_no_existe(self):
        self.client.force_authenticate(user=self.admin)
        with patch("apps.integraciones.views.renaper_persona", return_value=None):
            res = self.client.get("/api/v1/validar-dni/?dni=999&sexo=F")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_400_sin_dni_y_pasaporte(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/validar-dni/?sexo=M")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.get("/api/v1/validar-dni/?dni=1&tipo_dni=Pasaporte")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_403_sin_accion(self):
        self.client.force_authenticate(user=self.plano)
        res = self.client.get("/api/v1/validar-dni/?dni=30111222&sexo=M")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_503_si_servicio_caido(self):
        self.client.force_authenticate(user=self.admin)
        with patch("apps.integraciones.views.renaper_persona",
                   side_effect=F.FederadorError("caído")):
            res = self.client.get("/api/v1/validar-dni/?dni=30111222&sexo=M")
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


@override_settings(REFEPS_MOCK=False)
class RefepsRealTest(TestCase):
    def setUp(self):
        B._limpiar_cache()

    def test_consultar_real_mapea(self):
        from apps.profesionales.services.services_refeps import RefepsService

        def fake(req, timeout=None):
            url = req.full_url
            if url.endswith("/bus-auth/v2/auth"):
                return _ok({"accessToken": "AT"})
            return _ok({"resourceType": "Bundle", "total": 1, "entry": [{
                "resource": {
                    "resourceType": "Practitioner",
                    "identifier": [
                        {"system": "https://sisa.msal.gov.ar/REFEPS", "value": "MO 2"}],
                    "name": [{"family": "Gómez", "given": ["Ana"]}],
                    "qualification": [{
                        "code": {"coding": [{"display": "Odontólogo"}]},
                        "identifier": [{"value": "MO 2"}],
                    }],
                },
            }]})

        with patch("urllib.request.urlopen", side_effect=fake):
            with override_settings(
                BUS_BASE_URL="https://bus.test", BUS_ISSUER="x",
                BUS_SECRET="y", BUS_SCOPE="Practitioner/*.read",
                BUS_NAME="n", BUS_IDENT="i", BUS_ROLE="r",
            ):
                data = RefepsService.consultar("MO 2")
        self.assertEqual(data["nombre"], "Ana")
        self.assertEqual(data["apellido"], "Gómez")
        self.assertEqual(data["profesion"], "Odontólogo")

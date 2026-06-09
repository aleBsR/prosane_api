"""Tests de wiring HTTP de GET /api/v1/auth/me.

Usa APIRequestFactory + force_authenticate con un user de juguete y el claim
`roles` en el token (como lo emite getCustomToken). Sin DB ni URLconf: llama la
vista directamente. Verifica el contrato y que exige autenticación.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from authentication.views import me


class MeEndpointTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def _user(self):
        return SimpleNamespace(
            id="9b2c0000-0000-0000-0000-000000000001",
            email="medico@prosane.gob.ar",
            is_staff=False,
            persona=SimpleNamespace(nombre="Ana", apellido="García"),
            is_authenticated=True,
        )

    def test_sin_auth_devuelve_401(self):
        request = self.factory.get("/api/v1/auth/me")
        response = me(request)
        self.assertEqual(response.status_code, 401)

    def test_autenticado_devuelve_200_y_contrato(self):
        request = self.factory.get("/api/v1/auth/me")
        force_authenticate(
            request,
            user=self._user(),
            token={"roles": [{"rol": "medico", "ruta": "/medico"}]},
        )
        response = me(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data.keys()), {"user", "roles", "actions", "meta"})
        self.assertEqual(response.data["roles"], [{"name": "medico", "label": "Médico/a"}])
        self.assertIn("crearApto", [a["name"] for a in response.data["actions"]])
        # cada acción respeta las 8 claves del contrato
        for a in response.data["actions"]:
            self.assertEqual(
                set(a.keys()),
                {"name", "label", "icon", "color", "type", "category", "is_sensitive", "sort_order"},
            )
        self.assertIn("version", response.data["meta"])
        self.assertIn("permissions_synced_at", response.data["meta"])

    def test_usuario_sin_roles_en_token_devuelve_actions_vacio(self):
        request = self.factory.get("/api/v1/auth/me")
        force_authenticate(request, user=self._user(), token={})
        response = me(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["actions"], [])
        self.assertEqual(response.data["roles"], [])

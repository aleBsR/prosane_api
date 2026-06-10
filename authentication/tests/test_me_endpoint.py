"""Tests de wiring HTTP de GET /api/v1/auth/me (Slice 2: lee de la DB).

Usa usuarios reales sembrados (reset_permissions_data --with-users) porque la vista
resuelve roles/acciones desde la DB. Verifica el contrato y que exige autenticación.
"""
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from authentication.models import Usuarios
from authentication.views import me


@override_settings(SEEDS_ENABLED=True)
class MeEndpointTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.factory = APIRequestFactory()

    def test_sin_auth_devuelve_401(self):
        request = self.factory.get("/api/v1/auth/me")
        response = me(request)
        self.assertEqual(response.status_code, 401)

    def test_medico_devuelve_200_y_contrato(self):
        med = Usuarios.objects.get(email="medico@prosane.test")
        request = self.factory.get("/api/v1/auth/me")
        force_authenticate(request, user=med)
        response = me(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data.keys()), {"user", "roles", "actions", "meta"})
        self.assertEqual(response.data["roles"], [{"name": "medico", "label": "Médico/a"}])
        self.assertEqual(response.data["user"]["nombre"], "Mariana")
        nombres = [a["name"] for a in response.data["actions"]]
        self.assertEqual(nombres, ["listarPacientes", "verFichaClinica", "crearApto", "firmarApto"])
        for a in response.data["actions"]:
            self.assertEqual(
                set(a.keys()),
                {"name", "label", "icon", "color", "type", "category", "is_sensitive", "sort_order"},
            )

    def test_superadmin_ve_catalogo_completo(self):
        su = Usuarios.objects.get(email="superadmin@prosane.test")
        request = self.factory.get("/api/v1/auth/me")
        force_authenticate(request, user=su)
        response = me(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["actions"]), 8)

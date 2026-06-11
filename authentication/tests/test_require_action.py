"""Tests de enforcement server-side con require_action.

Protege endpoints sensibles de patients:
- pacientes  → require_action('listarPacientes')
- antecedentes → require_action('verFichaClinica')

Usuario con la acción → pasa; sin la acción → 403; superadmin → pasa; sin auth → 401.
"""
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from authentication.models import Usuarios
from patients.views import (
    PacienteListCreateAPIView,
    AntecedentesFamiliaresAPIView,
)


@override_settings(SEEDS_ENABLED=True)
class RequireActionTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.factory = APIRequestFactory()

    def _get(self, view, email=None, **kwargs):
        request = self.factory.get("/x")
        if email:
            force_authenticate(request, user=Usuarios.objects.get(email=email))
        return view.as_view()(request, **kwargs)

    # --- pacientes (listarPacientes) ---
    def test_pacientes_tutor_sin_accion_403(self):
        resp = self._get(PacienteListCreateAPIView, "tutor@prosane.test")
        self.assertEqual(resp.status_code, 403)

    def test_pacientes_medico_con_accion_pasa(self):
        resp = self._get(PacienteListCreateAPIView, "medico@prosane.test")
        self.assertNotEqual(resp.status_code, 403)
        self.assertEqual(resp.status_code, 200)

    # --- antecedentes (verFichaClinica) ---
    def test_antecedentes_tutor_sin_accion_403(self):
        resp = self._get(AntecedentesFamiliaresAPIView, "tutor@prosane.test", patient_id=1)
        self.assertEqual(resp.status_code, 403)

    def test_antecedentes_medico_con_accion_pasa(self):
        resp = self._get(AntecedentesFamiliaresAPIView, "medico@prosane.test", patient_id=1)
        self.assertNotEqual(resp.status_code, 403)  # 404 (sin paciente), pero NO 403

    # --- superadmin y sin auth ---
    def test_superadmin_pasa(self):
        resp = self._get(PacienteListCreateAPIView, "superadmin@prosane.test")
        self.assertNotEqual(resp.status_code, 403)

    def test_sin_auth_401(self):
        resp = self._get(PacienteListCreateAPIView)  # sin email → anónimo
        self.assertEqual(resp.status_code, 401)

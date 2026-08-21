from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from apps.usuarios.models import Usuario
from apps.usuarios.tests import BaseAuthFixtureTest


class ProfesionalesApiTest(BaseAuthFixtureTest):
    """Tests de /profesionales/ — alta y gestión de cuentas de profesionales."""

    def setUp(self):
        self.client.force_authenticate(Usuario.objects.get(email="ayudante@prosane.test"))

    def _list_url(self):
        return reverse("profesionales-list-create")

    def _detail_url(self, pk):
        return reverse("profesional-detail", kwargs={"pk": pk})

    def _validar_url(self):
        return reverse("profesionales-validar-matricula")

    def _payload(self, **kwargs):
        data = {
            "email": "nuevo@medico.test",
            "password": "clave123",
            "rol": "medico",
            "matricula": "99999999",
        }
        data.update(kwargs)
        return data

    def test_list_requiere_autenticacion(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_prohibido_sin_la_accion(self):
        self.client.force_authenticate(Usuario.objects.get(email="tutor@prosane.test"))
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_solo_profesionales(self):
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        emails = [u["email"] for u in res.data]
        self.assertIn("medico@prosane.test", emails)
        self.assertIn("odontologo@prosane.test", emails)
        self.assertNotIn("escuela@prosane.test", emails)
        self.assertNotIn("ayudante@prosane.test", emails)

    def test_crear_profesional(self):
        res = self.client.post(self._list_url(), self._payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["rol"], "medico")
        self.assertEqual(res.data["matricula"], "99999999")
        usuario = Usuario.objects.get(email="nuevo@medico.test")
        self.assertTrue(usuario.roles.filter(rol="medico").exists())
        self.assertTrue(usuario.check_password("clave123"))
        self.assertEqual(usuario.profesional_set.get().matricula, "99999999")

    def test_crear_odontologo_asigna_rol(self):
        res = self.client.post(
            self._list_url(), self._payload(rol="odontologo"), format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        usuario = Usuario.objects.get(email="nuevo@medico.test")
        self.assertTrue(usuario.roles.filter(rol="odontologo").exists())
        self.assertFalse(usuario.roles.filter(rol="medico").exists())

    def test_matricula_obligatoria(self):
        payload = self._payload()
        del payload["matricula"]
        res = self.client.post(self._list_url(), payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rol_invalido(self):
        res = self.client.post(
            self._list_url(), self._payload(rol="director"), format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_duplicado(self):
        res = self.client.post(
            self._list_url(), self._payload(email="medico@prosane.test"), format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_corta(self):
        res = self.client.post(
            self._list_url(), self._payload(password="123"), format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(REFEPS_MOCK=True)
    def test_crear_autocompleta_nombre_desde_refeps(self):
        res = self.client.post(
            self._list_url(), self._payload(matricula="123456789"), format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["nombre"], "Carlos")
        self.assertEqual(res.data["apellido"], "López")

    @override_settings(REFEPS_MOCK=True)
    def test_crear_con_nombre_manual_prevalece(self):
        res = self.client.post(
            self._list_url(),
            self._payload(matricula="123456789", nombre="Juan", apellido="Pérez"),
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["nombre"], "Juan")
        self.assertEqual(res.data["apellido"], "Pérez")

    @override_settings(REFEPS_MOCK=True)
    def test_validar_matricula_ok(self):
        res = self.client.post(
            self._validar_url(), {"matricula": "541012497922"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["profesion"], "Médico")
        self.assertEqual(res.data["nombre"], "Estela Rosa")

    @override_settings(REFEPS_MOCK=True)
    def test_validar_matricula_no_encontrada(self):
        res = self.client.post(
            self._validar_url(), {"matricula": "00000000"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(REFEPS_MOCK=False)
    def test_validar_matricula_servicio_caido(self):
        res = self.client.post(
            self._validar_url(), {"matricula": "541012497922"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_validar_matricula_vacia(self):
        res = self.client.post(self._validar_url(), {"matricula": ""}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_edita_cuenta(self):
        usuario = Usuario.objects.get(email="medico@prosane.test")
        res = self.client.patch(
            self._detail_url(usuario.pk),
            {"rol": "odontologo", "email": "medico-cambiado@prosane.test"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        usuario.refresh_from_db()
        self.assertEqual(usuario.email, "medico-cambiado@prosane.test")
        self.assertTrue(usuario.roles.filter(rol="odontologo").exists())
        self.assertFalse(usuario.roles.filter(rol="medico").exists())

    def test_delete_desactiva(self):
        usuario = Usuario.objects.get(email="medico@prosane.test")
        res = self.client.delete(self._detail_url(usuario.pk))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.personas.models import Persona
from apps.usuarios.models import Action, ActionRole, Rol
from apps.usuarios.action_resolution import effective_actions
from apps.usuarios.permissions import require_action

Usuario = get_user_model()

TEST_PASSWORD = "prosane-dev-2026"


class PermissionTest(TestCase):
    """Tests del núcleo data-driven con datos mínimos creados en setUp."""

    def setUp(self):
        self.action = Action.objects.create(
            name="testAction",
            label="Test Action",
            type="crud",
            category="test",
            sort_order=1,
        )
        self.rol = Rol.objects.create(rol="test_role")
        ActionRole.objects.create(role=self.rol, action=self.action)
        self.user = Usuario.objects.create_user(
            email="test@example.com",
            password="test1234",
        )
        self.user.roles.add(self.rol)

    def test_action_tiene_8_claves(self):
        actions = effective_actions(self.user)
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            set(actions[0].keys()),
            {"name", "label", "icon", "color", "type", "category", "is_sensitive", "sort_order"},
        )

    def test_effective_actions_devuelve_acciones_del_rol(self):
        actions = effective_actions(self.user)
        self.assertEqual([a["name"] for a in actions], ["testAction"])

    def test_require_action_pasa(self):
        perm = require_action("testAction")()
        request = type("Req", (), {"user": self.user, "method": "GET"})()
        self.assertTrue(perm.has_permission(request, None))

    def test_require_action_falla_sin_rol(self):
        user_sin_rol = Usuario.objects.create_user(
            email="sin_rol@example.com",
            password="test1234",
        )
        perm = require_action("testAction")()
        request = type("Req", (), {"user": user_sin_rol, "method": "GET"})()
        self.assertFalse(perm.has_permission(request, None))

    def test_superuser_pasa_aunque_no_tenga_la_accion(self):
        admin = Usuario.objects.create_superuser(
            email="admin@example.com",
            password="test1234",
        )
        perm = require_action("noExiste")()
        request = type("Req", (), {"user": admin, "method": "GET"})()
        self.assertTrue(perm.has_permission(request, None))


class SeedPermissionsTest(TestCase):
    @override_settings(SEEDS_ENABLED=True)
    def test_seed_crea_roles_acciones_y_relaciones(self):
        from django.core.management import call_command

        call_command("seed_permissions", verbosity=0)

        self.assertEqual(Action.objects.filter(is_active=True).count(), 17)
        self.assertTrue(Rol.objects.filter(rol="ayudante").exists())
        self.assertTrue(ActionRole.objects.filter(role__rol="ayudante").exists())


class BaseAuthFixtureTest(APITestCase):
    """Base para tests que usan los usuarios de prueba del fixture.

    Carga roles + usuarios y ejecuta seed_permissions para tener acciones y
    relaciones rol→acción listas.
    """

    fixtures = ["roles", "users"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.core.management import call_command

        call_command("seed_permissions", verbosity=0)


class AuthAPITest(BaseAuthFixtureTest):
    """Tests de los endpoints JWT usando usuarios del fixture."""

    def _login(self, email, password=TEST_PASSWORD):
        url = reverse("auth-login")
        return self.client.post(url, {
            "email": email,
            "password": password,
        }, format="json")

    def test_login_success(self):
        res = self._login("medico@prosane.test")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_login_invalid(self):
        res = self._login("medico@prosane.test", "wrong")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_authenticated(self):
        user = Usuario.objects.get(email="medico@prosane.test")
        self.client.force_authenticate(user=user)
        url = reverse("auth-me")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["user"]["email"], "medico@prosane.test")
        self.assertIn("roles", res.data)
        self.assertIn("actions", res.data)

    def test_me_includes_actions(self):
        user = Usuario.objects.get(email="ayudante@prosane.test")
        self.client.force_authenticate(user=user)
        url = reverse("auth-me")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("actions", res.data)
        action_names = [a["name"] for a in res.data["actions"]]
        self.assertEqual(action_names, [
            "verEscuelas", "crearEscuela", "editarEscuela", "eliminarEscuela",
            "verOperativo", "crearOperativo", "editarOperativo",
            "confirmarOperativo", "finalizarOperativo", "cancelarOperativo",
            "gestionarProfesionalesEnOperativo", "importarNominaOperativo",
            "gestionarEstadoAlumnoEnOperativo",
        ])

    def test_me_unauthenticated(self):
        url = reverse("auth-me")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):
        user = Usuario.objects.get(email="medico@prosane.test")
        self.client.force_authenticate(user=user)
        url = reverse("auth-logout")
        res = self.client.post(url, {"refresh": "dummy"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_refresh_success(self):
        login_res = self._login("medico@prosane.test")
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)

        refresh_url = reverse("auth-refresh")
        refresh_res = self.client.post(refresh_url, {
            "refresh": login_res.data["refresh"],
        }, format="json")
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

    def test_refresh_invalid(self):
        url = reverse("auth-refresh")
        res = self.client.post(url, {"refresh": "token-invalido"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        login_res = self._login("medico@prosane.test")
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        refresh_token = login_res.data["refresh"]

        user = Usuario.objects.get(email="medico@prosane.test")
        self.client.force_authenticate(user=user)
        logout_url = reverse("auth-logout")
        logout_res = self.client.post(logout_url, {"refresh": refresh_token}, format="json")
        self.assertEqual(logout_res.status_code, status.HTTP_204_NO_CONTENT)

        refresh_url = reverse("auth-refresh")
        refresh_res = self.client.post(refresh_url, {"refresh": refresh_token}, format="json")
        self.assertEqual(refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthDataDrivenIntegrationTest(BaseAuthFixtureTest):
    """Tests de /me con los datos seedeados y usuarios del fixture."""

    def _action_names(self, user):
        self.client.force_authenticate(user=user)
        url = reverse("auth-me")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        return {a["name"] for a in res.data["actions"]}

    def test_me_ayudante_tiene_todas_las_acciones(self):
        user = Usuario.objects.get(email="ayudante@prosane.test")
        actions = self._action_names(user)
        self.assertEqual(actions, {
            "verEscuelas", "crearEscuela", "editarEscuela", "eliminarEscuela",
            "verOperativo", "crearOperativo", "editarOperativo",
            "confirmarOperativo", "finalizarOperativo", "cancelarOperativo",
            "gestionarProfesionalesEnOperativo", "importarNominaOperativo",
            "gestionarEstadoAlumnoEnOperativo",
        })

    def test_me_tutor_ve_escuelas_y_familia(self):
        user = Usuario.objects.get(email="tutor@prosane.test")
        actions = self._action_names(user)
        self.assertEqual(actions, {
            "verEscuelas", "registrarHijo", "verHijos",
            "darConsentimiento", "cargarAntecedentesFamiliares",
        })

    def test_me_medico_solo_ve_operativo(self):
        user = Usuario.objects.get(email="medico@prosane.test")
        actions = self._action_names(user)
        self.assertEqual(actions, {"verOperativo", "gestionarEstadoAlumnoEnOperativo"})

    def test_me_superuser_ve_todas_las_acciones(self):
        user = Usuario.objects.get(email="superadmin@prosane.test")
        actions = self._action_names(user)
        self.assertEqual(actions, {
            "verEscuelas", "crearEscuela", "editarEscuela", "eliminarEscuela",
            "verOperativo", "crearOperativo", "editarOperativo",
            "confirmarOperativo", "finalizarOperativo", "cancelarOperativo",
            "gestionarProfesionalesEnOperativo", "importarNominaOperativo",
            "gestionarEstadoAlumnoEnOperativo",
            "registrarHijo", "verHijos",
            "darConsentimiento", "cargarAntecedentesFamiliares",
        })


class AuthTokenAliasTest(APITestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(email="t@example.com", password="test1234")

    def test_token_alias_devuelve_access_y_refresh(self):
        res = self.client.post(
            reverse("auth-token"),
            {"email": "t@example.com", "password": "test1234"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_token_refresh_alias_devuelve_access(self):
        login = self.client.post(
            reverse("auth-token"),
            {"email": "t@example.com", "password": "test1234"},
            format="json",
        )
        res = self.client.post(
            reverse("auth-token-refresh"),
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)


class MeContractTest(APITestCase):
    def setUp(self):
        persona = Persona.objects.create(
            nombre="Ana", apellido="García", dni="22222222",
            tipo_dni="DNI", sexo="F", fecha_nacimiento="1990-01-01",
        )
        self.user = Usuario.objects.create_user(
            email="ana@example.com", password="test1234", persona=persona,
        )
        rol, _ = Rol.objects.get_or_create(rol="tutor")
        self.user.roles.add(rol)
        self.client.force_authenticate(self.user)

    def test_me_devuelve_shape_congelado(self):
        res = self.client.get(reverse("auth-me"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["user"]["nombre"], "Ana")
        self.assertEqual(res.data["user"]["apellido"], "García")
        self.assertEqual(res.data["user"]["email"], "ana@example.com")
        self.assertIn("is_staff", res.data["user"])
        self.assertIn("tutor_id", res.data["user"])
        self.assertEqual(res.data["roles"][0]["name"], "tutor")
        self.assertIn("label", res.data["roles"][0])
        self.assertIsInstance(res.data["actions"], list)
        self.assertIn("version", res.data["meta"])
        self.assertIn("permissions_synced_at", res.data["meta"])


class TutorAccionesFamiliaTest(APITestCase):
    def setUp(self):
        call_command("seed_permissions")
        self.user = Usuario.objects.create_user(email="tutor2@example.com", password="test1234")
        self.user.roles.add(Rol.objects.get(rol="tutor"))
        self.client.force_authenticate(self.user)

    def test_tutor_ve_acciones_de_familia(self):
        res = self.client.get(reverse("auth-me"))
        names = {a["name"] for a in res.data["actions"]}
        self.assertIn("registrarHijo", names)
        self.assertIn("verHijos", names)

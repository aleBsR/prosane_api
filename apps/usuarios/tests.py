from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.personas.models import Persona
from apps.usuarios.models import Action, ActionRole, Rol
from apps.usuarios.action_resolution import effective_actions, effective_menu_actions
from apps.usuarios.permissions import require_action

Usuario = get_user_model()

TEST_PASSWORD = "prosane123"


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
            {"name", "label", "icon", "color", "type", "category", "is_sensitive", "sort_order", "show_in_menu"},
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

        self.assertEqual(Action.objects.filter(is_active=True).count(), 32)
        self.assertTrue(Rol.objects.filter(rol="administrativo").exists())
        self.assertTrue(ActionRole.objects.filter(role__rol="administrativo").exists())


class MenuVisibilityTest(TestCase):
    """Editar/eliminar escuela y editar operativo no van al menú de inicio,
    pero siguen otorgando permiso (las opciones viven dentro de cada tarjeta)."""

    @override_settings(SEEDS_ENABLED=True)
    def test_crud_contextual_fuera_del_menu_con_permiso_intacto(self):
        call_command("seed_permissions", verbosity=0)
        user = Usuario.objects.create_user(
            email="administrativo-menu@test.com", password="test1234",
        )
        user.roles.add(Rol.objects.get(rol="administrativo"))

        menu = {a["name"] for a in effective_menu_actions(user)}
        permisos = {a["name"] for a in effective_actions(user)}

        for name in ("editarEscuela", "eliminarEscuela", "editarOperativo"):
            self.assertNotIn(name, menu)
            self.assertIn(name, permisos)

        # Los accesos del menú siguen ahí.
        self.assertIn("verEscuelas", menu)
        self.assertIn("verOperativo", menu)
        self.assertIn("crearEscuela", menu)
        self.assertIn("crearOperativo", menu)

    @override_settings(SEEDS_ENABLED=True)
    def test_importar_csv_solo_escuela_y_superadmin(self):
        call_command("seed_permissions", verbosity=0)
        administrativo = Usuario.objects.create_user(
            email="administrativo-csv@test.com", password="test1234",
        )
        administrativo.roles.add(Rol.objects.get(rol="administrativo"))
        escuela = Usuario.objects.create_user(
            email="escuela-csv@test.com", password="test1234",
        )
        escuela.roles.add(Rol.objects.get(rol="escuela"))

        perms_administrativo = {a["name"] for a in effective_actions(administrativo)}
        perms_escuela = {a["name"] for a in effective_actions(escuela)}
        self.assertNotIn("importarNominaOperativo", perms_administrativo)
        self.assertIn("importarNominaOperativo", perms_escuela)

    @override_settings(SEEDS_ENABLED=True)
    def test_registrar_alumno_fuera_del_menu_con_permiso_intacto(self):
        # El alta vive dentro de "Alumnos de mi escuela": el tile sobra.
        call_command("seed_permissions", verbosity=0)
        escuela = Usuario.objects.create_user(
            email="escuela-menu@test.com", password="test1234",
        )
        escuela.roles.add(Rol.objects.get(rol="escuela"))
        menu = {a["name"] for a in effective_menu_actions(escuela)}
        permisos = {a["name"] for a in effective_actions(escuela)}
        self.assertNotIn("registrarAlumnoEscuela", menu)
        self.assertIn("registrarAlumnoEscuela", permisos)
        self.assertIn("verAlumnosEscuela", menu)


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
        user = Usuario.objects.get(email="administrativo@prosane.test")
        self.client.force_authenticate(user=user)
        url = reverse("auth-me")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("actions", res.data)
        action_names = [a["name"] for a in res.data["actions"]]
        self.assertEqual(action_names, [
            "verEscuelas", "crearEscuela", "editarEscuela", "eliminarEscuela",
            "verOperativo", "crearOperativo", "editarOperativo",
            "confirmarOperativo", "finalizarOperativo", "iniciarOperativo", "cancelarOperativo",
            "gestionarProfesionalesEnOperativo",
            "verGestionUsuarios", "gestionarUsuariosEscuela", "gestionarProfesionales",
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

    def test_me_administrativo_tiene_acciones_de_escuela_operativo_y_usuarios(self):
        user = Usuario.objects.get(email="administrativo@prosane.test")
        actions = self._action_names(user)
        self.assertEqual(actions, {
            "verEscuelas", "crearEscuela", "editarEscuela", "eliminarEscuela",
            "verOperativo", "crearOperativo", "editarOperativo",
            "confirmarOperativo", "iniciarOperativo", "finalizarOperativo", "cancelarOperativo",
            "gestionarProfesionalesEnOperativo",
            "verGestionUsuarios", "gestionarUsuariosEscuela", "gestionarProfesionales",
        })

    def test_me_escuela_tiene_importar_csv(self):
        user = Usuario.objects.get(email="escuela@prosane.test")
        actions = self._action_names(user)
        self.assertIn("importarNominaOperativo", actions)

    def test_me_tutor_recibe_permisos_de_escuela_y_familia(self):
        user = Usuario.objects.get(email="tutor@prosane.test")
        actions = self._action_names(user)
        self.assertEqual(actions, {
            "verEscuelas", "registrarHijo", "verHijos", "darConsentimiento",
            "cargarAntecedentesFamiliares", "cargarAntecedentesNino",
        })

    def test_me_medico_recibe_permiso_de_evaluacion_medica(self):
        user = Usuario.objects.get(email="medico@prosane.test")
        actions = self._action_names(user)
        self.assertEqual(actions, {
            "verOperativo", "gestionarEstadoAlumnoEnOperativo", "cargarEvaluacionMedica",
        })

    def test_me_auditoria_en_categoria_propia_y_al_final(self):
        user = Usuario.objects.get(email="superadmin@prosane.test")
        self.client.force_authenticate(user=user)
        res = self.client.get(reverse("auth-me"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        actions = res.data["actions"]
        audit = [a for a in actions if a["name"] == "verAuditoria"]
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["category"], "auditoria")
        self.assertEqual(actions[-1]["name"], "verAuditoria")

    def test_me_superadmin_ve_acciones_de_administracion(self):
        user = Usuario.objects.get(email="superadmin@prosane.test")
        actions = self._action_names(user)
        self.assertEqual(actions, {
            "verEscuelas", "crearEscuela", "editarEscuela", "eliminarEscuela",
            "verOperativo", "crearOperativo", "editarOperativo",
            "confirmarOperativo", "iniciarOperativo", "finalizarOperativo", "cancelarOperativo",
            "gestionarProfesionalesEnOperativo", "importarNominaOperativo",
            "gestionarEstadoAlumnoEnOperativo", "cargarSeccionEscuela", "cargarAntecedentesNino",
            "verGestionUsuarios",
            "gestionarUsuariosEscuela", "gestionarAdministrativos", "gestionarProfesionales",
            "verAuditoria",
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


class UsuariosEscuelaApiTest(BaseAuthFixtureTest):
    """Tests de /usuarios/escuelas/ — alta y gestión de cuentas de escuela."""

    def setUp(self):
        from apps.escuelas.models import Escuela
        self.escuela = Escuela.objects.create(nombre="Escuela Test", cue="1234567")
        self.client.force_authenticate(Usuario.objects.get(email="superadmin@prosane.test"))

    def _list_url(self):
        return reverse("usuarios-escuela-list-create")

    def _detail_url(self, pk):
        return reverse("usuario-escuela-detail", kwargs={"pk": pk})

    def test_list_requiere_autenticacion(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_prohibido_sin_la_accion(self):
        self.client.force_authenticate(Usuario.objects.get(email="tutor@prosane.test"))
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_solo_usuarios_con_rol_escuela(self):
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        emails = [u["email"] for u in res.data]
        self.assertIn("escuela@prosane.test", emails)
        self.assertNotIn("medico@prosane.test", emails)

    def test_crear_usuario_escuela(self):
        res = self.client.post(self._list_url(), {
            "email": "nueva@escuela.test",
            "escuela": str(self.escuela.id),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["escuela_nombre"], "Escuela Test")
        self.assertEqual(res.data["rol"], "escuela")
        usuario = Usuario.objects.get(email="nueva@escuela.test")
        self.assertTrue(usuario.roles.filter(rol="escuela").exists())
        self.assertEqual(usuario.escuela_id, self.escuela.id)
        # Ahora la contraseña es temporal generada, no "clave123"
        self.assertTrue(usuario.must_change_password)
        self.assertIsNotNone(usuario.temporal_password_expires_at)
        self.assertFalse(usuario.check_password("clave123"))

    def test_crear_sin_password_genera_temporal(self):
        # Ahora sin password debe generar temporal y no fallar (antes era 400)
        res = self.client.post(self._list_url(), {
            "email": "nueva2@escuela.test",
            "escuela": str(self.escuela.id),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        usuario = Usuario.objects.get(email="nueva2@escuela.test")
        self.assertTrue(usuario.must_change_password)

    def test_crear_email_duplicado_falla(self):
        res = self.client.post(self._list_url(), {
            "email": "escuela@prosane.test",
            "password": "clave123",
            "escuela": str(self.escuela.id),
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_reasigna_escuela_sin_tocar_password(self):
        usuario = Usuario.objects.get(email="escuela@prosane.test")
        old_hash = usuario.password
        res = self.client.patch(self._detail_url(usuario.pk), {
            "escuela": str(self.escuela.id),
            "password": "nuevaClave99",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        usuario.refresh_from_db()
        self.assertEqual(usuario.escuela_id, self.escuela.id)
        # El admin no puede pisar la contraseña por este endpoint (solo el propio usuario vía /change-password)
        self.assertEqual(usuario.password, old_hash)
        self.assertFalse(usuario.check_password("nuevaClave99"))

    def test_delete_desactiva_la_cuenta(self):
        usuario = Usuario.objects.get(email="escuela@prosane.test")
        res = self.client.delete(self._detail_url(usuario.pk))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)

    def test_detalle_404_si_no_es_usuario_escuela(self):
        medico = Usuario.objects.get(email="medico@prosane.test")
        res = self.client.get(self._detail_url(medico.pk))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class PasswordResetTest(BaseAuthFixtureTest):
    """Tests de /auth/reset-password/ — flujo de "¿Olvidaste tu contraseña?"."""

    def _pedir_codigo(self, email):
        return self.client.post(reverse("auth-reset-password"), {"email": email}, format="json")

    def _confirmar(self, email, code, new_password):
        return self.client.post(reverse("auth-reset-password-confirm"), {
            "email": email, "code": code, "new_password": new_password,
        }, format="json")

    def test_pedir_codigo_para_email_registrado_envia_mail_con_codigo(self):
        from django.core import mail
        import re
        res = self._pedir_codigo("medico@prosane.test")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("detail", res.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("medico@prosane.test", mail.outbox[0].to)
        self.assertIsNotNone(re.search(r"\b\d{6}\b", mail.outbox[0].body))

    def test_pedir_codigo_para_email_no_registrado_no_revela_y_no_envia(self):
        from django.core import mail
        res = self._pedir_codigo("noexiste@test.com")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("detail", res.data)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmar_resetea_la_password_y_permite_login(self):
        from django.core import mail
        from apps.usuarios.models import PasswordResetCode
        self._pedir_codigo("medico@prosane.test")
        code = PasswordResetCode.objects.get(email="medico@prosane.test").code
        res = self._confirmar("medico@prosane.test", code, "nueva-clave-2026")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user = Usuario.objects.get(email="medico@prosane.test")
        self.assertTrue(user.check_password("nueva-clave-2026"))
        login = self.client.post(reverse("auth-login"), {
            "email": "medico@prosane.test", "password": "nueva-clave-2026",
        }, format="json")
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_codigo_invalido_falla(self):
        res = self._confirmar("medico@prosane.test", "000000", "nueva-clave-2026")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_codigo_expirado_falla(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.usuarios.models import PasswordResetCode
        PasswordResetCode.objects.create(
            email="medico@prosane.test", code="123456",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        res = self._confirmar("medico@prosane.test", "123456", "nueva-clave-2026")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_codigo_de_un_solo_uso(self):
        from django.core import mail
        from apps.usuarios.models import PasswordResetCode
        self._pedir_codigo("medico@prosane.test")
        code = PasswordResetCode.objects.get(email="medico@prosane.test").code
        first = self._confirmar("medico@prosane.test", code, "clave-uno-2026")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        second = self._confirmar("medico@prosane.test", code, "clave-dos-2026")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pedir_codigo_invalida_codigos_previos(self):
        from django.core import mail
        from apps.usuarios.models import PasswordResetCode
        self._pedir_codigo("medico@prosane.test")
        code1 = PasswordResetCode.objects.get(email="medico@prosane.test").code
        self._pedir_codigo("medico@prosane.test")
        self.assertEqual(len(mail.outbox), 2)
        # El código anterior quedó invalidado (used_at seteado).
        self.assertIsNotNone(PasswordResetCode.objects.get(code=code1).used_at)


class UsuariosAdministrativosApiTest(BaseAuthFixtureTest):
    """Tests de /usuarios/administrativos/ — alta de cuentas de administrativo (solo superadmin)."""

    def setUp(self):
        self.client.force_authenticate(Usuario.objects.get(email="superadmin@prosane.test"))

    def _list_url(self):
        return reverse("usuarios-administrativos-list-create")

    def _detail_url(self, pk):
        return reverse("usuario-administrativo-detail", kwargs={"pk": pk})

    def test_list_requiere_autenticacion(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_prohibido_para_administrativo(self):
        # El administrativo NO puede crear a otros administrativos (solo superadmin).
        self.client.force_authenticate(Usuario.objects.get(email="administrativo@prosane.test"))
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_solo_usuarios_con_rol_administrativo(self):
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        emails = [u["email"] for u in res.data]
        self.assertIn("administrativo@prosane.test", emails)
        self.assertNotIn("medico@prosane.test", emails)

    def test_crear_usuario_administrativo(self):
        res = self.client.post(self._list_url(), {
            "email": "nuevo@administrativo.test",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["rol"], "administrativo")
        usuario = Usuario.objects.get(email="nuevo@administrativo.test")
        self.assertTrue(usuario.roles.filter(rol="administrativo").exists())
        self.assertTrue(usuario.must_change_password)
        self.assertFalse(usuario.check_password("clave123"))

    def test_crear_sin_password_genera_temporal_administrativo(self):
        res = self.client.post(self._list_url(), {"email": "nuevo2@administrativo.test"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        usuario = Usuario.objects.get(email="nuevo2@administrativo.test")
        self.assertTrue(usuario.must_change_password)

    def test_crear_email_duplicado_falla(self):
        res = self.client.post(self._list_url(), {
            "email": "administrativo@prosane.test", "password": "clave123",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_password_ignorado_solo_cambia_estado(self):
        usuario = Usuario.objects.get(email="administrativo@prosane.test")
        old_hash = usuario.password
        res = self.client.patch(self._detail_url(usuario.pk), {
            "password": "nuevaClave99", "is_active": False,
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        usuario.refresh_from_db()
        self.assertEqual(usuario.password, old_hash)
        self.assertFalse(usuario.check_password("nuevaClave99"))
        self.assertFalse(usuario.is_active)

    def test_delete_desactiva_la_cuenta(self):
        usuario = Usuario.objects.get(email="administrativo@prosane.test")
        res = self.client.delete(self._detail_url(usuario.pk))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)

    def test_detalle_404_si_no_es_usuario_administrativo(self):
        medico = Usuario.objects.get(email="medico@prosane.test")
        res = self.client.get(self._detail_url(medico.pk))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class UsuariosSuperadminApiTest(BaseAuthFixtureTest):
    """Tests de /usuarios/superadmins/ — solo otro superadmin, con auditoría."""

    def setUp(self):
        self.client.force_authenticate(Usuario.objects.get(email="superadmin@prosane.test"))

    def _list_url(self):
        return reverse("usuarios-superadmin-list-create")

    def _detail_url(self, pk):
        return reverse("usuario-superadmin-detail", kwargs={"pk": pk})

    def _resend_url(self, pk):
        return reverse("usuario-superadmin-resend-temp", kwargs={"pk": pk})

    def _crear_otro(self, email="otro@prosane.test"):
        res = self.client.post(self._list_url(), {"email": email}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        return Usuario.objects.get(email=email)

    def test_list_requiere_autenticacion(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_prohibido_para_administrativo(self):
        self.client.force_authenticate(Usuario.objects.get(email="administrativo@prosane.test"))
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_prohibido_para_medico(self):
        self.client.force_authenticate(Usuario.objects.get(email="medico@prosane.test"))
        res = self.client.post(self._list_url(), {"email": "x@prosane.test"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_solo_usuarios_con_rol_superadmin(self):
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        emails = [u["email"] for u in res.data]
        self.assertIn("superadmin@prosane.test", emails)
        self.assertNotIn("medico@prosane.test", emails)

    def test_crear_superadmin_con_temporal_y_auditoria(self):
        from apps.usuarios.models import AuditoriaUsuario
        res = self.client.post(self._list_url(), {"email": "nuevo@prosane.test"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["rol"], "superadmin")
        usuario = Usuario.objects.get(email="nuevo@prosane.test")
        self.assertTrue(usuario.is_superuser)
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.roles.filter(rol="superadmin").exists())
        self.assertTrue(usuario.must_change_password)
        self.assertFalse(usuario.check_password("clave123"))
        log = AuditoriaUsuario.objects.filter(accion="crear", objetivo=usuario).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor.email, "superadmin@prosane.test")
        self.assertEqual(log.ip, "127.0.0.1")

    def test_crear_email_duplicado_falla(self):
        res = self.client.post(self._list_url(), {
            "email": "superadmin@prosane.test",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_temp_y_auditoria(self):
        from apps.usuarios.models import AuditoriaUsuario
        otro = self._crear_otro()
        res = self.client.post(self._resend_url(otro.pk), format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        otro.refresh_from_db()
        self.assertTrue(otro.must_change_password)
        self.assertTrue(
            AuditoriaUsuario.objects.filter(accion="resend_temp", objetivo=otro).exists()
        )

    def test_delete_desactiva_y_audita(self):
        from apps.usuarios.models import AuditoriaUsuario
        otro = self._crear_otro()
        res = self.client.delete(self._detail_url(otro.pk))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        otro.refresh_from_db()
        self.assertFalse(otro.is_active)
        self.assertTrue(
            AuditoriaUsuario.objects.filter(accion="desactivar", objetivo=otro).exists()
        )

    def test_delete_ultimo_superadmin_da_409(self):
        unico = Usuario.objects.get(email="superadmin@prosane.test")
        res = self.client.delete(self._detail_url(unico.pk))
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        unico.refresh_from_db()
        self.assertTrue(unico.is_active)

    def test_delete_propio_da_409(self):
        otro = self._crear_otro()
        self.client.force_authenticate(otro)
        res = self.client.delete(self._detail_url(otro.pk))
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        otro.refresh_from_db()
        self.assertTrue(otro.is_active)

    def test_patch_desactivar_ultimo_da_409(self):
        unico = Usuario.objects.get(email="superadmin@prosane.test")
        res = self.client.patch(self._detail_url(unico.pk), {"is_active": False}, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        unico.refresh_from_db()
        self.assertTrue(unico.is_active)

    def test_patch_reactivar_y_audita(self):
        from apps.usuarios.models import AuditoriaUsuario
        otro = self._crear_otro()
        self.client.delete(self._detail_url(otro.pk))
        res = self.client.patch(self._detail_url(otro.pk), {"is_active": True}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        otro.refresh_from_db()
        self.assertTrue(otro.is_active)
        self.assertTrue(
            AuditoriaUsuario.objects.filter(accion="reactivar", objetivo=otro).exists()
        )

    def test_detalle_404_si_no_es_superadmin(self):
        medico = Usuario.objects.get(email="medico@prosane.test")
        res = self.client.get(self._detail_url(medico.pk))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class BootstrapSuperuserTest(TestCase):
    """El primer superadmin de producción sale de createsuperuser --noinput + env."""

    def test_createsuperuser_noinput_con_env(self):
        import os
        from unittest import mock

        env = {
            "DJANGO_SUPERUSER_EMAIL": "root@prosane.test",
            "DJANGO_SUPERUSER_PASSWORD": "ClaveSegura99",
        }
        with mock.patch.dict(os.environ, env):
            call_command("createsuperuser", "--noinput", verbosity=0)
        usuario = Usuario.objects.get(email="root@prosane.test")
        self.assertTrue(usuario.is_superuser)
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.is_active)
        self.assertTrue(usuario.check_password("ClaveSegura99"))


class AccionAdministrativosRenameTest(TestCase):
    """La acción gestionarAyudantes se renombró a gestionarAdministrativos."""

    @override_settings(SEEDS_ENABLED=True)
    def test_seed_usa_nombre_nuevo(self):
        call_command("seed_permissions", verbosity=0)
        self.assertTrue(Action.objects.filter(name="gestionarAdministrativos").exists())
        self.assertFalse(Action.objects.filter(name="gestionarAyudantes").exists())

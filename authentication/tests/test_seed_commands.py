"""Tests de los commands de datos limpios reproducibles (Fase 2).

- reset_permissions_data: limpia SOLO las 4 tablas de permisos y recarga fixtures.
- reset_permissions_data --with-users: carga personas + usuarios de prueba (juguete),
  protegido por SEEDS_ENABLED (anti-prod).

Integración sobre el test DB (el test runner crea las tablas legacy + permisos).
"""
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings

from authentication.models import Action, RoleAction, Roles, Usuarios


class ResetPermissionsDataTests(TransactionTestCase):
    def test_carga_catalogo_completo(self):
        call_command("reset_permissions_data", verbosity=0)
        self.assertEqual(Action.objects.count(), 10)
        self.assertEqual(RoleAction.objects.count(), 17)
        self.assertEqual(Roles.objects.count(), 5)

    def test_medico_da_sus_6_acciones(self):
        call_command("reset_permissions_data", verbosity=0)
        medico = Roles.objects.get(rol="medico")
        nombres = set(medico.role_actions.values_list("action__name", flat=True))
        self.assertEqual(
            nombres, {"listarPacientes", "verFichaClinica", "verConsentimiento", "crearApto", "firmarApto", "verApto"}
        )

    def test_tutor_da_sus_3_acciones(self):
        call_command("reset_permissions_data", verbosity=0)
        tutor = Roles.objects.get(rol="tutor")
        nombres = set(tutor.role_actions.values_list("action__name", flat=True))
        self.assertEqual(nombres, {"verConstancias", "darConsentimiento", "verConsentimiento"})

    def test_idempotente(self):
        call_command("reset_permissions_data", verbosity=0)
        call_command("reset_permissions_data", verbosity=0)
        self.assertEqual(Action.objects.count(), 10)
        self.assertEqual(RoleAction.objects.count(), 17)


@override_settings(SEEDS_ENABLED=True)
class ResetWithUsersTests(TransactionTestCase):
    def test_carga_personas_usuarios_y_roles(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.assertEqual(
            Usuarios.objects.filter(email__endswith="@prosane.test").count(), 5
        )
        su = Usuarios.objects.get(email="superadmin@prosane.test")
        self.assertTrue(su.is_superuser)

        med = Usuarios.objects.get(email="medico@prosane.test")
        self.assertFalse(med.is_superuser)
        self.assertTrue(med.roles.filter(rol="medico").exists())
        self.assertEqual(med.persona.nombre, "Mariana")   # persona vinculada (nombre lindo)

    def test_password_del_fixture_verifica(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        med = Usuarios.objects.get(email="medico@prosane.test")
        self.assertTrue(med.check_password("prosane-dev-2026"))

    def test_idempotente(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.assertEqual(
            Usuarios.objects.filter(email__endswith="@prosane.test").count(), 5
        )


class ResetWithUsersGuardTests(TransactionTestCase):
    @override_settings(SEEDS_ENABLED=False)
    def test_with_users_falla_sin_seeds_enabled(self):
        with self.assertRaises(CommandError):
            call_command("reset_permissions_data", "--with-users", verbosity=0)

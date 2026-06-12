from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings

from authentication.models import Roles, Usuarios


@override_settings(SEEDS_ENABLED=True)
class SeedAllTests(TransactionTestCase):
    def test_orquesta_permisos_y_usuarios(self):
        call_command("seed_all", verbosity=0)
        self.assertEqual(Roles.objects.count(), 5)
        self.assertEqual(
            Usuarios.objects.filter(email__endswith="@prosane.test").count(), 5
        )


class SeedAllGuardTests(TransactionTestCase):
    @override_settings(SEEDS_ENABLED=False)
    def test_falla_sin_seeds_enabled(self):
        with self.assertRaises(CommandError):
            call_command("seed_all", verbosity=0)

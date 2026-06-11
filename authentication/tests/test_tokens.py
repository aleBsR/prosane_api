"""Tests del token de acceso con claim `roles` (login del front).

El access token debe llevar el claim `roles`. Con el app token_blacklist instalado,
get_token crea un OutstandingToken (FK al usuario), así que estos tests usan un
usuario REAL + DB (antes usaban un user de juguete, que ya no aplica).
"""
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings

from authentication.models import Usuarios
from authentication.tokens import RolesTokenObtainPairSerializer


@override_settings(SEEDS_ENABLED=True)
class RolesTokenTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.user = Usuarios.objects.get(email="medico@prosane.test")

    def test_get_token_incluye_claim_roles(self):
        token = RolesTokenObtainPairSerializer.get_token(self.user)
        self.assertEqual([r["rol"] for r in token["roles"]], ["medico"])

    def test_access_token_hereda_el_claim_roles(self):
        # el access derivado del refresh copia los claims → el refresh preserva roles
        token = RolesTokenObtainPairSerializer.get_token(self.user)
        self.assertEqual([r["rol"] for r in token.access_token["roles"]], ["medico"])

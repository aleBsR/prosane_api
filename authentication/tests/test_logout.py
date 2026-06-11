"""Tests del logout: invalida el refresh token server-side (blacklist de simplejwt)."""
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import Usuarios
from authentication.tokens import RolesTokenObtainPairSerializer
from authentication.views import logout


@override_settings(SEEDS_ENABLED=True)
class LogoutTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.factory = APIRequestFactory()
        self.user = Usuarios.objects.get(email="medico@prosane.test")

    def _refresh_str(self):
        return str(RolesTokenObtainPairSerializer.get_token(self.user))

    def _logout(self, body, user=None):
        request = self.factory.post("/api/v1/auth/logout/", body, format="json")
        if user:
            force_authenticate(request, user=user)
        return logout(request)

    def test_logout_blacklistea_el_refresh(self):
        refresh = self._refresh_str()
        resp = self._logout({"refresh": refresh}, user=self.user)
        self.assertEqual(resp.status_code, 205)
        # el refresh ya no sirve: check_blacklist debe levantar
        with self.assertRaises(TokenError):
            RefreshToken(refresh).check_blacklist()

    def test_logout_sin_refresh_devuelve_400(self):
        resp = self._logout({}, user=self.user)
        self.assertEqual(resp.status_code, 400)

    def test_logout_sin_auth_devuelve_401(self):
        resp = self._logout({"refresh": self._refresh_str()})  # sin autenticar
        self.assertEqual(resp.status_code, 401)

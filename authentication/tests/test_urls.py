"""Las rutas de sesión resuelven bajo /api/v1/auth/ (paths congelados del spec)."""
from django.test import SimpleTestCase
from django.urls import resolve

from rest_framework_simplejwt.views import TokenRefreshView

from authentication.views import me
from authentication.tokens import RolesTokenObtainPairView


class AuthUrlsTests(SimpleTestCase):
    def test_me_resuelve(self):
        self.assertEqual(resolve("/api/v1/auth/me/").func, me)

    def test_token_resuelve(self):
        match = resolve("/api/v1/auth/token/")
        self.assertEqual(match.func.view_class, RolesTokenObtainPairView)

    def test_token_refresh_resuelve(self):
        match = resolve("/api/v1/auth/token/refresh/")
        self.assertEqual(match.func.view_class, TokenRefreshView)

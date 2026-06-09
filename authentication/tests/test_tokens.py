"""Tests del token de acceso con claim `roles` (login del front).

El access token debe llevar el claim `roles` (lo consume el sistema de permisos y
/me). Y como ROTATE_REFRESH_TOKENS está activo, el claim debe estar en el refresh
para que el access regenerado en /token/refresh lo herede.

Puro (sin DB): user de juguete cuyo `.roles.all()` devuelve objetos con rol/ruta.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase

from authentication.tokens import RolesTokenObtainPairSerializer


def _user():
    return SimpleNamespace(
        id="9b2c0000-0000-0000-0000-000000000001",
        pk="9b2c0000-0000-0000-0000-000000000001",
        roles=SimpleNamespace(
            all=lambda: [SimpleNamespace(rol="medico", ruta="/medico")]
        ),
    )


class RolesTokenTests(SimpleTestCase):
    def test_get_token_incluye_claim_roles(self):
        token = RolesTokenObtainPairSerializer.get_token(_user())
        self.assertEqual(token["roles"], [{"rol": "medico", "ruta": "/medico"}])

    def test_access_token_hereda_el_claim_roles(self):
        # el access derivado del refresh copia los claims → el refresh preserva roles
        token = RolesTokenObtainPairSerializer.get_token(_user())
        access = token.access_token
        self.assertEqual(access["roles"], [{"rol": "medico", "ruta": "/medico"}])

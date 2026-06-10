"""Tests del generador de users.json (hashes Django, sin secretos en claro)."""
from django.contrib.auth.hashers import check_password
from django.test import SimpleTestCase

from authentication.management.commands.generate_users_fixture import build_users_fixture


class BuildUsersFixtureTests(SimpleTestCase):
    def test_5_usuarios_y_4_userrole(self):
        objs = build_users_fixture("toy")
        us = [o for o in objs if o["model"] == "authentication.usuarios"]
        urs = [o for o in objs if o["model"] == "authentication.userrole"]
        self.assertEqual(len(us), 5)
        self.assertEqual(len(urs), 4)  # superadmin no lleva rol

    def test_password_es_hash_django_que_verifica(self):
        objs = build_users_fixture("toy-secreta")
        u = next(o for o in objs if o["model"] == "authentication.usuarios")
        pw = u["fields"]["password"]
        self.assertTrue(pw.startswith("pbkdf2_sha256$"))   # hasher de Django, no $2y$ de bcrypt/PHP
        self.assertTrue(check_password("toy-secreta", pw))
        self.assertNotIn("toy-secreta", pw)                # nunca en texto plano

    def test_superadmin_es_superuser_sin_rol(self):
        objs = build_users_fixture("x")
        sa = next(
            o for o in objs
            if o["model"] == "authentication.usuarios"
            and o["fields"]["email"] == "superadmin@prosane.test"
        )
        self.assertTrue(sa["fields"]["is_superuser"])
        self.assertTrue(sa["fields"]["is_staff"])
        sa_links = [
            o for o in objs
            if o["model"] == "authentication.userrole" and o["fields"]["id_user"] == sa["pk"]
        ]
        self.assertEqual(sa_links, [])

    def test_cada_usuario_linkea_una_persona_integer(self):
        objs = build_users_fixture("x")
        for o in objs:
            if o["model"] == "authentication.usuarios":
                self.assertIsInstance(o["fields"]["persona"], int)

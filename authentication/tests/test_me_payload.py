"""Tests del armador puro del payload de /me (Fase 1).

Codifica el contrato CONGELADO de /api/v1/auth/me (spec §3):
top-level {user, roles, actions, meta}, `actions` con las 8 claves,
`meta` con version (hash del set) + permissions_synced_at.

Puro (sin DB ni request): SimpleTestCase con un user de juguete.
"""
from datetime import datetime, timezone
from types import SimpleNamespace

from django.test import SimpleTestCase

from authentication.actions_map import actions_for_roles, permissions_version
from authentication.me import build_me_payload

NOW = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)


def _user(persona=None):
    return SimpleNamespace(
        id="9b2c0000-0000-0000-0000-000000000001",
        email="medico@prosane.gob.ar",
        is_staff=False,
        persona=persona,
    )


class BuildMePayloadTests(SimpleTestCase):
    def test_top_level_tiene_user_roles_actions_meta(self):
        payload = build_me_payload(_user(), ["medico"], now=NOW)
        self.assertEqual(set(payload.keys()), {"user", "roles", "actions", "meta"})

    def test_actions_coinciden_con_actions_for_roles(self):
        payload = build_me_payload(_user(), ["medico"], now=NOW)
        self.assertEqual(payload["actions"], actions_for_roles(["medico"]))

    def test_meta_version_es_el_hash_del_set(self):
        payload = build_me_payload(_user(), ["medico"], now=NOW)
        self.assertEqual(
            payload["meta"]["version"],
            permissions_version(actions_for_roles(["medico"])),
        )

    def test_meta_synced_at_en_formato_z(self):
        payload = build_me_payload(_user(), ["medico"], now=NOW)
        self.assertEqual(payload["meta"]["permissions_synced_at"], "2026-06-09T12:00:00Z")

    def test_roles_mapeados_a_name_y_label(self):
        payload = build_me_payload(_user(), ["medico"], now=NOW)
        self.assertEqual(payload["roles"], [{"name": "medico", "label": "Médico/a"}])

    def test_user_con_persona(self):
        persona = SimpleNamespace(nombre="Ana", apellido="García")
        payload = build_me_payload(_user(persona), ["medico"], now=NOW)
        self.assertEqual(payload["user"]["email"], "medico@prosane.gob.ar")
        self.assertEqual(payload["user"]["nombre"], "Ana")
        self.assertEqual(payload["user"]["apellido"], "García")
        self.assertFalse(payload["user"]["is_staff"])

    def test_user_sin_persona_no_rompe(self):
        payload = build_me_payload(_user(persona=None), ["medico"], now=NOW)
        self.assertIsNone(payload["user"]["nombre"])
        self.assertIsNone(payload["user"]["apellido"])

    def test_sin_roles_actions_vacio_y_version_estable(self):
        payload = build_me_payload(_user(), [], now=NOW)
        self.assertEqual(payload["actions"], [])
        self.assertEqual(payload["roles"], [])
        self.assertEqual(payload["meta"]["version"], permissions_version([]))

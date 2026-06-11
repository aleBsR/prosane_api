"""Tests del formateador puro del payload de /me + el resolutor Fase 1 (código).

build_me_payload es un formateador puro (recibe role_names + actions ya resueltas).
resolve_actions_code es la resolución Fase 1 (mapa en código). Ambos sin DB.
"""
from datetime import datetime, timezone
from types import SimpleNamespace

from django.test import SimpleTestCase

from authentication.actions_map import (
    actions_for_roles, all_actions, permissions_version, resolve_actions_code,
)
from authentication.me import build_me_payload

NOW = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)


def _user(persona=None, is_superuser=False):
    return SimpleNamespace(
        id="9b2c0000-0000-0000-0000-000000000001",
        email="medico@prosane.gob.ar",
        is_staff=False,
        is_superuser=is_superuser,
        persona=persona,
    )


class BuildMePayloadTests(SimpleTestCase):
    def test_top_level_tiene_user_roles_actions_meta(self):
        payload = build_me_payload(_user(), ["medico"], actions_for_roles(["medico"]), now=NOW)
        self.assertEqual(set(payload.keys()), {"user", "roles", "actions", "meta"})

    def test_actions_passthrough(self):
        acts = actions_for_roles(["medico"])
        payload = build_me_payload(_user(), ["medico"], acts, now=NOW)
        self.assertEqual(payload["actions"], acts)

    def test_meta_version_es_el_hash_de_las_actions(self):
        acts = actions_for_roles(["medico"])
        payload = build_me_payload(_user(), ["medico"], acts, now=NOW)
        self.assertEqual(payload["meta"]["version"], permissions_version(acts))

    def test_meta_synced_at_en_formato_z(self):
        payload = build_me_payload(_user(), [], [], now=NOW)
        self.assertEqual(payload["meta"]["permissions_synced_at"], "2026-06-09T12:00:00Z")

    def test_roles_mapeados_a_name_y_label(self):
        payload = build_me_payload(_user(), ["medico"], [], now=NOW)
        self.assertEqual(payload["roles"], [{"name": "medico", "label": "Médico/a"}])

    def test_user_con_persona(self):
        persona = SimpleNamespace(nombre="Ana", apellido="García")
        payload = build_me_payload(_user(persona), ["medico"], [], now=NOW)
        self.assertEqual(payload["user"]["nombre"], "Ana")
        self.assertEqual(payload["user"]["apellido"], "García")

    def test_user_sin_persona_no_rompe(self):
        payload = build_me_payload(_user(persona=None), ["medico"], [], now=NOW)
        self.assertIsNone(payload["user"]["nombre"])
        self.assertIsNone(payload["user"]["apellido"])


class ResolveActionsCodeTests(SimpleTestCase):
    def test_por_rol(self):
        self.assertEqual(resolve_actions_code(_user(), ["tutor"]), actions_for_roles(["tutor"]))

    def test_superuser_recibe_catalogo_completo(self):
        acts = resolve_actions_code(_user(is_superuser=True), [])
        self.assertEqual({a["name"] for a in acts}, {a["name"] for a in all_actions()})
        self.assertEqual(len(acts), 10)

    def test_superuser_ordenado_y_8_claves(self):
        acts = resolve_actions_code(_user(is_superuser=True), [])
        self.assertEqual([a["sort_order"] for a in acts], sorted(a["sort_order"] for a in acts))
        for a in acts:
            self.assertEqual(
                set(a.keys()),
                {"name", "label", "icon", "color", "type", "category", "is_sensitive", "sort_order"},
            )

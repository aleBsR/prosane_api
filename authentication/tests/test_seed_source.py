"""Tests de las funciones puras que alimentan el seed (Fase 2).

all_actions() y role_action_pairs() derivan, desde ROLE_ACTIONS, qué filas de
`actions` y `role_actions` hay que sembrar. Puro, sin DB.
"""
from django.test import SimpleTestCase

from authentication.actions_map import (
    ROLE_ACTIONS,
    ACTION_FIELDS,
    all_actions,
    role_action_pairs,
)


class AllActionsTests(SimpleTestCase):
    def test_devuelve_acciones_unicas_por_name(self):
        names = [a["name"] for a in all_actions()]
        self.assertEqual(len(names), len(set(names)))

    def test_incluye_todas_las_acciones_del_mapa(self):
        esperadas = {a["name"] for acc in ROLE_ACTIONS.values() for a in acc}
        self.assertEqual({a["name"] for a in all_actions()}, esperadas)

    def test_cada_accion_tiene_las_8_claves(self):
        for a in all_actions():
            self.assertEqual(set(a.keys()), set(ACTION_FIELDS))

    def test_acciones_compartidas_aparecen_una_sola_vez(self):
        # crearApto está en medico y odontologo → debe aparecer una vez
        crear = [a for a in all_actions() if a["name"] == "crearApto"]
        self.assertEqual(len(crear), 1)


class RoleActionPairsTests(SimpleTestCase):
    def test_pares_rol_accion(self):
        pares = role_action_pairs()
        self.assertIn(("medico", "crearApto"), pares)
        self.assertIn(("tutor", "darConsentimiento"), pares)

    def test_no_hay_pares_duplicados(self):
        pares = role_action_pairs()
        self.assertEqual(len(pares), len(set(pares)))

    def test_toda_accion_referenciada_existe_en_all_actions(self):
        nombres = {a["name"] for a in all_actions()}
        for _rol, accion in role_action_pairs():
            self.assertIn(accion, nombres)

    def test_solo_roles_del_mapa(self):
        roles = {rol for rol, _accion in role_action_pairs()}
        self.assertEqual(roles, set(ROLE_ACTIONS.keys()))

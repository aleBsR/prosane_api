"""Tests de las funciones puras que alimentan el seed (Fase 2).

all_actions() y role_action_pairs() derivan, desde ROLE_ACTIONS, qué filas de
`actions` y `role_actions` hay que sembrar. Puro, sin DB.
"""
from django.test import SimpleTestCase

from authentication.actions_map import (
    ROLE_ACTIONS,
    ACTION_FIELDS,
    all_actions,
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

    def test_catalogo_tiene_9(self):
        self.assertEqual(len(all_actions()), 9)

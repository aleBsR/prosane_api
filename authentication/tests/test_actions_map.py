"""Tests del núcleo puro de permisos (Fase 1): mapa rol→acciones.

Estos tests codifican el CONTRATO CONGELADO del spec
(docs/superpowers/specs/2026-06-09-permisos-data-driven-design.md §3 y §8):
- cada acción tiene EXACTAMENTE las 8 claves,
- todo `name` es camelCase,
- la resolución deduplica y ordena,
- `permissions_version` es un hash determinístico e independiente del orden.

Son tests puros (sin DB): SimpleTestCase. El contenido concreto de ROLE_ACTIONS
es un detalle de Fase 1 (descartable), por eso aquí probamos INVARIANTES de
estructura, no nombres de acciones específicos.
"""
import re

from django.test import SimpleTestCase

from authentication.actions_map import (
    ROLE_ACTIONS,
    ACTION_FIELDS,
    actions_for_roles,
    permissions_version,
)

CAMEL_CASE = re.compile(r"^[a-z][a-zA-Z0-9]*$")


class ActionShapeTests(SimpleTestCase):
    def test_las_8_claves_congeladas(self):
        self.assertEqual(
            ACTION_FIELDS,
            ("name", "label", "icon", "color", "type",
             "category", "is_sensitive", "sort_order"),
        )

    def test_cada_accion_del_mapa_tiene_exactamente_las_8_claves(self):
        for rol, acciones in ROLE_ACTIONS.items():
            for a in acciones:
                self.assertEqual(
                    set(a.keys()), set(ACTION_FIELDS),
                    msg=f"acción {a.get('name')!r} del rol {rol!r} no tiene las 8 claves exactas",
                )

    def test_todos_los_names_son_camelcase(self):
        for rol, acciones in ROLE_ACTIONS.items():
            for a in acciones:
                self.assertRegex(
                    a["name"], CAMEL_CASE,
                    msg=f"name {a['name']!r} (rol {rol!r}) no es camelCase",
                )


class ActionsForRolesTests(SimpleTestCase):
    def test_rol_desconocido_devuelve_lista_vacia(self):
        self.assertEqual(actions_for_roles(["rol-que-no-existe"]), [])

    def test_sin_roles_devuelve_lista_vacia(self):
        self.assertEqual(actions_for_roles([]), [])

    def test_devuelve_acciones_con_las_8_claves(self):
        # algún rol con acciones definidas
        rol = next(r for r, acc in ROLE_ACTIONS.items() if acc)
        result = actions_for_roles([rol])
        self.assertTrue(result)
        for a in result:
            self.assertEqual(set(a.keys()), set(ACTION_FIELDS))

    def test_deduplica_por_name(self):
        rol = next(r for r, acc in ROLE_ACTIONS.items() if acc)
        # el mismo rol repetido no duplica acciones
        result = actions_for_roles([rol, rol])
        names = [a["name"] for a in result]
        self.assertEqual(len(names), len(set(names)))

    def test_union_de_varios_roles_no_duplica_names(self):
        roles = list(ROLE_ACTIONS.keys())
        names = [a["name"] for a in actions_for_roles(roles)]
        self.assertEqual(len(names), len(set(names)))

    def test_ordenado_por_sort_order_no_decreciente(self):
        roles = list(ROLE_ACTIONS.keys())
        orders = [a["sort_order"] for a in actions_for_roles(roles)]
        self.assertEqual(orders, sorted(orders))


class PermissionsVersionTests(SimpleTestCase):
    def test_determinista_mismo_set_misma_version(self):
        acciones = actions_for_roles(list(ROLE_ACTIONS.keys()))
        self.assertEqual(permissions_version(acciones), permissions_version(acciones))

    def test_independiente_del_orden(self):
        acciones = actions_for_roles(list(ROLE_ACTIONS.keys()))
        revertidas = list(reversed(acciones))
        self.assertEqual(permissions_version(acciones), permissions_version(revertidas))

    def test_sets_distintos_dan_versiones_distintas(self):
        rol = next(r for r, acc in ROLE_ACTIONS.items() if acc)
        una = actions_for_roles([rol])
        todas = actions_for_roles(list(ROLE_ACTIONS.keys()))
        if {a["name"] for a in una} != {a["name"] for a in todas}:
            self.assertNotEqual(permissions_version(una), permissions_version(todas))

    def test_lista_vacia_tiene_version_estable(self):
        self.assertEqual(permissions_version([]), permissions_version([]))

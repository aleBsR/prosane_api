"""Slice 2 — resolución de acciones desde la DB + equivalencia con Fase 1.

El test de equivalencia es el BLINDAJE del contrato: /me armado con el mapa en
código (Fase 1) y con las tablas (Fase 2) debe dar EXACTAMENTE lo mismo, byte por
byte, para los 5 usuarios de prueba.
"""
import json
from datetime import datetime, timezone

from django.core.management import call_command
from django.test import TransactionTestCase, override_settings

from authentication.actions_map import ACTION_FIELDS, resolve_actions_code
from authentication.me import build_me_payload
from authentication.models import Usuarios
from authentication.action_resolution import ActionPermissionBackend, effective_actions

NOW = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)
TEST_EMAILS = [
    "superadmin@prosane.test", "medico@prosane.test", "odontologo@prosane.test",
    "ayudante@prosane.test", "tutor@prosane.test",
]


@override_settings(SEEDS_ENABLED=True)
class EffectiveActionsDBTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)

    def test_medico_5_acciones_ordenadas(self):
        u = Usuarios.objects.get(email="medico@prosane.test")
        self.assertEqual(
            [a["name"] for a in effective_actions(u)],
            ["listarPacientes", "verFichaClinica", "crearApto", "firmarApto", "verApto"],
        )

    def test_tutor_2_acciones(self):
        u = Usuarios.objects.get(email="tutor@prosane.test")
        self.assertEqual(
            {a["name"] for a in effective_actions(u)},
            {"verConstancias", "darConsentimiento"},
        )

    def test_superadmin_catalogo_completo(self):
        u = Usuarios.objects.get(email="superadmin@prosane.test")
        self.assertEqual(len(effective_actions(u)), 9)

    def test_cada_accion_tiene_las_8_claves(self):
        u = Usuarios.objects.get(email="medico@prosane.test")
        for a in effective_actions(u):
            self.assertEqual(set(a.keys()), set(ACTION_FIELDS))


@override_settings(SEEDS_ENABLED=True)
class Fase1VsFase2EquivalenceTests(TransactionTestCase):
    """BLINDAJE: misma respuesta /me con el mapa (Fase 1) y con las tablas (Fase 2)."""

    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)

    def test_me_identico_byte_por_byte(self):
        for email in TEST_EMAILS:
            u = Usuarios.objects.get(email=email)
            role_names = list(u.roles.values_list("rol", flat=True))

            payload_fase1 = build_me_payload(
                u, role_names, resolve_actions_code(u, role_names), now=NOW
            )
            payload_fase2 = build_me_payload(
                u, role_names, effective_actions(u), now=NOW
            )
            self.assertEqual(
                json.dumps(payload_fase1, ensure_ascii=False),
                json.dumps(payload_fase2, ensure_ascii=False),
                msg=f"/me difiere entre mapa y DB para {email}",
            )


@override_settings(SEEDS_ENABLED=True)
class ActionPermissionBackendTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)

    def test_has_perm_por_accion(self):
        backend = ActionPermissionBackend()
        med = Usuarios.objects.get(email="medico@prosane.test")
        self.assertTrue(backend.has_perm(med, "firmarApto"))
        self.assertFalse(backend.has_perm(med, "darConsentimiento"))

    def test_get_all_permissions_es_el_set_de_names(self):
        backend = ActionPermissionBackend()
        tutor = Usuarios.objects.get(email="tutor@prosane.test")
        self.assertEqual(
            backend.get_all_permissions(tutor), {"verConstancias", "darConsentimiento"}
        )

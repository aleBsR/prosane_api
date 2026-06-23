"""Seed de permisos data-driven.

Crea roles base, carga acciones desde fixture (idempotente) y arma las relaciones
rol→acción.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.usuarios.models import Action, ActionRole, Rol
from apps.usuarios.management.commands._fixture_uuids import role_uuid


# Mapeo rol → nombres de acción.
# Este diccionario reemplaza al fixture de role_actions y evita depender de UUIDs.
ROLE_ACTIONS = {
    "ayudante": [
        "verEscuelas", "crearEscuela", "editarEscuela", "eliminarEscuela",
        "verOperativo", "crearOperativo", "editarOperativo",
        "confirmarOperativo", "iniciarOperativo", "finalizarOperativo", "cancelarOperativo",
        "gestionarProfesionalesEnOperativo", "importarNominaOperativo",
        "gestionarEstadoAlumnoEnOperativo", "cargarSeccionEscuela",
    ],
    "medico": [
        "verOperativo", "gestionarEstadoAlumnoEnOperativo", "cargarEvaluacionMedica",
    ],
    "odontologo": [
        "verOperativo", "gestionarEstadoAlumnoEnOperativo", "cargarEvaluacionOdontologica",
    ],
    "tutor": [
        "verEscuelas", "registrarHijo", "verHijos",
        "darConsentimiento", "cargarAntecedentesFamiliares", "cargarAntecedentesNino",
    ],
}


def _load_actions():
    """Lee apps/usuarios/fixtures/actions.json y crea/actualiza acciones."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "actions.json"
    with open(fixture_path, encoding="utf-8") as f:
        actions = json.load(f)

    created_count = 0
    for item in actions:
        fields = item["fields"]
        _, created = Action.objects.get_or_create(
            name=fields["name"],
            defaults={
                "label": fields["label"],
                "icon": fields.get("icon"),
                "color": fields.get("color"),
                "type": fields["type"],
                "category": fields.get("category"),
                "is_sensitive": fields.get("is_sensitive", False),
                "sort_order": fields.get("sort_order", 0),
                "is_active": fields.get("is_active", True),
                "created_at": fields.get("created_at"),
                "updated_at": fields.get("updated_at"),
            },
        )
        if created:
            created_count += 1
    return created_count


class Command(BaseCommand):
    help = "Carga roles, acciones y relaciones rol→acción (data-driven)."

    def handle(self, *args, **options):
        # 1) Roles base con UUIDs determinísticos (para que users.json pueda referenciarlos)
        for rol_name in ROLE_ACTIONS.keys():
            Rol.objects.get_or_create(
                id=role_uuid(rol_name),
                defaults={"rol": rol_name},
            )
        self.stdout.write(f"roles base: {', '.join(ROLE_ACTIONS.keys())}")

        # 2) Acciones desde fixture (idempotente)
        acciones_creadas = _load_actions()
        acciones_cargadas = Action.objects.filter(is_active=True).count()
        self.stdout.write(f"acciones cargadas: {acciones_cargadas} (nuevas: {acciones_creadas})")

        # 3) Relaciones rol→acción
        creadas = 0
        for rol_name, action_names in ROLE_ACTIONS.items():
            rol = Rol.objects.get(rol=rol_name)
            for action_name in action_names:
                action = Action.objects.get(name=action_name)
                _, created = ActionRole.objects.get_or_create(role=rol, action=action)
                if created:
                    creadas += 1

        self.stdout.write(f"relaciones rol→acción creadas: {creadas}")
        self.stdout.write(self.style.SUCCESS("Seed de permisos OK"))

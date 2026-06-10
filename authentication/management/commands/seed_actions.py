"""Seed idempotente de acciones y role_actions (Fase 2).

Vuelca a las tablas `actions` y `role_actions` lo definido en
authentication.actions_map.ROLE_ACTIONS. Re-ejecutable: actualiza metadata de
acciones existentes y no duplica vínculos rol→acción.

Uso:
    python manage.py seed_actions
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from authentication.actions_map import all_actions, role_action_pairs
from authentication.models import Action, RoleAction, Roles


class Command(BaseCommand):
    help = "Siembra (idempotente) las acciones y los vínculos rol→acción."

    @transaction.atomic
    def handle(self, *args, **options):
        creadas = actualizadas = 0
        for a in all_actions():
            _, created = Action.objects.update_or_create(
                name=a["name"],
                defaults={
                    "label": a["label"],
                    "icon": a["icon"],
                    "color": a["color"],
                    "type": a["type"],
                    "category": a["category"],
                    "is_sensitive": a["is_sensitive"],
                    "sort_order": a["sort_order"],
                    "is_active": True,
                },
            )
            creadas += int(created)
            actualizadas += int(not created)
        self.stdout.write(f"actions: {creadas} creadas, {actualizadas} actualizadas")

        vinculos = 0
        faltantes = set()
        for rol_name, action_name in role_action_pairs():
            role = Roles.objects.filter(rol=rol_name).first()
            if role is None:
                faltantes.add(rol_name)
                continue
            action = Action.objects.get(name=action_name)
            _, created = RoleAction.objects.get_or_create(role=role, action=action)
            vinculos += int(created)
        self.stdout.write(f"role_actions: {vinculos} nuevos vínculos")

        if faltantes:
            self.stdout.write(
                self.style.WARNING(
                    f"roles inexistentes en la DB (saltados): {sorted(faltantes)}"
                )
            )
        self.stdout.write(self.style.SUCCESS("seed_actions OK"))

"""Reset de datos reproducibles (estilo migrate:fresh --seed, acotado).

Limpia SOLO las 4 tablas de permisos (NUNCA las legacy con datos) y recarga los
fixtures en orden FK-safe. Con --with-users carga también personas + usuarios de
prueba (JUGUETE), protegido por SEEDS_ENABLED (no corre en prod).

Uso:
    python manage.py reset_permissions_data
    python manage.py reset_permissions_data --with-users   # solo dev (SEEDS_ENABLED)
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from authentication.models import Action, ActionLog, RoleAction, UserActionOverride

# Permisos (siempre). Orden FK-safe: roles → actions → role_actions
PERMISSION_FIXTURES = ["roles", "actions", "role_actions"]
# Usuarios de prueba (solo --with-users). people ANTES de users (el user referencia
# a la persona, tiene que existir primero).
USER_FIXTURES = ["people", "users"]


class Command(BaseCommand):
    help = "Limpia SOLO las tablas de permisos y recarga los fixtures (reproducible)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-users", action="store_true",
            help="Carga personas + usuarios de prueba (JUGUETE, solo dev/SEEDS_ENABLED).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Salvaguarda anti-prod PRIMERO: si piden usuarios y no es entorno de seeds,
        # abortamos antes de tocar nada.
        if options["with_users"] and not getattr(settings, "SEEDS_ENABLED", False):
            raise CommandError(
                "SEEDS_ENABLED no está activo: --with-users es SOLO para desarrollo local."
            )

        # 1) Hard-delete SOLO las 4 de permisos, en orden FK-safe (hijas → padre).
        #    hard_delete porque BaseModel hace soft-delete por defecto.
        ActionLog.all_objects.all().hard_delete()
        UserActionOverride.all_objects.all().hard_delete()
        RoleAction.all_objects.all().hard_delete()
        Action.all_objects.all().hard_delete()
        self.stdout.write("permisos limpiados (action_logs, user_action_overrides, role_actions, actions)")

        # 2) Permisos (siempre).
        for fixture in PERMISSION_FIXTURES:
            call_command("loaddata", fixture, verbosity=0)
        self.stdout.write(f"fixtures de permisos: {', '.join(PERMISSION_FIXTURES)}")

        # 3) Usuarios de prueba (opcional, con salvaguarda anti-prod).
        if options["with_users"]:
            if not getattr(settings, "SEEDS_ENABLED", False):
                raise CommandError(
                    "SEEDS_ENABLED no está activo: --with-users es SOLO para desarrollo local."
                )
            for fixture in USER_FIXTURES:
                call_command("loaddata", fixture, verbosity=0)
            self.stdout.write(f"usuarios de prueba (juguete): {', '.join(USER_FIXTURES)}")

        self.stdout.write(self.style.SUCCESS("reset_permissions_data OK"))

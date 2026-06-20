"""Orquestador de seeds de desarrollo.

Carga roles, usuarios de prueba, permisos y acciones.
Solo para desarrollo local (SEEDS_ENABLED).
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Carga datos base de desarrollo (roles, usuarios, permisos, acciones)."

    def handle(self, *args, **options):
        if not getattr(settings, "SEEDS_ENABLED", False):
            raise CommandError(
                "SEEDS_ENABLED no está activo: seed_all es SOLO para desarrollo local."
            )

        self.stdout.write("Iniciando seed_all...")

        # 1) Roles base (UUIDs determinísticos para que users.json los referencie)
        call_command("loaddata", "roles", verbosity=0)
        self.stdout.write("roles base cargados")

        # 2) Usuarios de prueba (incluye RoleUsuario con roles asignados)
        call_command("loaddata", "users", verbosity=0)
        self.stdout.write("usuarios de prueba cargados: 5")

        # 3) Permisos y acciones
        call_command("seed_permissions", verbosity=1)

        self.stdout.write(self.style.SUCCESS("seed_all completado"))

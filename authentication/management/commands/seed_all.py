"""Orquestador de seeds de desarrollo.

Punto de entrada único para sembrar todos los datos de dev. Cada app agrega
su paso en SEED_STEPS cuando construye su feature.

Uso:
    python manage.py seed_all

Requiere SEEDS_ENABLED=True en settings (salvaguarda anti-prod).
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Orquestador de seeds de desarrollo (corre todos los seeders por-app)."

    # Pasos del seed, en orden. Cada app suma el suyo acá a futuro:
    #   (etiqueta, nombre_command, [args])
    SEED_STEPS = [
        ("permisos + usuarios de prueba", "reset_permissions_data", ["--with-users"]),
    ]

    def handle(self, *args, **opts):
        if not getattr(settings, "SEEDS_ENABLED", False):
            raise CommandError(
                "seed_all está deshabilitado: SEEDS_ENABLED=False (salvaguarda anti-prod)."
            )
        for label, command, cmd_args in self.SEED_STEPS:
            self.stdout.write(f"→ {label} ({command})")
            call_command(command, *cmd_args, verbosity=opts.get("verbosity", 1))
        self.stdout.write(self.style.SUCCESS(f"seed_all OK ({len(self.SEED_STEPS)} pasos)."))

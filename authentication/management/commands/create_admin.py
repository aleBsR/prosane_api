"""Crea un superusuario con su Persona vinculada.

Uso (no interactivo, para scripts/CI):
    python manage.py create_admin \\
        --email admin@prosane.ar --password s3cr3t \\
        --nombre Juan --apellido Pérez --dni 20123456 \\
        --sexo M --fecha-nacimiento 1980-05-15

Uso interactivo (sin flags):
    python manage.py create_admin   # pide los datos por prompt
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from authentication.models import Usuarios
from core.models import Personas


class Command(BaseCommand):
    help = "Crea un superusuario con su Persona vinculada."

    def add_arguments(self, parser):
        for field in ["email", "password", "nombre", "apellido", "dni", "sexo", "fecha-nacimiento"]:
            parser.add_argument(f"--{field}", default=None)
        parser.add_argument("--tipo-dni", default="DNI")

    def handle(self, *args, **options):
        # En modo no-interactivo todos los campos se pasan por flag.
        # En modo interactivo se piden por prompt los que falten.
        def get(key, prompt, default=None):
            val = options.get(key)
            if val:
                return val
            if default is not None:
                return input(prompt) or default
            return input(prompt)

        email = get("email", "Email: ")
        password = get("password", "Password: ")
        nombre = get("nombre", "Nombre: ")
        apellido = get("apellido", "Apellido: ")
        dni = get("dni", "DNI: ")
        tipo_dni = options.get("tipo_dni") or "DNI"
        sexo = get("sexo", "Sexo (M/F/X): ")
        # argparse convierte --fecha-nacimiento a fecha_nacimiento
        fecha_nacimiento = get("fecha_nacimiento", "Fecha de nacimiento (YYYY-MM-DD): ")

        with transaction.atomic():
            persona = Personas.objects.create(
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                tipo_dni=tipo_dni,
                sexo=sexo,
                fecha_nacimiento=fecha_nacimiento,
            )
            user = Usuarios.objects.create_superuser(email=email, password=password)
            user.persona = persona
            user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Superusuario {email} creado con persona {nombre} {apellido}."
            )
        )

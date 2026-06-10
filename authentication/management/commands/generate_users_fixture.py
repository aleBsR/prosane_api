"""Genera authentication/fixtures/users.json con hashes de Django (PBKDF2).

Los usuarios de prueba son de JUGUETE (solo dev local). El hash se calcula con
make_password() — el hasher configurado del proyecto (pbkdf2_sha256) — para que el
login de Django los verifique. La contraseña sale de --password o de la env var
SEED_USER_PASSWORD; NUNCA se escribe en texto plano.

Uso:
    SEED_USER_PASSWORD=... python manage.py generate_users_fixture
    python manage.py generate_users_fixture --password ...
"""
import json
import os

from django.apps import apps
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

# Metadata NO sensible. (email, uuid del user, pk integer de su persona, pk de rol|None)
# pks de rol: medico=2, odontologo=3, tutor=4, ayudante=5.
TEST_USERS = [
    ("superadmin@prosane.test", "c0000000-0000-0000-0000-000000000001", 9001, None),
    ("medico@prosane.test", "c0000000-0000-0000-0000-000000000002", 9002, 2),
    ("odontologo@prosane.test", "c0000000-0000-0000-0000-000000000003", 9003, 3),
    ("ayudante@prosane.test", "c0000000-0000-0000-0000-000000000004", 9004, 5),
    ("tutor@prosane.test", "c0000000-0000-0000-0000-000000000005", 9005, 4),
]

_TS = "2026-01-01T00:00:00Z"


def build_users_fixture(password):
    """Devuelve la lista de objetos de fixture (Usuarios + UserRole) con el hash."""
    hashed = make_password(password)  # PBKDF2 (hasher de Django), salt aleatorio
    objs = []
    for email, uuid, persona_pk, rol_pk in TEST_USERS:
        objs.append({
            "model": "authentication.usuarios",
            "pk": uuid,
            "fields": {
                "email": email,
                "password": hashed,           # → columna password_hash
                "persona": persona_pk,        # FK integer a personas.id
                "is_superuser": rol_pk is None,
                "is_staff": rol_pk is None,
                "is_active": True,
                "date_joined": _TS,
            },
        })
    ur_pk = 9001
    for _email, uuid, _persona_pk, rol_pk in TEST_USERS:
        if rol_pk is not None:
            objs.append({
                "model": "authentication.userrole",
                "pk": ur_pk,
                "fields": {"id_user": uuid, "id_rol": rol_pk, "created_at": _TS, "updated_at": _TS},
            })
            ur_pk += 1
    return objs


class Command(BaseCommand):
    help = "Genera authentication/fixtures/users.json con hashes de Django (solo dev)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=None)

    def handle(self, *args, **options):
        if not getattr(settings, "SEEDS_ENABLED", False):
            raise CommandError(
                "SEEDS_ENABLED no está activo: este comando es SOLO para desarrollo local."
            )
        password = options["password"] or os.environ.get("SEED_USER_PASSWORD")
        if not password:
            raise CommandError(
                "Falta la contraseña: pasá --password o seteá la env var SEED_USER_PASSWORD."
            )

        objs = build_users_fixture(password)
        path = os.path.join(
            apps.get_app_config("authentication").path, "fixtures", "users.json"
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(objs, f, indent=2, ensure_ascii=False)
            f.write("\n")
        self.stdout.write(self.style.SUCCESS(f"users.json generado ({len(TEST_USERS)} usuarios) en {path}"))

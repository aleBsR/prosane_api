"""Genera apps/usuarios/fixtures/users.json con hashes de Django (PBKDF2).

Los usuarios de prueba son de JUGUETE (solo dev local). El hash se calcula con
make_password() — el hasher configurado del proyecto — para que el login de Django
los verifique. La contraseña sale de --password o de la env var SEED_USER_PASSWORD;
NUNCA se escribe en texto plano.

Uso:
    SEED_USER_PASSWORD=... python manage.py generate_users_fixture
    python manage.py generate_users_fixture --password ...
"""
import json
import os

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from apps.usuarios.management.commands._fixture_uuids import role_uuid


TEST_USERS = [
    ("superadmin@prosane.test", "c0000000-0000-0000-0000-000000000001", True, "superadmin"),
    ("medico@prosane.test", "c0000000-0000-0000-0000-000000000002", False, "medico"),
    ("odontologo@prosane.test", "c0000000-0000-0000-0000-000000000003", False, "odontologo"),
    ("ayudante@prosane.test", "c0000000-0000-0000-0000-000000000004", False, "ayudante"),
    ("tutor@prosane.test", "c0000000-0000-0000-0000-000000000005", False, "tutor"),
    ("medico1@prosane.test", "c0000000-0000-0000-0000-000000000006", False, "medico"),
    ("odontologo1@prosane.test", "c0000000-0000-0000-0000-000000000007", False, "odontologo"),
    ("escuela@prosane.test", "c0000000-0000-0000-0000-000000000008", False, "escuela"),
]

_TS = "2026-01-01T00:00:00Z"


def build_users_fixture(password):
    """Devuelve la lista de objetos de fixture (Usuario + RoleUsuario) con el hash."""
    hashed = make_password(password)
    objs = []
    for email, uuid, is_superuser, rol_name in TEST_USERS:
        objs.append({
            "model": "usuarios.usuario",
            "pk": uuid,
            "fields": {
                "email": email,
                "password": hashed,
                "is_superuser": is_superuser,
                "is_staff": is_superuser,
                "is_active": True,
                "date_joined": _TS,
            },
        })

    roleusuario_pk = 9001
    for _email, user_uuid, _is_superuser, rol_name in TEST_USERS:
        if rol_name:
            objs.append({
                "model": "usuarios.roleusuario",
                "pk": roleusuario_pk,
                "fields": {
                    "id_user": user_uuid,
                    "id_rol": str(role_uuid(rol_name)),
                    "created_at": _TS,
                    "updated_at": _TS,
                },
            })
            roleusuario_pk += 1
    return objs


class Command(BaseCommand):
    help = "Genera apps/usuarios/fixtures/users.json con hashes de Django (solo dev)."

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
            settings.BASE_DIR, "apps", "usuarios", "fixtures", "users.json"
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(objs, f, indent=2, ensure_ascii=False)
            f.write("\n")
        self.stdout.write(
            self.style.SUCCESS(f"users.json generado ({len(TEST_USERS)} usuarios) en {path}")
        )

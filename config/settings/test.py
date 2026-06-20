"""Settings para correr la suite de tests: aislados, rápidos, sin .env."""
from .base import *  # noqa: F401,F403

SECRET_KEY = "django-insecure-test-key-only-for-tests"

# simplejwt fija SIGNING_KEY al importar base.py (cuando SECRET_KEY aún era None);
# lo realineamos al SECRET_KEY de test.
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": SECRET_KEY}  # noqa: F405

# SQLite en memoria: evita depender de Postgres y de las tablas managed = True.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Hashing rápido para tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# URLconf vacío: aísla los tests de bugs pre-existentes en config.urls
# (p. ej. falta patients/urls.py). Ver config/test_urls.py.
ROOT_URLCONF = "config.test_urls"

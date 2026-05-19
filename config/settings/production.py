from .base import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Deberás configurar los hosts permitidos cuando sepas el dominio
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Configuraciones para producción
# Por ejemplo: Seguridad de cookies, HTTPS, almacenamiento de estáticos en S3, etc.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

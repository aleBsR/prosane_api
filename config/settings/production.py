import os
from .base import *
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Cargar variables de entorno. Se puede configurar una ruta absoluta
# en producción definiendo PROSANE_ENV_PATH (ej: /opt/SIP_Servidor/SIP/.env)
dotenv_path = os.getenv("PROSANE_ENV_PATH", os.path.join(BASE_DIR, '.env'))
load_dotenv(dotenv_path=dotenv_path)

# Seguridad
DEBUG = False
SECRET_KEY = os.getenv("SECRET_KEY")

# Hosts permitidos desde .env
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Configuración de base de datos PostgreSQL de producción
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

# HTTPS y seguridad en producción
SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Archivos estáticos
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Archivos multimedia
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Zona horaria
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_TZ = False

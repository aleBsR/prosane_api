from .base import *
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# En desarrollo permitimos todos los hosts por comodidad
ALLOWED_HOSTS = ['*']

# Configuración de base de datos PostgreSQL local
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

# Archivos Estáticos
STATIC_URL = 'static/'


# ───────────────────────────────────────────────────────────────────────────
# Logging verboso de DESARROLLO (SOLO acá; nunca en base.py ni production.py).
# Loguea requests/responses con bodies JSON redactados (Ley 25.326: sin
# DNI/diagnósticos/emails/tokens en texto plano). Ver common/dev_logging.py.
# ───────────────────────────────────────────────────────────────────────────
MIDDLEWARE = MIDDLEWARE + ['common.dev_logging.RequestResponseLoggingMiddleware']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'dev': {
            'format': '%(asctime)s %(levelname)s %(name)s | %(message)s',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'dev'},
    },
    'loggers': {
        # Nuestro middleware de requests/responses (verboso).
        'prosane.api': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        # Errores/4xx-5xx de Django.
        'django.request': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}

# Paso 01: Infraestructura base

## Objetivo

Agregar `django-cors-headers`, crear `.env.example`, registrar `ActionPermissionBackend`, y corregir settings issues.

## 1. Agregar django-cors-headers

**Archivo:** `requirements/common.txt`
```
django-cors-headers==4.7.0
```

Instalar:
```bash
pip install django-cors-headers
```

**Archivo:** `config/settings/base.py`
```python
INSTALLED_APPS += [
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # al principio
    # ... resto del middleware
]

CORS_ALLOW_ALL_ORIGINS = True  # TODO: restringir en producción
```

## 2. Registrar ActionPermissionBackend

**Archivo:** `config/settings/base.py`
```python
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'apps.usuarios.action_resolution.ActionPermissionBackend',
]
```

## 3. Crear .env.example

**Archivo:** `.env.example`
```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=prosane
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

## 4. Fix SECRET_KEY sin fallback

**Archivo:** `config/settings/base.py`
```python
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY no está definida en el entorno.')
```

## 5. Verificar

```bash
python manage.py check
```

## Criterio de aceptación

- `pip install` no da errores
- `python manage.py check` pasa sin warnings
- `.env.example` documenta todas las variables
- CORS configurado
- `ActionPermissionBackend` registrado en AUTHENTICATION_BACKENDS

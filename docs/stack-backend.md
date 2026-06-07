# Etapa 0 — Stack backend: Django + Django REST Framework

> **Decisión del equipo**: backend en **Django REST Framework** con **Python 3.10.12**. Este documento resume las mejores prácticas para que el proyecto sea **estable en producción** y no falle al deployearlo.

---

## 1. Versiones recomendadas (Mayo 2026)

| Componente | Versión | Por qué |
|-----------|---------|---------|
| **Python** | **3.10.12** | Versión definida por el equipo. Estable, ampliamente soportada por Django 5.x. |
| **Django** | **5.1 LTS** (o 5.2 si ya está disponible como LTS) | LTS = Long Term Support → parches de seguridad por 3 años. Compatible con Python 3.10–3.13. |
| **Django REST Framework** | **3.15+** | Última estable, soporta Django 5.x. |
| **PostgreSQL** | **15 o 16** | Estándar en producción para Django. SQLite solo para desarrollo. |
| **Gunicorn** | última estable | WSGI server, battle-tested en prod. |
| **Nginx** | última estable | Reverse proxy + servir estáticos + HTTPS. |

> ⚠️ Django 4.2 LTS también es opción válida si el hosting tiene restricciones, pero 5.x es preferible para proyecto nuevo en 2026.

## 2. Estructura de proyecto recomendada (escalable)

```
salud_salta_api/
├── README.md
├── manage.py
├── requirements/
│   ├── base.txt              # deps comunes (Django, DRF, psycopg, etc.)
│   ├── development.txt       # incluye base + debug-toolbar, pytest, etc.
│   ├── production.txt        # incluye base + gunicorn, sentry-sdk, etc.
│   └── local.txt             # base + cosas locales
├── config/                   # NO se llama "salud_salta" para evitar conflictos
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py           # config común a todos los entornos
│   │   ├── development.py    # DEBUG=True, SQLite o Postgres local
│   │   ├── staging.py
│   │   └── production.py     # DEBUG=False, secrets via env vars
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                     # TODAS las apps Django acá adentro
│   ├── __init__.py
│   ├── users/                # autenticación, perfiles, roles
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py
│   │   ├── services.py       # lógica de negocio (NO en views)
│   │   ├── selectors.py      # queries complejas
│   │   └── tests/
│   ├── escuelas/
│   ├── salud/                # planillas PROSANE, controles, derivaciones
│   └── notifications/
├── static/
├── media/
├── docs/
├── .env.example              # template de variables de entorno
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml            # config de herramientas (ruff, mypy, pytest)
```

### Principios clave de esta estructura

1. **`config/` en vez de un nombre de proyecto** → evita conflictos de imports cuando el proyecto crece.
2. **`apps/` agrupa todas las apps Django** → orden claro, fácil de encontrar.
3. **Settings divididas por entorno** → nunca un solo `settings.py` con `if DEBUG`.
4. **Requirements separados** → producción no instala `pytest` ni `debug-toolbar`.
5. **`services.py` y `selectors.py`** → views como adaptadores HTTP delgados; lógica de negocio en services. Esto facilita testing y mantenibilidad.
6. **URLs versionadas** desde día 1: `/api/v1/...`. Cuando haya breaking changes, `/api/v2/`.

## 3. Configuración crítica para producción

### settings/base.py — claves de seguridad

```python
# Obligatorio: leer secretos desde variables de entorno
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False                         # default seguro
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# HTTPS / cookies seguras
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000        # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Headers de seguridad
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
```

### Checklist oficial de Django

```bash
python manage.py check --deploy
```

→ Django mismo te indica qué configurar antes de salir a prod.

## 4. Stack de deployment recomendado

```
[ Cliente Flutter / Browser ]
            │ HTTPS
            ▼
     [ Nginx (reverse proxy) ]
            │
            ├── /static/ y /media/  →  archivos servidos directamente
            │
            └── /api/ → proxy_pass → [ Gunicorn (3-5 workers) ]
                                              │
                                              ▼
                                       [ Django + DRF ]
                                              │
                                              ▼
                                       [ PostgreSQL 15+ ]
                                              │
                                              ▼
                                       [ Redis (cache + tasks) ]
                                              │
                                              ▼
                                       [ Celery workers (jobs async) ]
```

### Componentes y para qué

- **Nginx**: terminación HTTPS (con Let's Encrypt + Certbot), reverse proxy, servir estáticos.
- **Gunicorn**: WSGI server para correr Django en prod (no usar `runserver`).
- **PostgreSQL**: BD real. SQLite NO se usa en prod.
- **Redis** (opcional pero recomendado): cache + broker para Celery.
- **Celery** (si hay tareas pesadas): envío de mails, generación de PDFs (¡constancia PROSANE!), notificaciones.
- **Sentry** (recomendado): tracking de errores en prod.
- **Docker + docker-compose**: para reproducibilidad. Mismo entorno en dev y prod.

## 5. Seguridad — checklist mínimo

- [ ] `DEBUG=False` en producción (siempre, sin excepción).
- [ ] `SECRET_KEY` en variable de entorno, nunca commiteada.
- [ ] `ALLOWED_HOSTS` configurado.
- [ ] HTTPS obligatorio (Let's Encrypt es gratis).
- [ ] Headers de seguridad activos (HSTS, X-Frame-Options, etc.).
- [ ] Autenticación robusta — recomendado **JWT** (`djangorestframework-simplejwt`) para una app Flutter.
- [ ] Permisos por rol implementados en DRF (`permission_classes`).
- [ ] Rate limiting (`DEFAULT_THROTTLE_CLASSES` en DRF) para prevenir abuso.
- [ ] CORS configurado correctamente con `django-cors-headers` (solo dominios conocidos).
- [ ] Logs de seguridad activos.
- [ ] Backups automáticos de PostgreSQL.
- [ ] Datos sensibles (salud → categoría especial por Ley 25.326) cifrados en reposo.

## 6. Paquetes esenciales del stack

```text
# requirements/base.txt
Django>=5.1,<5.2
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3      # JWT auth
django-cors-headers>=4.3
django-environ>=0.11                    # leer .env
psycopg[binary]>=3.1                    # driver Postgres
Pillow>=10.0                            # imágenes (firmas, fotos)
django-filter>=23.0                     # filtros REST
drf-spectacular>=0.27                   # docs OpenAPI/Swagger automáticas
```

```text
# requirements/production.txt
-r base.txt
gunicorn>=21.0
sentry-sdk>=1.40
whitenoise>=6.6                         # servir estáticos sin nginx (alternativa)
redis>=5.0
celery>=5.3
```

```text
# requirements/development.txt
-r base.txt
django-debug-toolbar>=4.2
pytest>=8.0
pytest-django>=4.7
factory-boy>=3.3
ruff>=0.3
mypy>=1.8
```

## 7. Buenas prácticas para evitar caer en prod

1. **Migrations versionadas y revisadas** → nunca `--fake` salvo emergencia documentada.
2. **`python manage.py collectstatic --noinput`** en cada deploy.
3. **Healthcheck endpoint** (`/healthz`) que devuelve 200 si la app está viva.
4. **Logs estructurados** (JSON) → fácil de buscar en Sentry / CloudWatch.
5. **CI/CD** con tests obligatorios antes de deployar (GitHub Actions o GitLab CI).
6. **Variables de entorno** SIEMPRE — nada hardcodeado: secrets, URLs de DB, claves de API.
7. **Versionar la API** (`/api/v1/`) desde el principio.
8. **Documentación OpenAPI automática** con `drf-spectacular` → permite que Flutter genere clientes automáticos.
9. **Throttling** activo para endpoints públicos.
10. **Backups diarios** de la base.

## 8. Documentación OpenAPI (clave para Flutter)

Con `drf-spectacular` la API queda autodescripta:

```python
# settings/base.py
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
```

Esto genera un `schema.yaml` que se puede usar en Flutter con:

- **openapi-generator** → genera el cliente Dart automáticamente.
- Documentación Swagger UI accesible en `/api/docs/`.

Beneficio: el frontend Flutter y el backend Django quedan **sincronizados por contrato** — si alguno cambia, lo ve el otro.

## 9. Hosting recomendado para un TP universitario

Opciones por costo / complejidad:

| Opción | Costo | Complejidad | Para qué |
|--------|-------|-------------|----------|
| **Railway** / **Render** | Free tier / ~5 USD | Baja | Deploy en minutos, ideal para TP |
| **PythonAnywhere** | Free | Muy baja | Demo, pero limitado |
| **Fly.io** | Free tier | Media | Más control, Docker |
| **DigitalOcean Droplet** | ~6 USD | Alta | Control total, Nginx + Gunicorn manual |
| **AWS / GCP** | Free tier | Alta | Sobredimensionado para TP |

> **Recomendación para el TP**: **Railway** o **Render** — deploy con git push, base PostgreSQL gestionada, HTTPS automático, suficiente para demos al profe.

## 10. Fuentes consultadas (links para el socio)

### Estructura y best practices

- [Django Project Structure Best Practices: A Production-Ready Guide (DEV)](https://dev.to/alansomathew/django-project-structure-best-practices-a-production-ready-guide-3io3)
- [Django REST Framework: The Complete Guide for 2026](https://devtoolbox.dedyn.io/blog/django-rest-framework-complete-guide)
- [django-project-structure (saqibur/GitHub) — template oficial referencia](https://github.com/saqibur/django-project-structure)
- [Django Folder and File Project Structure: Best Practices 2026](https://studygyaan.com/django/best-practice-to-structure-django-project-directories-and-files)
- [Building Robust APIs with DRF: Best Practices and Project Structure (Medium)](https://medium.com/@anindya.lokeswara/building-robust-apis-with-django-rest-framework-best-practices-and-project-structure-9d5f4447539f)
- [Best Practices for Building a Django (DRF) Project (Medium)](https://medium.com/@palwishaakhtar/best-practices-for-building-a-django-drf-project-21fead201780)
- [Django Project Structure Best Practices in 2026 (Technaureus)](https://www.technaureus.com/blog-detail/django-project-structure-best-practices-2026)

### Deployment

- [How to Set Up Django with Postgres, Nginx, and Gunicorn on Ubuntu (DigitalOcean)](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu)
- [Securely Deploy a Django App With Gunicorn, Nginx, & HTTPS (Real Python)](https://realpython.com/django-nginx-gunicorn/)
- [Deploy DRF to Production: Docker, Nginx, SSL — The Complete Guide](https://www.bhusalmanish.com.np/blog/posts/deploy-drf-production.html)
- [Dockerizing Django with Postgres, Gunicorn, and Nginx (TestDriven.io)](https://testdriven.io/blog/dockerizing-django-with-postgres-gunicorn-and-nginx/)
- [How To Scale and Secure a Django Application with Docker, Nginx, and Let's Encrypt (DigitalOcean)](https://www.digitalocean.com/community/tutorials/how-to-scale-and-secure-a-django-application-with-docker-nginx-and-let-s-encrypt)
- [Django deployment with Nginx and Gunicorn (Python Lessons)](https://pylessons.com/django-deployment)

### Documentación oficial

- [Django Deployment Checklist (oficial)](https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/)
- [Django REST Framework — docs oficiales](https://www.django-rest-framework.org/)
- [drf-spectacular — OpenAPI/Swagger automático](https://drf-spectacular.readthedocs.io/)

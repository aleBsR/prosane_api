# PROSANE API

Backend del sistema PROSANE — API REST para la digitalización del Programa Nacional de Salud Escolar.

Desarrollado con **Django 6.0.5** + **Django REST Framework 3.17.1**. Autenticación JWT, permisos data-driven, soft-delete y auditoría.

---

## Requisitos

- **Python 3.13+**
- **PostgreSQL 16+**
- **pip** (gestor de paquetes de Python)

Dependencias principales (ver `requirements/requirements.txt`):

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| Django | 6.0.5 | Framework web |
| djangorestframework | 3.17.1 | API REST |
| djangorestframework-simplejwt | 5.5.1 | Autenticación JWT |
| psycopg2-binary | 2.9.12 | Conexión PostgreSQL |
| django-cors-headers | 4.9.0 | CORS (desarrollo permisivo) |
| drf-spectacular | 0.29.0 | Documentación OpenAPI/Swagger |
| python-dotenv | 1.2.2 | Variables de entorno |

---

## Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone <repo-url> prosane_api
cd prosane_api
```

### 2. Crear y activar entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements/requirements.txt
```

### 4. Configurar variables de entorno

Copiar `.env.example` a `.env` y completar:

```bash
cp .env.example .env
```

Editar `.env` con tus datos:

```
SECRET_KEY=generá-una-clave-segura
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=prosane
DB_USER=ale
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432
```

Para generar una `SECRET_KEY`:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Crear la base de datos

```bash
createdb -U postgres prosane
```

### 6. Ejecutar migraciones

```bash
python manage.py migrate
```

### 7. Cargar datos de prueba (fixtures)

```bash
python manage.py loaddata actions users roles
```

Esto crea los roles, permisos y usuarios de prueba.

### 8. Iniciar servidor

```bash
# Local (solo tu máquina)
python manage.py runserver

# Accesible desde la red local (para conectar con la app en un celular/tablet)
python manage.py runserver 0.0.0.0:8000
```

El servidor arranca en `http://localhost:8000`.

---

## Usuarios de prueba (password: `prosane123`)

| Email | Rol |
|-------|-----|
| `superadmin@prosane.test` | Superadmin — acceso total |
| `medico@prosane.test` | Médico — ver operativos, evaluar alumnos |
| `odontologo@prosane.test` | Odontólogo — ver operativos, evaluar alumnos |
| `ayudante@prosane.test` | Ayudante — CRUD escuelas, gestión completa de operativos |
| `tutor@prosane.test` | Tutor — registro de hijos, ver escuelas |
| `escuela@prosane.test` | Escuela — alumnos, cursos y operativos de su escuela |

---

## Guia de pruebas

El flujo completo por roles esta documentado en:
`C:\Users\usuario\Documents\Alejandro\Documentos\Escuela\GUIA_PRUEBAS_FLUJO_COMPLETO.md`

## Documentación interactiva de la API

Con el servidor corriendo, abrí en el navegador:

| Herramienta | URL |
|-------------|-----|
| Swagger UI | `http://localhost:8000/docs/swagger-ui/` |
| ReDoc | `http://localhost:8000/docs/redoc/` |
| Schema OpenAPI | `http://localhost:8000/docs/schema/` |

---

## Conexión con la app Flutter (`prosane_app`)

La app Flutter se conecta a esta API. La URL base se configura al ejecutar la app mediante `--dart-define`:

| Dónde corre la app | `API_BASE_URL` |
|---|---|
| Emulador Android | `http://10.0.2.2:8000/api/v1/auth` |
| Navegador web / escritorio | `http://localhost:8000/api/v1/auth` |
| Celular/tablet físico (misma red) | `http://<IP-de-tu-PC>:8000/api/v1/auth` |

Para que un dispositivo físico en la red local pueda alcanzar la API, iniciar Django con:
```bash
python manage.py runserver 0.0.0.0:8000
```

Ejemplo de ejecución de la app Flutter:
```bash
flutter run --dart-define=API_BASE_URL=http://192.168.0.8:8000/api/v1/auth
```

---

## Comandos útiles

```bash
# Migraciones
python manage.py makemigrations
python manage.py migrate

# Tests
python manage.py test apps/usuarios apps/escuelas apps/operativos apps/tutores --settings=config.settings.test

# Shell de Django
python manage.py shell

# Shell de base de datos
python manage.py dbshell

# Crear usuario admin
python manage.py createsuperuser
```

---

## Rama activa

El desarrollo principal está en la rama `dev-base`. La rama `base` contiene la arquitectura de las carpetas.


```bash
git checkout dev-base
```

---

## Estructura del proyecto

```
config/           → Configuración Django (settings, urls, wsgi/asgi)
common/           → BaseModel con UUID, auditoría y soft-delete
apps/
  personas/       → Persona y Domicilio
  usuarios/       → Usuario, autenticación JWT, roles, permisos data-driven
  tutores/        → Tutores/padres, registro y gestión de hijos
  pacientes/      → Pacientes (alumnos)
  antecedentes/   → Antecedentes personales y familiares
  vacunas/        → Vacunas y carnet de vacunación
  profesionales/  → Profesionales de salud + validación REFEPS
  escuelas/       → Escuelas, cursos y observaciones
  operativos/     → Operativos sanitarios (núcleo del negocio)
  docs/           → Documentación Swagger/ReDoc
requirements/
  requirements.txt
```

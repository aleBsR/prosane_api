# Arquitectura del proyecto

Este documento describe la organización de carpetas y archivos del proyecto **PROSANE API**, una API REST construida con Django y Django REST Framework.

El objetivo es que cualquier desarrollador que se incorpore al proyecto entienda rápidamente dónde vive cada pieza del sistema y por qué se organizó de esa forma.

---

## Filosofía general

- **Aplicaciones pequeñas y enfocadas**: cada app representa un bounded context del dominio (usuarios, pacientes, vacunas, etc.).
- **Rama `base` minimalista**: en esta rama solo hay modelos, serializers simples, admins y migraciones. No hay endpoints, views, ni permissions; esos se agregan en ramas de features.
- **Capa de servicios**: la lógica de negocio compleja no vive en serializers ni en views; se delega a funciones o clases dentro de `services/`.
- **Nombres en español**: las apps y sus modelos usan nombres en español para reflejar el dominio del proyecto.
- **Prefijo `apps.`**: todas las apps propias viven bajo `apps/` y se referencian con ese prefijo en `INSTALLED_APPS` y en imports.

---

## Estructura de carpetas

```
prosane_api/
│
├── config/                 # Configuración del proyecto Django
├── common/                 # Código compartido entre todas las apps
├── apps/                   # Apps del dominio
├── docs/                   # Documentación para desarrolladores
├── context/                # Artefactos de diseño (DER, etc.)
├── requirements/           # Dependencias por entorno
├── venv/                   # Entorno virtual
├── .env                    # Variables de entorno
├── manage.py               # CLI de Django
└── db.sqlite3              # SQLite local (solo desarrollo)
```

---

## `config/`

Contiene la configuración central de Django.

| Archivo/carpeta | Propósito |
|-----------------|-----------|
| `settings/base.py` | Settings comunes a todos los entornos. |
| `settings/local.py` | Settings para desarrollo local (PostgreSQL, DEBUG=True). |
| `settings/test.py` | Settings para correr tests (SQLite en memoria). |
| `settings/production.py` | Settings para producción. |
| `urls.py` | Router principal de URLs. En `base` solo expone el admin. |
| `test_urls.py` | URLconf vacío usado por los tests. |
| `wsgi.py` / `asgi.py` | Entrypoints del servidor. |

---

## `common/`

Código reutilizable por todas las apps. No debe depender de ninguna app del dominio.

| Archivo | Propósito |
|---------|-----------|
| `models.py` | `BaseModel` abstracto con UUID, auditoría y soft delete. |
| `managers.py` | Managers y querysets para soft delete. |
| `serializers.py` | `AuditSerializerMixin` para sellar el actor en serializers. |
| `mixins.py` | `AuditViewMixin` para sellar el actor desde vistas. |
| `tests/` | Tests unitarios de las utilidades de `common`. |

> **Regla**: si algo es transversal a todas las apps, va en `common`. Si es específico de un dominio, va en su app.

---

## `apps/`

Carpeta que agrupa todas las aplicaciones del dominio. Cada app sigue la misma estructura base.

### Estructura interna de una app

```
apps/<nombre_app>/
├── __init__.py
├── apps.py                 # Configuración de la app
├── admin.py                # Registro de modelos en el admin de Django
├── models/                 # Modelos divididos por archivo
│   ├── __init__.py         # Exporta los modelos públicos
│   ├── <modelo1>.py
│   └── <modelo2>.py
├── serializers.py          # Serializers simples (base)
├── services/               # Lógica de negocio (vacío en base)
│   └── __init__.py
├── tests.py                # Tests de la app
└── migrations/
    └── __init__.py
```

### Apps del dominio

| App | Responsabilidad | Modelos principales |
|-----|-----------------|---------------------|
| `apps.personas` | Datos personales y direcciones compartidas. | `Persona`, `Domicilio` |
| `apps.usuarios` | Autenticación, roles y permisos. | `Usuario`, `Rol`, `RoleUsuario` |
| `apps.tutores` | Perfil de tutor o responsable de un paciente. | `Tutor` |
| `apps.pacientes` | Registro de pacientes. | `Paciente` |
| `apps.antecedentes` | Historia clínica del paciente. | `AntecedenteFamiliar`, `AntecedentePersonal` |
| `apps.vacunas` | Control de vacunación. | `Vacuna`, `CarnetVacuna` |
| `apps.profesionales` | Perfiles profesionales y validación de matrículas. | `Profesional` |
| `apps.escuelas` | Escuelas y observaciones escolares de pacientes. | `Escuela`, `ObservacionEscuela` |
| `apps.docs` | App Django para documentación interactiva de la API. | - |

### ¿Por qué `models/` en lugar de `models.py`?

Dividir los modelos en archivos separados mejora la legibilidad y el mantenimiento a medida que el dominio crece. Cada archivo contiene un único modelo y su lógica relacionada. El `__init__.py` se encarga de exponer los modelos públicos para que el resto del proyecto siga importando de forma simple:

```python
from apps.usuarios.models import Usuario, Rol
```

### ¿Por qué `services/`?

Los serializers deben encargarse solo de validación y representación. Cuando una operación involucra varios modelos, llamadas externas o reglas de negocio, esa lógica va en `services/`. En la rama `base` las carpetas están vacías; se completarán en cada feature.

Ejemplo de uso futuro:

```python
# apps/usuarios/services/registration.py
def register_tutor(data):
    # crear persona, usuario, rol y tutor
    pass
```

---

## `docs/`

Documentación técnica para desarrolladores. No es una app Django.

| Archivo | Propósito |
|---------|-----------|
| `README.md` | Introducción y guía de la documentación. |
| `arquitecturaProyecto.md` | Este documento. |

La documentación interactiva de la API se construirá en la app Django `apps/docs`.

---

## `context/`

Contiene artefactos de diseño como el DER (Diagrama Entidad-Relación) del proyecto.

---

## Patrones importantes


### `BaseModel`

Casi todos los modelos de dominio heredan de `common.models.BaseModel`, que proporciona:

- `id` como UUID.
- Campos de auditoría: `created_at`, `updated_at`, `created_by`, `updated_by`.
- Soft delete mediante `deleted_at`.

#### Excepciones

- **`Usuario`** no hereda de `BaseModel` porque ya hereda de `AbstractBaseUser` y `PermissionsMixin`. Agregar auditoría con FK a sí mismo complica el modelo de autenticación.
- **`Vacuna`** y **`CarnetVacuna`** sí heredan de `BaseModel`; antes tenían su propio `id` UUID a mano.

### Modelos `managed = True`

Todos los modelos de dominio usan `managed = True`. Esto significa que Django controla el esquema: las migraciones crean, modifican y eliminan las tablas.

> En etapas anteriores algunos modelos usaban `managed = False` porque las tablas ya existían en una base legada. En la rama `base` se optó por que Django administre el esquema para facilitar el desarrollo y los tests.

### Modelo eliminado

- **`Matricula`** fue eliminado de `apps.profesionales`. La validación de matrículas se maneja actualmente mediante el mock de REFEPS en `apps.profesionales.services.services_refeps.py`.

### Referencias entre apps

Las ForeignKey entre apps usan el `app_label` del modelo destino:

```python
# Correcto
persona = models.ForeignKey("personas.Persona", ...)

# Incorrecto
persona = models.ForeignKey("apps.personas.Persona", ...)
```

El `app_label` es la última parte del nombre de la app (`personas`, `usuarios`, etc.).

---

## Tests

- Los tests usan `config.settings.test` (SQLite en memoria).
- La suite principal está en `common/tests/` y verifica el comportamiento de `BaseModel`.
- Cada app tiene su propio `tests.py` para tests específicos del dominio.

Para correr los tests:

```bash
python manage.py test --settings=config.settings.test
```

---

## Convenciones de nombres

- Apps: español, plural (`usuarios`, `pacientes`, `vacunas`).
- Modelos: español, en **singular** (`Persona`, `Usuario`, `Rol`).
- Tablas: se conservan los nombres originales mediante `db_table`.
- Archivos de modelos: singular del modelo (`usuario.py`, `paciente.py`).
- Imports: siempre con el prefijo `apps.`, por ejemplo `from apps.personas.models import Persona`.

---

## ¿Cómo agregar una nueva app?

1. Crear la carpeta bajo `apps/<nombre_app>/`.
2. Agregar `apps/<nombre_app>` a `INSTALLED_APPS`.
3. Crear `apps.py` con `name = "apps.<nombre_app>"`.
4. Crear `models/` con los modelos y su `__init__.py`.
5. Crear `serializers.py` simple.
6. Crear `admin.py`, `tests.py` y `migrations/__init__.py`.
7. Crear `services/` solo si la app tendrá lógica de negocio compleja.
8. Ejecutar `makemigrations` y verificar con `django check`.

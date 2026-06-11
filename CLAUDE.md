# PROSANE API — guía para el equipo

Backend REST del circuito **PROSANE** (Programa Nacional de Salud Escolar) en Salta
Capital, Argentina. Es una **capa digital intermedia** que digitaliza la planilla de
Control Integral de Salud (CIS) — **no reemplaza SISA**, lo alimenta. Consumido por una
app Flutter (`Mobile/TPFinal/salud_salta`) y un panel web.

Equipo: Roberto (guía/arquitectura), Ramiro y Ale (desarrollo). El idioma del dominio y
de los comentarios es **español**.

## Documentación de referencia

- `docs/modelo-de-datos.md` — **fuente de verdad del dominio** (modelo basado en la planilla PROSANE oficial).
- `docs/stack-backend.md` — estructura de proyecto, seguridad y deployment.
- `docs/reconciliacion-modelo.md` — **leer antes de tocar modelos**: hoy conviven tres vocabularios distintos y el modelo NO está cerrado.
- `docs/arquitectura.md` — **mapa de apps por dominio** + convenciones (leer para ubicarse en la estructura y saber dónde va cada cosa).
- `docs/reglas/` — playbooks paso a paso para tareas comunes (ej. `crear-accion.md`).
- `prosane_propuesta.md` — propuesta de diseño original (actores y flujos).

## Stack actual (verificado en el código)

- **Django 6.0.5** + **DRF 3.17.1** + **djangorestframework-simplejwt** (`requirements.txt`).
- Auth: **JWT** (`Bearer`), `AUTH_USER_MODEL = 'authentication.Usuarios'` (custom, login por **email**, PK UUID).
- Por defecto **toda** vista exige autenticación (`DEFAULT_PERMISSION_CLASSES = IsAuthenticated`).
- Settings divididas: `config/settings/{base,local,production}.py`. `manage.py` usa `local`.
- DB: SQLite en `base.py`; PostgreSQL en `local`/`production` vía `.env`.

> ⚠️ **Inconsistencia a resolver:** los `docs/` recomiendan **Django 5.1 LTS**, pero el
> código declara **Django 6.0.5**. Decidir cuál antes de avanzar (no asumir).

## Reglas NO negociables

**Seguridad**
- **Nunca** commitear secrets. `SECRET_KEY`, credenciales de DB y claves de API van solo en `.env` (ya está en `.gitignore`). `.env.example` documenta las variables sin valores.
- `DEBUG = False` en producción, siempre. `ALLOWED_HOSTS` restringido (nada de `['*']` fuera de local).
- Validar permisos por rol en cada endpoint sensible (`permission_classes`), no confiar solo en `IsAuthenticated`.

**Datos sensibles (esto es una app de salud de menores)**
- Los datos clínicos son **categoría sensible** (Ley 25.326) y los titulares son **menores** (Ley 26.061). Tratarlos con ese cuidado: acceso mínimo por rol, sin loguear DNI/diagnósticos/emails en texto plano.
- **Consentimiento** obligatorio antes de cualquier control (Ley 26.529). Adolescentes ≥13 pueden consentir por sí mismos (autonomía progresiva).
- La `Constancia` guarda **snapshots** de los datos al momento de la firma, **no FKs vivas** — un documento legal emitido no debe mutar si después cambian los datos.
- Un tutor solo ve lo que el profesional marca como visible; nunca la ficha clínica completa.

**Modelo de datos**
- El esquema **no está cerrado** (ver `docs/reconciliacion-modelo.md`). No crear ni renombrar tablas de dominio sin acordarlo — Roberto está revisando las tablas existentes.
- Casi todas las tablas actuales son `managed = False` (salieron de `inspectdb`). Aclarar quién es dueño del esquema antes de cambiarlas.

## Convenciones de código

- **Vistas delgadas**: la lógica de negocio va en `services.py`; las queries complejas en `selectors.py`. Las views son adaptadores HTTP, no contienen reglas.
- **Serializers** para validación y forma de los datos; usar `write_only` para passwords y campos sensibles. Evitar `fields = '__all__'` en datos sensibles — listar campos explícitos.
- **Operaciones multi-modelo** (crear Usuario+Persona+Rol, etc.) van dentro de `@transaction.atomic`.
- **Versionar la API**: `/api/v1/...` desde el inicio.
- Vocabulario del dominio consistente con `docs/modelo-de-datos.md` (no mezclar `NNA`/`Paciente`/`Tutor`/`Familia` sin criterio).
- Tests con `pytest` por feature; no dar algo por "andando" sin correrlo.

## Estado conocido (cosas rotas a la fecha)

- El repo **no arranca** sin `.env` con `SECRET_KEY` (simplejwt usa `SIGNING_KEY = SECRET_KEY` en import → crashea si es `None`).
- `authentication/urls.py` importa `solo_medicos`, que **no existe** en `views.py` → `ImportError`.
- `config/urls.py` hace `include('patients.urls')`, pero **`patients/urls.py` no existe** → `ImportError`.
- `PacientesSerializer` lista `sexo`/`fecha_nacimiento`, que están en `Personas`, no en `Pacientes`.
- Falta `django-cors-headers` (la app Flutter lo va a necesitar).
- No hay endpoint de refresh de token, ni docs OpenAPI (`drf-spectacular`), ni tests.

## Herramientas útiles en este repo

- **context7** (MCP, ya conectado): traer documentación **actualizada** de Django 6 / DRF / simplejwt. El stack es muy nuevo — preferirlo antes que responder de memoria.
- Antes de implementar features: usar las skills de proceso (planificación, TDD, debugging sistemático, code review).
- `python manage.py check --deploy` antes de cualquier deploy.

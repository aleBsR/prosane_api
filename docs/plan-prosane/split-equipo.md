# División de trabajo — Dos desarrolladores

> Estrategia para que dos personas trabajen en paralelo sin pisarse el código.

---

## Principios

1. **Cada desarrollador trabaja en apps distintas** — no tocan los mismos archivos
2. **La infraestructura base la hace una sola persona** (no se puede paralelizar)
3. **Lo que ambas necesitan** (permisos, URLs, settings) lo establece el Developer A primero, y Developer B lo usa
4. **Los tests de cada uno son independientes**
5. **Operativos se hace después**, cuando ambas tracks estén listas

---

## Timeline

```
Semana 1                    Semana 2                    Semana 3
├── Infraestructura (A) ────┤                            │
│                           ├── Tutor+Consent (A) ───────┤
│                           │                            │
├── Escuelas (B) ───────────┤                            │
│                           ├── Merge A+B                ├── Operativos (A+B)
```

---

## Sistema de permisos (data-driven)

Ambos developers usan `require_action('nombreAccion')` de `apps.usuarios.permissions`. Las acciones se definen en fixtures JSON y se cargan con `seed_all`. No hay permisos hardcodeados en código.

Ver `plan-implementacion.md` para la especificación completa.

---

## Developer A — Infraestructura + permisos + tutor

### Track A: Apps que toca

| App | Archivos |
|-----|----------|
| `apps.usuarios` | models (Action, RoleAction), permissions (require_action), action_resolution (ActionPermissionBackend + effective_actions), views (login/refresh/logout/me), urls, fixtures, management commands |
| `apps.tutores` | views (register + alumnos), urls |
| `config/` | settings/base.py (AUTHENTICATION_BACKENDS, CORS, SECRET_KEY), urls.py |
| `requirements/common.txt` | + django-cors-headers |
| `.env.example` | nuevo |

### Paso A1 — Infraestructura + permisos data-driven

```
Archivos:
  requirements/common.txt          + django-cors-headers
  .env.example                     nuevo
  config/settings/base.py          fix SECRET_KEY, CORS, AUTHENTICATION_BACKENDS
  apps/usuarios/models/action.py   Action, RoleAction (managed=True)
  apps/usuarios/permissions.py     require_action(action_name) → DRF permission class
  apps/usuarios/action_resolution  ActionPermissionBackend + effective_actions()
  apps/usuarios/views.py           LoginView, RefreshView, LogoutView, MeView
  apps/usuarios/urls.py            /auth/login/, /auth/refresh/, /auth/logout/, /auth/me/
  apps/usuarios/fixtures/          actions.json, roles.json, role_actions.json
  apps/usuarios/management/        seed_all.py
  config/urls.py                   path('api/v1/', include('apps.usuarios.urls'))
```

| Sub-paso | Qué hace | Test |
|----------|----------|------|
| A1.1 | CORS + .env.example + fix SECRET_KEY | `python manage.py check` |
| A1.2 | Modelos Action + RoleAction (data-driven) | Migraciones |
| A1.3 | ActionPermissionBackend + effective_actions + require_action | `test apps.usuarios.tests.PermissionTest` |
| A1.4 | Endpoints JWT (login, refresh, logout, me con effective_actions) | `test apps.usuarios.tests.AuthAPITest` |
| A1.5 | Fixtures + seed_all command | `seed_all` + shell |

**Developer B no toca nada de esto.**

### Paso A2 — Registro de tutor + alumnos

```
Archivos:
  apps/tutores/views.py            RegisterTutorView, TutorAlumnosView
  apps/tutores/urls.py             /auth/register/tutor/, /tutores/{id}/alumnos/
  config/urls.py                   + include('apps.tutores.urls')
```

| Sub-paso | Qué hace | Test |
|----------|----------|------|
| A2.1 | `POST /auth/register/tutor/` — crea Persona + Usuario + Tutor + devuelve JWT | API test |
| A2.2 | `POST /tutores/{id}/alumnos/` — crea Persona + Paciente vinculado al tutor | API test |
| A2.3 | `GET /tutores/{id}/alumnos/` — lista alumnos del tutor | API test |

---

## Developer B — Escuelas + Curso

### Track B: Apps que toca

| App | Archivos |
|-----|----------|
| `apps.escuelas` | models (fix Escuela + nuevo Curso), serializers, views, urls |

### Paso B1 — Fix Escuela + Curso

```
Archivos:
  apps/escuelas/models/escuela.py  agregar cue, domicilio FK, telefono, activa
  apps/escuelas/models/curso.py    nuevo modelo
  apps/escuelas/serializers.py     EscuelaSerializer, EscuelaListSerializer, CursoSerializer
  apps/escuelas/admin.py           mejorado
```

| Sub-paso | Qué hace | Test |
|----------|----------|------|
| B1.1 | Agregar campos a Escuela: `cue`, `domicilio` (FK a personas.Domicilio), `telefono`, `activa` | `makemigrations` + `migrate` |
| B1.2 | Crear modelo `Curso` con FK a Escuela | Migraciones |
| B1.3 | Serializers (EscuelaSerializer con Domicilio anidado, EscuelaListSerializer con localidad) | Shell test |
| B1.4 | Admin mejorado para Escuela + Curso | Admin |

### Paso B2 — Endpoints CRUD Escuelas

```
Archivos:
  apps/escuelas/views.py           EscuelaListCreateView, EscuelaDetailView
                                   CursoListCreateView, CursoDetailView
  apps/escuelas/urls.py            rutas /escuelas/, /escuelas/{id}/cursos/
  config/urls.py                   + path('api/v1/escuelas/', include('apps.escuelas.urls'))
```

| Sub-paso | Qué hace | Test |
|----------|----------|------|
| B2.1 | EscuelaListCreateView + EscuelaDetailView con APIView + require_action | API test |
| B2.2 | CursoListCreateView + CursoDetailView (anidados a escuela) | API test |
| B2.3 | URLs + registro en config/urls.py | API test |

**Lo que necesita de A:** El sistema de permisos (`require_action`) ya debe existir. Las acciones de escuelas (`verEscuelas`, `crearEscuela`, etc.) están en fixtures desde A1.5. B solo las importa y usa.

⚠️ **Importante:** B debe esperar a que A termine el paso A1 (permisos + fixtures) antes de codificar las views, porque necesita `require_action` y las acciones seedeadas.

---

## Puntos de integración

| Archivo | Lo pone A | Lo extiende B |
|---------|-----------|---------------|
| `config/urls.py` | `path('api/v1/', include('apps.usuarios.urls'))` | + `path('api/v1/escuelas/', include('apps.escuelas.urls'))` |
| `config/settings/base.py` | CORS, AUTHENTICATION_BACKENDS | — (ya está `apps.escuelas` en INSTALLED_APPS) |
| `apps/usuarios/fixtures/actions.json` | Acciones de auth + escuelas + operativos | B solo las usa |

---

## Después del merge — Operativos

Cuando A terminó Track A y B terminó Track B, se mergea todo y se construye Operativos:

| Paso | Qué hace | Depende de | Quién |
|------|----------|------------|-------|
| Merge | Unificar ambos tracks | A y B completos | — |
| 10 | Modelos Operativo, OperativoProfesional, OperativoAlumno | Escuelas, Pacientes | A/B |
| 11 | Admin de operativos | Modelos | A/B |
| 12 | Servicios: crear, confirmar, cancelar, finalizar, CSV | Modelos | A/B |
| 13 | Serializers | Modelos | A/B |
| 14 | Endpoints CRUD + acciones + profesionales + alumnos + CSV | Servicios | A/B |

---

## Resumen de no pisarse

| Lo que SOLO toca A | Lo que SOLO toca B | Lo que tocan ambos (secuencial) |
|--------------------|--------------------|----------------------------------|
| `apps/usuarios/permissions.py` | `apps/escuelas/models/escuela.py` | `config/urls.py` (A primero, B después) |
| `apps/usuarios/action_resolution.py` | `apps/escuelas/models/curso.py` | |
| `apps/usuarios/models/action.py` | `apps/escuelas/views.py` | |
| `apps/usuarios/views.py` | `apps/escuelas/urls.py` | |
| `apps/usuarios/urls.py` | `apps/escuelas/serializers.py` | |
| `apps/usuarios/fixtures/` | `apps/escuelas/admin.py` | |
| `apps/usuarios/management/` | | |
| `apps/tutores/views.py` | | |
| `apps/tutores/urls.py` | | |
| `requirements/common.txt` | | |
| `.env.example` | | |
| `config/settings/base.py` (AUTHENTICATION_BACKENDS) | | |

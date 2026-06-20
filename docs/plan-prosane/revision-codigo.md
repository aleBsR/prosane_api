# Revisión de código — prosane_api (rama ale-base)

> **Rama:** `ale-base` (origin/base)
> **Propósito:** Identificar lo que ya existe vs. lo que falta construir.

---

## Lo que ya existe y está OK ✅

### Models
| App | Modelos | Estado |
|-----|---------|--------|
| `apps.personas` | Persona, Domicilio | ✅ Completos |
| `apps.usuarios` | Usuario (AbstractBaseUser+JWT), Rol, RoleUsuario | ✅ Completos |
| `apps.tutores` | Tutor | ✅ Completo |
| `apps.pacientes` | Paciente | ✅ Completo |
| `apps.antecedentes` | AntecedenteFamiliar, AntecedentePersonal | ✅ Completos |
| `apps.vacunas` | Vacuna, CarnetVacuna | ✅ Completos |
| `apps.profesionales` | Profesional | ✅ Completo |
| `apps.escuelas` | Escuela (incompleto), ObservacionEscuela | ⚠️ Parcial |
| `common` | BaseModel, AuditModel | ✅ Completos |

### Serializers
- Todas las apps tienen serializers básicos (`fields = '__all__'`) ✅

### Settings
- JWT configurado (simplejwt) ✅
- DRF configurado (IsAuthenticated default) ✅
- base.py / local.py / test.py / production.py ✅
- PostgreSQL via .env ✅

---

## Lo que hay que construir/modificar 🛠️

### Infraestructura
| Ítem | Dónde | Prioridad |
|------|-------|-----------|
| django-cors-headers | requirements + settings | Alta |
| .env.example | raíz del proyecto | Alta |
| Fix SECRET_KEY sin fallback | settings/base.py | Alta |

### Permisos (no existe nada)
| Ítem | Archivo |
|------|---------|
| Modelo Action | `apps/usuarios/models/action.py` |
| Modelo RoleAction | `apps/usuarios/models/action.py` |
| `require_action` permission class | `apps/usuarios/permissions.py` |

### Auth endpoints (no existe nada)
| Ítem | Archivo |
|------|---------|
| LoginView | `apps/usuarios/views.py` |
| RefreshView | `apps/usuarios/views.py` |
| LogoutView | `apps/usuarios/views.py` |
| MeView | `apps/usuarios/views.py` |
| URLs de auth | `apps/usuarios/urls.py` |

### Escuelas (mejora)
| Ítem | Cambio |
|------|--------|
| Escuela.cue | Agregar campo varchar(20) unique |
| Escuela.domicilio | FK a `personas.Domicilio` |
| Escuela.telefono | Agregar varchar(20) |
| Escuela.activa | Agregar bool default True |
| Curso | Modelo nuevo (FK a Escuela) |
| Serializers específicos | Reemplazar `__all__` |
| Views CRUD + URLs | Nuevo (usando APIView) |

### Operativos (nuevo)
| Ítem | Archivo |
|------|---------|
| App `apps.operativos` | `apps/operativos/` |
| Operativo model | `apps/operativos/models/operativo.py` |
| OperativoProfesional model | `apps/operativos/models/profesional.py` |
| OperativoAlumno model | `apps/operativos/models/alumno.py` |
| Admin | `apps/operativos/admin.py` |
| Services | `apps/operativos/services.py` |
| Serializers | `apps/operativos/serializers.py` |
| Views + URLs | `apps/operativos/views.py`, `apps/operativos/urls.py` |

### Seeds / Fixtures (no existe nada)
| Ítem | Archivo |
|------|---------|
| actions.json | `apps/usuarios/fixtures/actions.json` |
| seed_all command | `apps/usuarios/management/commands/seed_all.py` |

### Dead code (root-level)
| Directorio | Contenido | Acción |
|------------|-----------|--------|
| `authentication/` | Solo pycache | ❌ No está en INSTALLED_APPS |
| `core/` | Solo pycache | ❌ No está en INSTALLED_APPS |
| `health/` | Solo pycache | ❌ No está en INSTALLED_APPS |
| `patients/` | Solo pycache | ❌ No está en INSTALLED_APPS |
| `professionals/` | Solo pycache | ❌ No está en INSTALLED_APPS |

Ninguno está registrado en INSTALLED_APPS. Son carpetas abandonadas de desarrollo anterior. No interfieren pero se pueden eliminar.

---

## Resumen de acciones

| Prioridad | Acción | Pasos |
|-----------|--------|-------|
| 🔴 Alta | CORS + .env.example + SECRET_KEY fix | Paso 01 |
| 🔴 Alta | Permission system (Action, require_action) | Paso 02 |
| 🔴 Alta | JWT endpoints (login, refresh, logout, me) | Paso 03 |
| 🔴 Alta | Seeds de roles y acciones | Paso 04 |
| 🟡 Media | Fix Escuela + Curso model | Paso 05 |
| 🟡 Media | Serializers de escuelas | Paso 06 |
| 🟡 Media | Endpoints CRUD escuelas | Paso 07 |
| 🟢 Baja | Modelos de operativos | Paso 08 |
| 🟢 Baja | Admin de operativos | Paso 09 |
| 🟢 Baja | Servicios de operativos | Paso 10 |
| 🟢 Baja | Serializers de operativos | Paso 11 |
| 🟢 Baja | Endpoints + tests de operativos | Paso 12 |

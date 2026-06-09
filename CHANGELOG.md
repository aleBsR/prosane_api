# Changelog — PROSANE API

> Sesión: 06-08/06/2026  
> Rama: `rama-dev` → `dev`

---

## 1. Auditoría — `common` app

### Agregado

| Archivo | Descripción |
|---|---|
| `common/models.py` | `AuditModel` (created_at, updated_at, created_by, updated_by, deleted_at, soft delete) + `BaseModel` (UUID PK + AuditModel) |
| `common/models.py` | Campos `created_year` (INT), `created_year_month` (VARCHAR), `updated_year` (INT), `updated_year_month` (VARCHAR) con auto-población en `save()` |
| `common/serializers.py` | `AuditSerializerMixin` — sella `created_by`/`updated_by` desde `request.user`, anti-spoofing |
| `common/mixins.py` | `AuditViewMixin` — para vistas CBV, sella actor en `perform_create()`/`perform_update()` |
| `common/managers.py` | `SoftDeleteManager` — `.all()` oculta borrados; `.alive()`/`.dead()`/`.hard_delete()` |
| `common/tests/` | 17 tests unitarios para modelos, mixins y soft delete |

### Migración masiva a `BaseModel` (10 tablas)

Todas las tablas pasaron de PK `integer` a PK `UUID`, con columnas de auditoría y soft delete:

| Tabla | PK antes | PK ahora | Audit | FK migradas |
|---|---|---|---|---|
| `matriculas` | int | UUID | ✅ | — (standalone) |
| `domicilio` | int | UUID | ✅ | `pacientes.id_domicilio` |
| `personas` | int | UUID | ✅ | `usuarios.id_persona`, `pacientes.id_persona`, `responsables.id_persona` |
| `responsables` | int | UUID | ✅ | `pacientes.id_responsable` |
| `profesionales` | int | UUID | ✅ | — |
| `pacientes` | int | UUID | ✅ | `antecedentesfamiliares.id_paciente`, `antecedentespersonales.id_paciente` |
| `antecedentesfamiliares` | int | UUID | ✅ | — |
| `antecedentespersonales` | int (id_antecedente) | UUID | ✅ | — |
| `roles` | int | UUID | ✅ | `user_role.id_rol` |
| `user_role` | AutoField | UUID | ✅ | — |

### Integración en `Pacientes`

| Capa | Cambio |
|---|---|
| Modelo | `Pacientes(BaseModel)` |
| Serializer | `PacientesSerializer(AuditSerializerMixin, ModelSerializer)` + `_actor()` en `create()` y `update()` |
| Vistas | `context={'request': request}` pasado al serializer para que el mixin lea `request.user` |

---

## 2. Sistema de registros

### Registro de tutor (`POST /auth/register-tutor/`)

- Nuevo: `RegisterTutorSerializer` — anida `UserSerializer` + `parentesco`
- Crea `Personas` → `Usuarios` (rol `tutor`) → `Responsables(usuario, persona, parentesco)` en una sola transacción
- Body: `{parentesco, usuario: {email, password, persona: {nombre, apellido, dni, sexo, fecha_nacimiento}}}`

### Registro de profesional (`POST /auth/register-profesional/`)

- Nuevo: `RegisterProfesionalSerializer` — valida matrícula contra `RefepsService`
- Obtiene datos de persona del mock REFEPS (nombre, apellido, dni, sexo, fecha_nacimiento)
- Crea `Personas` + `Usuarios` (rol `medico`/`odontologo` según profesión) + `Profesionales`
- Body: `{email, password, matricula}`
- Mock: `REFEPS_MOCK = True` en `settings/base.py`

### Registro genérico (`POST /auth/register/`)

- Usa `UserSerializer` con `context={'rol': 'usuario'}` por defecto
- Rol asignado via `self.context.get('rol', 'usuario')` en `UserSerializer.create()`

### Patrón de diseño aplicado

- **Strategy**: `RefepsService.consultar()` — mock vs API real mediante feature toggle `REFEPS_MOCK`
- **Template Method**: `UserSerializer.create()` — rol definido por `context`, no hardcodeado
- **Composite**: `RegisterTutorSerializer` anida `UserSerializer`
- **Thin View**: Todas las vistas de registro son 5 líneas (validar → save → response)

---

## 3. Permisos

### Agregados

| Clase | Hereda de | Verifica |
|---|---|---|
| `EsTutor` | `TieneRol` | `rol == 'tutor'` en token |
| `EsAyudante` | `TieneRol` | `rol == 'ayudante'` en token |
| `EsProfesional` | `IsAuthenticated` | `rol in ('medico', 'odontologo')` en token |

### Roles en DB

| rol | ruta |
|---|---|
| usuario | /home |
| medico | /home/medico |
| odontologo | /home/odontologo |
| tutor | /home/tutor |
| ayudante | /home/ayudante |

---

## 4. Fixes de seguridad y bugs

### Vistas públicas — doble decorador

Todas las vistas públicas (`register`, `login`, `register_tutor`, `register_profesional`) tienen:
```python
@permission_classes([AllowAny])
@authentication_classes([])
```
`AllowAny` solo no alcanza — `JWTAuthentication` global rechaza tokens inválidos antes del chequeo de permisos.

### Patients endpoints

| Fix | Archivo | Cambio |
|---|---|---|
| Crash: `crear_paciente` no existía | `patients/urls.py` | Eliminada la importación y ruta |
| Runtime: `id_responsable` → `responsable` | `patients/serializers.py:98` | Atributo renombrado en el modelo |
| Seguridad: anónimos veían todos los pacientes | `patients/views.py` | `permission_classes = [IsAuthenticated]` |
| Query: `.get(persona=persona)` → `.get(usuario=request.user)` | `patients/views.py` | Evita `MultipleObjectsReturned` |
| URL: `<int:pk>` con UUIDs | `patients/urls.py` | Cambiado a `<uuid:pk>` |
| `__all__` en serializers de antecedentes | `patients/serializers.py` | Lista explícita de fields |
| `ResponsablesSerializer` sin campo `persona` | `patients/serializers.py` | Agregado a fields |

### Profesionales endpoints

| Fix | Archivo | Cambio |
|---|---|---|
| Permisos: solo `IsAuthenticated` | `professionals/views.py` | `IsAuthenticated` → `EsProfesional` |
| Redundancia: `RefepsService.consultar()` 2 veces | `professionals/serializers.py` | Guarda resultado en `self.context['datos_refeps']` |
| Tutor podía validar matrículas | `professionals/views.py` | Ahora 403 |

---

## 5. Documentación

### AGENTS.md

Actualizado con:
- Comando de tests: `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test`
- Arquitectura con `common/` y `patients/`
- DER: referencia a `.der/Prosane_der.architect` con 25 tablas y alcance Fase 1
- Endpoints actuales y futuros

### Reportes generados

| Archivo | Contenido |
|---|---|
| `INFORME_IMPLEMENTACION.md` | Flujo de registros, patrones de diseño, guía para futuros endpoints |
| `INFORME_REVISION_TEAMATE.md` | Revisión de código del teammate en `patients/` |
| `ANALISIS_CONFLICTOS_PR2.md` | Análisis de conflictos de la PR `feat/audit-base-model` |

### apidocs (de teammate)

- App `apidocs` con 18 páginas HTML en `/docs/`
- Skill `.opencode/skills/prosane-api-conventions/SKILL.md`

---

## 6. Modelos — cambios estructurales

### `Responsables`

- Agregado `persona` FK (nullable) — para auto-link tutor-paciente por DNI cuando el tutor no tiene cuenta
- Agregado `usuario` FK (nullable) — para cuando el tutor se registra
- Ambas columnas pueden ser null → soporta el flujo "médico crea paciente, tutor se registra después"

### `Personas`

- Agregados `sexo` y `fecha_nacimiento` (requeridos en registro)

### `Pacientes`

- `id_responsable` → nullable (para pacientes creados por médico sin tutor asignado)

### Antecedentes

- FK renombradas: `id_paciente` → `paciente`, `id_antecedente` → `antecedente` (atributo Python)
- `db_column` preserva nombres físicos en DB

---

## 7. Servicios

| Archivo | Descripción |
|---|---|
| `professionals/services/services_refeps.py` | `RefepsService.consultar()` — mock con feature toggle `REFEPS_MOCK` |
| `config/settings/base.py:171` | `REFEPS_MOCK = True` |

Matrículas mock:
- `541012497922` → Estela Rosa Acevedo (Médico)
- `123456789` → Carlos López (Odontólogo)

---

## 8. Tests

| Comando | Resultado |
|---|---|
| `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test common` | 17 tests OK |
| `python manage.py check` | 0 issues |

---

## 9. Endpoints actuales

| Método | URL | Permiso | Estado |
|---|---|---|---|
| `POST` | `/auth/register/` | Public | ✅ |
| `POST` | `/auth/register-tutor/` | Public | ✅ |
| `POST` | `/auth/register-profesional/` | Public | ✅ |
| `POST` | `/auth/login/` | Public | ✅ |
| `POST` | `/auth/rol/<id>` | `EsAdmin` | ✅ |
| `GET` | `/auth/medico/` | `EsMedico` | ✅ |
| `GET` | `/api/v1/` | `IsAuthenticated` | ✅ Lista pacientes del tutor |
| `POST` | `/api/v1/` | `IsAuthenticated` | ✅ Crea paciente (auto-link tutor) |
| `GET` | `/api/v1/<uuid:pk>/` | `IsAuthenticated` | ✅ |
| `PUT` | `/api/v1/<uuid:pk>/` | `IsAuthenticated` | ✅ |
| `PATCH` | `/api/v1/<uuid:pk>/` | `IsAuthenticated` | ✅ |
| `DELETE` | `/api/v1/<uuid:pk>/` | `IsAuthenticated` | ✅ |
| `GET` | `/api/v1/<uuid:patient_id>/antecedentes-familiares/` | `IsAuthenticated` | ✅ |
| `PUT` | `/api/v1/<uuid:patient_id>/antecedentes-familiares/` | `IsAuthenticated` | ✅ |
| `GET` | `/api/v1/<uuid:patient_id>/antecedentes-personales/` | `IsAuthenticated` | ✅ |
| `PUT` | `/api/v1/<uuid:patient_id>/antecedentes-personales/` | `IsAuthenticated` | ✅ |
| `GET` | `/api/v1/responsable/` | `IsAuthenticated` | ✅ |
| `PUT` | `/api/v1/responsable/` | `IsAuthenticated` | ✅ |
| `GET` | `/api/v1/profesionales/perfil/` | `EsProfesional` | ✅ |
| `PUT` | `/api/v1/profesionales/perfil/` | `EsProfesional` | ✅ |
| `POST` | `/api/v1/profesionales/validar-matricula/` | `EsProfesional` | ✅ |
| `GET` | `/docs/` | Public | ✅ Documentación interactiva |

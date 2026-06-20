# Plan de implementación — PROSANE API (ale-base)

> Basado en el sistema de permisos data-driven de `ale-dev`.
> Cada paso es testeable antes de pasar al siguiente.

---

## Estado actual de ale-base

| App | Modelos | Serializers | Views | Endpoints |
|-----|---------|-------------|-------|-----------|
| `apps.usuarios` | Usuario, Rol, RoleUsuario | ✅ básicos | ❌ | ❌ |
| `apps.personas` | Persona, Domicilio | ✅ básicos | ❌ | ❌ |
| `apps.pacientes` | Paciente | ✅ básicos | ❌ | ❌ |
| `apps.tutores` | Tutor | ✅ básicos | ❌ | ❌ |
| `apps.antecedentes` | AntecedenteFamiliar, Personal | ✅ básicos | ❌ | ❌ |
| `apps.vacunas` | Vacuna, CarnetVacuna | ✅ básicos | ❌ | ❌ |
| `apps.profesionales` | Profesional | ✅ básicos | ❌ | ❌ |
| `apps.escuelas` | Escuela (incompleta), ObsEscuela | ✅ básicos | ❌ | ❌ |
| `common` | BaseModel, AuditModel | — | — | — |
| `config` | JWT config, DRF config | — | — | — |

**No existe nada de:** permisos data-driven, endpoints, fixtures, seeds, Curso, Operativos.

---

## Sistema de permisos (data-driven)

Inspirado en `ale-dev`, simplificado:

### Modelos

```python
class Action(BaseModel):
    name = models.CharField(max_length=100, unique=True)       # 'crearOperativo'
    label = models.CharField(max_length=200)                    # 'Crear operativo'
    type = models.CharField(max_length=20, default='crud')      # crud / action
    category = models.CharField(max_length=50, blank=True)      # escuelas / operativos
    is_sensitive = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

class RoleAction(BaseModel):
    role = models.ForeignKey(Rol, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    unique_together = (role, action)
```

### Backend de resolución

```python
class ActionPermissionBackend(BaseBackend):
    def has_perm(self, user_obj, perm):
        return perm in self.get_all_permissions(user_obj)

    def get_all_permissions(self, user_obj):
        if user_obj.is_superuser:
            return set(Action.objects.filter(is_active=True).values_list('name', flat=True))
        return set(RoleAction.objects.filter(
            role__roleusuario__id_user=user_obj,
            action__is_active=True,
        ).values_list('action__name', flat=True))
```

### require_action (factory)

```python
def require_action(action_name):
    class RequireAction(BasePermission):
        def has_permission(self, request, view):
            return request.user.has_perm(action_name)
    return RequireAction
```

### effective_actions (para el endpoint /me)

```python
def effective_actions(user):
    """Retorna lista de acciones efectivas del usuario (para cache del frontend)."""
    if user.is_superuser:
        qs = Action.objects.filter(is_active=True)
    else:
        qs = Action.objects.filter(
            role_actions__role__roleusuario__id_user=user,
            is_active=True,
        ).distinct()
    return qs.values('name', 'label', 'type', 'category', 'is_sensitive', 'sort_order')
```

### Uso en views

```python
# Estático
class MiView(APIView):
    permission_classes = [require_action('verOperativo')]

# Dinámico (por método HTTP)
class MiView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [require_action('crearOperativo')()]
        return [require_action('verOperativo')()]
```

---

## Primera etapa

### Módulo 1: Infraestructura + permisos

| Paso | Archivos | Qué hace | Test |
|------|----------|----------|------|
| **01** | `requirements/common.txt`, `.env.example`, `config/settings/base.py` | CORS + .env.example + fix SECRET_KEY + registro AUTHENTICATION_BACKENDS | `python manage.py check` |
| **02** | `apps/usuarios/models/action.py`, `apps/usuarios/permissions.py`, `apps/usuarios/action_resolution.py` | Modelos Action + RoleAction + ActionPermissionBackend + require_action + effective_actions | `test apps.usuarios.tests.PermissionTest` |
| **03** | `apps/usuarios/views.py`, `apps/usuarios/urls.py`, `config/urls.py` | LoginView, RefreshView, LogoutView, MeView (con effective_actions en /me) | `test apps.usuarios.tests.AuthAPITest` |
| **04** | `apps/usuarios/fixtures/actions.json`, `apps/usuarios/fixtures/roles.json`, `apps/usuarios/fixtures/role_actions.json`, `apps/usuarios/management/commands/seed_all.py` | Fixtures de roles + acciones + command seed_all | `seed_all` + shell |

### Módulo 2: Tutor

| Paso | Archivos | Qué hace | Test |
|------|----------|----------|------|
| **05** | `apps/tutores/views.py`, `apps/tutores/urls.py` | POST /auth/register/tutor/ (crea Persona + Usuario + Tutor + JWT) | API test |
| **06** | `apps/tutores/views.py` | POST /tutores/{id}/alumnos/ (crea Persona + Paciente vinculado) + GET listado | API test |

### Módulo 3: Escuelas

| Paso | Archivos | Qué hace | Test |
|------|----------|----------|------|
| **07** | `apps/escuelas/models/escuela.py`, `apps/escuelas/models/curso.py` | Fix Escuela (CUE, domicilio, telefono, activa) + Curso model | Migraciones |
| **08** | `apps/escuelas/serializers.py` | EscuelaSerializer, EscuelaListSerializer, CursoSerializer | Shell test |
| **09** | `apps/escuelas/views.py`, `apps/escuelas/urls.py` | CRUD Escuela + Curso con APIView + permisos data-driven | API tests |

### Módulo 4: Operativos

| Paso | Archivos | Qué hace | Test |
|------|----------|----------|------|
| **10** | `apps/operativos/models/` | Operativo, OperativoProfesional, OperativoAlumno | Migraciones |
| **11** | `apps/operativos/admin.py` | Admin + data de prueba | Admin |
| **12** | `apps/operativos/services.py` | Servicios: crear, confirmar, finalizar, cancelar, asignar profesional, conflicto fecha, importar CSV | Unit tests |
| **13** | `apps/operativos/serializers.py` | Serializers de operativos | Shell test |
| **14** | `apps/operativos/views.py`, `apps/operativos/urls.py` | Endpoints CRUD + acciones + profesionales + alumnos + CSV con permisos data-driven | API tests |

---

## División para dos desarrolladores

### Developer A — Módulos 1 + 2 (infra, permisos, tutor)

| Orden | Paso | App |
|-------|------|-----|
| 1 | 01-04 | Infraestructura + permisos + seeds |
| 2 | 05-06 | Tutor endpoints |

### Developer B — Módulo 3 (escuelas)

| Orden | Paso | App |
|-------|------|-----|
| 1 | 07-09 | Escuela fix + Curso + CRUD |

**Punto de integración:** Developer A termina 01-04 primero. Developer B usa `require_action` de A. Las acciones de escuelas están en los fixtures desde el paso 04.

### Después del merge

| Orden | Paso | Quién |
|-------|------|-------|
| 3 | 10-14 | A, B, o ambos — Operativos completo |

---

## Convenciones

- **Modelos nuevos**: heredan de `common.models.BaseModel`
- **Views**: `APIView` (DRF base class), no generic views
- **Permisos**: `require_action('nombreAccion')` — **data-driven** (viven en DB)
- **Resolver**: `ActionPermissionBackend` registrado en `AUTHENTICATION_BACKENDS`
- **Frontend**: endpoint `/me` devuelve `effective_actions` para cache local
- **Tests**: `python manage.py test apps.<app>` — cada paso antes del siguiente
- **Commits**: uno por paso, mensaje tipo `feat(permisos): data-driven Action + RoleAction + require_action`

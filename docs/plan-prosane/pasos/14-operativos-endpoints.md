# Paso 14: Endpoints de operativos

## Objetivo

Exponer todas las operaciones de operativos vía API REST con permisos.

## 1. Views

**Archivo:** `apps/operativos/views.py`

### Operativos CRUD

| View | Métodos | Ruta |
|------|---------|------|
| `OperativoListCreateView` | GET, POST | `/api/v1/operativos/` |
| `OperativoDetailView` | GET, PUT, PATCH, DELETE | `/api/v1/operativos/{id}/` |

### Acciones de estado

| View | Método | Ruta |
|------|--------|------|
| `OperativoConfirmarView` | POST | `/api/v1/operativos/{id}/confirmar/` |
| `OperativoFinalizarView` | POST | `/api/v1/operativos/{id}/finalizar/` |
| `OperativoCancelarView` | POST | `/api/v1/operativos/{id}/cancelar/` |

### Profesionales

| View | Métodos | Ruta |
|------|---------|------|
| `OperativoProfesionalListView` | GET | `/api/v1/operativos/{id}/profesionales/` |
| `OperativoProfesionalAssignView` | POST | `/api/v1/operativos/{id}/profesionales/asignar/` |
| `OperativoProfesionalRemoveView` | DELETE | `/api/v1/operativos/{id}/profesionales/{id}/remover/` |

### Alumnos

| View | Métodos | Ruta |
|------|---------|------|
| `OperativoAlumnoListCreateView` | GET, POST | `/api/v1/operativos/{id}/alumnos/` |
| `OperativoAlumnoDetailView` | GET, PATCH, DELETE | `/api/v1/operativos/{id}/alumnos/{id}/` |
| `OperativoAlumnoImportCSVView` | POST | `/api/v1/operativos/{id}/alumnos/importar-csv/` |

## 2. URLs

**Archivo:** `apps/operativos/urls.py`
```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.OperativoListCreateView.as_view(), name='operativo-list-create'),
    path('<uuid:pk>/', views.OperativoDetailView.as_view(), name='operativo-detail'),
    path('<uuid:pk>/confirmar/', views.OperativoConfirmarView.as_view(), name='operativo-confirmar'),
    path('<uuid:pk>/finalizar/', views.OperativoFinalizarView.as_view(), name='operativo-finalizar'),
    path('<uuid:pk>/cancelar/', views.OperativoCancelarView.as_view(), name='operativo-cancelar'),
    path('<uuid:pk>/profesionales/', views.OperativoProfesionalListView.as_view(), name='operativo-profesional-list'),
    path('<uuid:pk>/profesionales/asignar/', views.OperativoProfesionalAssignView.as_view(), name='operativo-profesional-assign'),
    path('<uuid:pk>/profesionales/<uuid:prof_pk>/remover/', views.OperativoProfesionalRemoveView.as_view(), name='operativo-profesional-remove'),
    path('<uuid:pk>/alumnos/', views.OperativoAlumnoListCreateView.as_view(), name='operativo-alumno-list-create'),
    path('<uuid:pk>/alumnos/importar-csv/', views.OperativoAlumnoImportCSVView.as_view(), name='operativo-alumno-import-csv'),
    path('<uuid:pk>/alumnos/<uuid:alumno_pk>/', views.OperativoAlumnoDetailView.as_view(), name='operativo-alumno-detail'),
]
```

**Archivo:** `config/urls.py`
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.usuarios.urls')),
    path('api/v1/escuelas/', include('apps.escuelas.urls')),
    path('api/v1/operativos/', include('apps.operativos.urls')),
]
```

## 3. Tests de integración

```bash
python manage.py test apps.operativos.tests
```

## Criterio de aceptación

- `GET /api/v1/operativos/` → lista con filtros (`?escuela_id=`, `?fecha=`, `?estado=`)
- `POST /api/v1/operativos/` → crea (201)
- `GET/PUT/PATCH/DELETE /api/v1/operativos/{id}/` → CRUD completo
- `POST .../confirmar/` → confirma (200) o 409 si no cumple condiciones
- `POST .../cancelar/` → cancela (200)
- `POST .../finalizar/` → finaliza (200)
- `GET .../profesionales/` → lista (200)
- `POST .../profesionales/asignar/` → asigna (201) o 409 si conflicto fecha
- `DELETE .../profesionales/{id}/remover/` → remueve (204)
- `GET .../alumnos/` → lista con filtro `?estado=`
- `POST .../alumnos/importar-csv/` → importa y devuelve resumen
- `PATCH .../alumnos/{id}/` → cambia estado (presente/ausente)
- Filtro por rol: médico/odontólogo solo ven sus operativos asignados, ayudante ve los propios
- Todos los tests pasan

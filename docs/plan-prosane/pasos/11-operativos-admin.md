# Paso 11: Admin + data de prueba para operativos

## Objetivo

Poder crear y gestionar operativos desde el panel de Django admin.

## 1. Admin

**Archivo:** `apps/operativos/admin.py`
```python
from django.contrib import admin
from .models import Operativo, OperativoProfesional, OperativoAlumno


class OperativoProfesionalInline(admin.TabularInline):
    model = OperativoProfesional
    extra = 1
    autocomplete_fields = ['profesional']


class OperativoAlumnoInline(admin.TabularInline):
    model = OperativoAlumno
    extra = 0
    readonly_fields = ['apellido', 'nombre', 'dni', 'tipo_dni']
    can_delete = True


@admin.register(Operativo)
class OperativoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'escuela', 'fecha', 'estado']
    list_filter = ['estado', 'fecha']
    search_fields = ['nombre', 'escuela__nombre', 'notas']
    date_hierarchy = 'fecha'
    inlines = [OperativoProfesionalInline, OperativoAlumnoInline]
    autocomplete_fields = ['escuela']
    readonly_fields = ['created_by']


@admin.register(OperativoProfesional)
class OperativoProfesionalAdmin(admin.ModelAdmin):
    list_display = ['operativo', 'profesional', 'rol_en_operativo', 'confirmado']
    list_filter = ['rol_en_operativo', 'confirmado']


@admin.register(OperativoAlumno)
class OperativoAlumnoAdmin(admin.ModelAdmin):
    list_display = ['apellido', 'nombre', 'dni', 'operativo', 'estado']
    list_filter = ['estado']
    search_fields = ['apellido', 'nombre', 'dni']
```

## 2. Data de prueba

```bash
python manage.py shell << 'EOF'
from django.utils import timezone
from apps.escuelas.models import Escuela, Curso
from apps.operativos.models import Operativo, OperativoAlumno

escuela, _ = Escuela.objects.get_or_create(
    nombre='Escuela de Prueba',
    defaults={'cue': 'TEST001'},
)
op = Operativo.objects.create(
    nombre='Operativo de prueba',
    escuela=escuela,
    fecha=timezone.now().date(),
)
for ape, nom, dni in [
    ('García', 'Juan', '12345678'),
    ('Pérez', 'María', '23456789'),
]:
    OperativoAlumno.objects.create(
        operativo=op, apellido=ape, nombre=nom, dni=dni,
    )
print(f'OK: {op} con {op.alumnos.count()} alumnos')
EOF
```

## 3. Probar

```bash
python manage.py runserver
```

Ir a `http://127.0.0.1:8000/admin/operativos/` y verificar.

## Criterio de aceptación

- Los 3 modelos aparecen en `/admin`
- Se puede crear un operativo con alumnos desde el admin
- Inlines funcionan (alumnos editables desde el operativo)
- Data de prueba visible

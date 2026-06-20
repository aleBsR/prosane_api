# Paso 04: Seeds de roles + acciones

## Objetivo

Crear fixtures de acciones y roles, y un management command `seed_all` para cargarlos.

## 1. Fixtures

**Archivo:** `apps/usuarios/fixtures/actions.json`
Cada acción que vamos a usar en el sistema.
```json
[
  {"model": "usuarios.action", "fields": {"name": "crearEscuela", "label": "Crear escuela", "type": "crud", "category": "escuelas", "sort_order": 10}},
  {"model": "usuarios.action", "fields": {"name": "verEscuelas", "label": "Ver escuelas", "type": "crud", "category": "escuelas", "sort_order": 11}},
  {"model": "usuarios.action", "fields": {"name": "editarEscuela", "label": "Editar escuela", "type": "crud", "category": "escuelas", "sort_order": 12}},
  {"model": "usuarios.action", "fields": {"name": "eliminarEscuela", "label": "Eliminar escuela", "type": "crud", "category": "escuelas", "sort_order": 13}},
  {"model": "usuarios.action", "fields": {"name": "crearOperativo", "label": "Crear operativo", "type": "crud", "category": "operativos", "sort_order": 20}},
  {"model": "usuarios.action", "fields": {"name": "verOperativo", "label": "Ver operativo", "type": "crud", "category": "operativos", "sort_order": 21}},
  {"model": "usuarios.action", "fields": {"name": "editarOperativo", "label": "Editar operativo", "type": "crud", "category": "operativos", "sort_order": 22}},
  {"model": "usuarios.action", "fields": {"name": "confirmarOperativo", "label": "Confirmar operativo", "type": "action", "category": "operativos", "is_sensitive": true, "sort_order": 23}},
  {"model": "usuarios.action", "fields": {"name": "cancelarOperativo", "label": "Cancelar operativo", "type": "action", "category": "operativos", "is_sensitive": true, "sort_order": 24}},
  {"model": "usuarios.action", "fields": {"name": "gestionarProfesionalesEnOperativo", "label": "Gestionar profesionales", "type": "action", "category": "operativos", "sort_order": 25}},
  {"model": "usuarios.action", "fields": {"name": "importarNominaOperativo", "label": "Importar nómina", "type": "action", "category": "operativos", "sort_order": 26}},
  {"model": "usuarios.action", "fields": {"name": "gestionarEstadoAlumnoEnOperativo", "label": "Gestionar estado alumno", "type": "action", "category": "operativos", "sort_order": 27}}
]
```

**Nota:** Los `pk` se omiten (null) para que Django los asigne automáticamente.

## 2. Management command: seed_all

**Archivo:** `apps/usuarios/management/commands/seed_all.py`
```python
from django.core.management import call_command
from django.core.management.base import BaseCommand
from apps.usuarios.models import Rol


class Command(BaseCommand):
    help = 'Carga fixtures de acciones y roles base'

    def handle(self, *args, **options):
        # Crear roles base si no existen
        roles = ['ayudante', 'medico', 'odontologo', 'admin']
        for nombre in roles:
            Rol.objects.get_or_create(rol=nombre)

        # Cargar acciones desde fixture
        call_command('loaddata', 'actions.json')

        # Asignar acciones a roles (opcional, se puede hacer manual)
        self.stdout.write(self.style.SUCCESS('Seed completado: roles + acciones'))
```

## 3. Ejecutar

```bash
python manage.py makemigrations usuarios
python manage.py migrate usuarios
python manage.py seed_all
```

## 4. Test

```bash
python manage.py shell -c "
from apps.usuarios.models import Action, Rol, RoleAction
print('Acciones:', Action.objects.count())
print('Roles:', Rol.objects.count())
"
```

## Criterio de aceptación

- `python manage.py seed_all` completa sin errores
- Las 12 acciones existen en la tabla `acciones`
- Los 4 roles existen en la tabla `roles`
- Se puede asignar una acción a un rol via `RoleAction.objects.create(role=rol, action=action)`

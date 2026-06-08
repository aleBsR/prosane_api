# common — infraestructura transversal

Modelo base de auditoría reutilizable. La mayoría de las tablas del dominio
heredan de `BaseModel` para obtener identidad, auditoría y soft delete.

## Uso

```python
from django.db import models
from common.models import BaseModel


class ControlIntegralSalud(BaseModel):
    numero_planilla = models.CharField(max_length=50)
    # Heredados de BaseModel:
    #   id (UUID), created_at, updated_at, created_by, updated_by, deleted_at
```

`BaseModel` combina `UUIDPrimaryKeyModel` (PK UUID) y `AuditModel` (auditoría +
soft delete). Si un modelo no quiere cambiar su PK, puede heredar solo de
`AuditModel`.

> ⚠️ Las columnas de auditoría solo se materializan si Django controla el
> esquema (`managed=True`) o si ya existen en la base externa. Ver
> `docs/reconciliacion-modelo.md`.

## Soft delete

Los registros no se borran: se marcan con `deleted_at`.

| Acceso | Qué hace |
|--------|----------|
| `Modelo.objects.all()` | solo registros vivos (default) |
| `Modelo.all_objects.all()` | todos, incluidos los borrados |
| `Modelo.all_objects.alive()` / `.dead()` | filtra vivos / borrados |
| `obj.delete()` | soft delete (marca `deleted_at`) |
| `Modelo.objects.filter(...).delete()` | soft delete masivo |
| `obj.hard_delete()` | borrado real de la fila (explícito) |
| `obj.restore()` | revive un registro borrado |

El borrado masivo por cualquiera de los dos managers es **soft**; el borrado
real es siempre explícito vía `hard_delete()`.

> Nota: `delete()` de instancia devuelve `None` (no la tupla
> `(count, {label: count})` de Django).

## Sellar el actor (created_by / updated_by)

La regla es setearlo explícito en los services:

```python
NNA.objects.create(**data, created_by=actor, updated_by=actor)
```

En vistas DRF genéricas, `AuditViewMixin` lo hace por defecto desde
`request.user`:

```python
from common.mixins import AuditViewMixin

class NNAViewSet(AuditViewMixin, viewsets.ModelViewSet):
    ...
```

Para serializers usados fuera de una vista con `AuditViewMixin`, está
`AuditSerializerMixin` (ambos componen de forma segura). Marcá los campos de
auditoría como read-only:

```python
from common.serializers import AuditSerializerMixin

class NNASerializer(AuditSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = NNA
        fields = [...]
        read_only_fields = AuditSerializerMixin.AUDIT_READ_ONLY_FIELDS
```

Los campos de auditoría nunca se aceptan desde el payload del cliente.

## Tests

```bash
python manage.py test common --settings=config.settings.test
```

Los settings de test usan SQLite en memoria y un `ROOT_URLCONF` vacío, así la
suite corre aislada sin `.env` ni de los bugs pre-existentes de `config.urls`.

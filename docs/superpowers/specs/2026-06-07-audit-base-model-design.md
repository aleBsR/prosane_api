# Diseño — Modelo base de auditoría (`AuditModel` / `BaseModel`)

**Fecha:** 2026-06-07
**Estado:** Aprobado (diseño) — pendiente de plan de implementación
**Autor:** Roberto (guía) + Claude

---

## 1. Contexto y objetivo

PROSANE API necesita campos de auditoría a nivel profesional, tomando como referencia el
patrón de `snapping-api` (macro `addTrackableColumns`: `created_by`, `updated_by`,
`created_at`, `updated_at`, `deleted_at`).

`snapping-api` es Node + Knex + MySQL, así que **no se copia código literal**: se porta el
**concepto** a la forma idiomática de Django, que es un **modelo base abstracto** del que
hereda la mayoría de las tablas.

**Objetivo:** un componente **genérico y reutilizable** (no campos pegados tabla por tabla)
que provea identidad, auditoría y soft delete a cualquier modelo que lo herede.

### Decisiones ya tomadas (brainstorming)

| Decisión | Elección |
|----------|----------|
| Enfoque | **A — modelo base abstracto** (equivalente idiomático del macro de snapping) |
| Campos | **Núcleo + soft delete** (`created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at`). Sin `created_year`/`year_month` de snapping: redundantes en PostgreSQL (se resuelven con índice sobre `created_at` + `date_trunc`). |
| Seteo de actor | **Explícito en services** (la vista pasa `request.user`), con un mixin DRF opcional como red de seguridad. |
| Ubicación | App nueva **`common/`** (infraestructura transversal, separada del dominio). |
| PK | **UUID** (consistente con `authentication.Usuarios`). |

### Restricción heredada del estado actual

Casi todas las tablas hoy son `managed = False` (hechas a mano, sin DDL versionado, mapeadas
con `inspectdb`). **Una base abstracta solo materializa columnas si Django controla el
esquema** (`managed = True`) o si esas columnas ya existen en el SQL externo. Este diseño
deja el `BaseModel` listo **independientemente** de esa decisión, que Roberto resuelve al
analizar las tablas existentes (ver `docs/reconciliacion-modelo.md`).

---

## 2. Estructura del código

App nueva `common/`, dedicada a infraestructura transversal:

```
common/
├── __init__.py
├── apps.py
├── models.py        # UUIDPrimaryKeyModel, AuditModel, BaseModel (abstractos)
├── managers.py      # SoftDeleteManager, SoftDeleteQuerySet
├── serializers.py   # AuditSerializerMixin
├── mixins.py        # AuditViewMixin (perform_create/perform_update DRF)
└── tests/
    ├── __init__.py
    └── test_audit_model.py
```

`core/` queda solo para dominio (`Personas`, `Domicilio`). Registrar `common` en
`INSTALLED_APPS` (`config/settings/base.py`).

---

## 3. Modelos base (`common/models.py`)

Diseño **componible**: un mixin para la PK UUID y otro para auditoría; `BaseModel` combina
ambos y es lo que hereda la mayoría de las tablas. Una tabla puede heredar solo `AuditModel`
si no quiere cambiar su PK.

```python
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from common.managers import SoftDeleteManager


class UUIDPrimaryKeyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class AuditModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", db_column="created_by",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", db_column="updated_by",
    )
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()      # por defecto oculta los borrados
    all_objects = models.Manager()     # acceso a todo, incluso borrados

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete: marca deleted_at en vez de borrar la fila."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Borrado real de la fila. Explícito, para casos puntuales."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])


class BaseModel(UUIDPrimaryKeyModel, AuditModel):
    """Lo que hereda la mayoría de las tablas del dominio."""

    class Meta:
        abstract = True
```

**Razones de diseño:**
- `related_name="+"` → evita choques de accesor inverso cuando muchas tablas comparten
  `created_by`/`updated_by`.
- `on_delete=SET_NULL` → conserva la auditoría aunque se borre el usuario (igual que snapping).
- `db_index=True` en `created_at` y `deleted_at` → soporta reportes por fecha y el filtro
  de soft delete.
- PK UUID → consistente con `authentication.Usuarios`.

---

## 4. Soft delete (`common/managers.py`)

```python
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(
            deleted_at__isnull=True
        )
```

- `Modelo.objects.all()` → solo vivos.
- `Modelo.all_objects.all()` → incluye borrados.
- `.delete()` sobre queryset también es soft (`UPDATE deleted_at = now()`).

---

## 5. Seteo del actor (explícito en services)

La **fuente de verdad** es el service, que recibe `actor` y sella `created_by`/`updated_by`.

```python
# Service (ejemplo)
from django.db import transaction

class NNAService:
    @staticmethod
    @transaction.atomic
    def create(data, actor):
        return NNA.objects.create(**data, created_by=actor, updated_by=actor)

    @staticmethod
    @transaction.atomic
    def update(instance, data, actor):
        for field, value in data.items():
            setattr(instance, field, value)
        instance.updated_by = actor
        instance.save()
        return instance
```

```python
# Vista delgada DRF
class NNAViewSet(AuditViewMixin, viewsets.ModelViewSet):
    ...
```

`common/mixins.py` provee `AuditViewMixin` como red de seguridad para vistas DRF genéricas:

```python
class AuditViewMixin:
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
```

`common/serializers.py` provee `AuditSerializerMixin` para serializers que quieran sellar
desde `self.context["request"].user`, y marca los campos de auditoría como `read_only`
(no se aceptan desde el cliente).

**Regla:** los campos de auditoría **nunca** se setean desde el payload del cliente; siempre
desde `request.user` en el backend.

---

## 6. Aplicación a las tablas (fuera del alcance de este spec)

Este spec entrega **solo el componente genérico** (`common/`). Aplicarlo a tablas concretas
es trabajo posterior, condicionado al análisis de Roberto sobre las tablas `managed=False`:

- **Tablas nuevas canónicas** (ej. `ControlIntegralSalud`) → nacen `managed=True` heredando
  `BaseModel`. Las columnas se crean por migración Django.
- **Tablas hechas a mano** → si pasan a `managed=True`, heredan y listo; si quedan externas,
  hay que agregar las 5 columnas en el SQL y mapearlas en el modelo (`managed=False`).

No se modifica ninguna tabla de dominio en esta entrega.

---

## 7. Testing (`common/tests/test_audit_model.py`)

Se crea un modelo concreto de prueba que herede `BaseModel` (solo en el entorno de tests) y
se valida:

1. `created_at` / `updated_at` se setean al crear; `updated_at` cambia al guardar de nuevo.
2. `delete()` marca `deleted_at` y **no** borra la fila.
3. El registro borrado **no** aparece en `objects` pero **sí** en `all_objects`.
4. `hard_delete()` borra la fila de verdad.
5. `restore()` limpia `deleted_at` y el registro vuelve a `objects`.
6. `.delete()` sobre un queryset hace soft delete masivo.
7. El service sella `created_by` y `updated_by` con el actor pasado.
8. `AuditViewMixin.perform_create` sella ambos campos con `request.user`.

Framework: `pytest` + `pytest-django` (agregar a requirements de desarrollo si falta).

---

## 8. Fuera de alcance (YAGNI / futuro)

- Historial de cambios campo-por-campo (`django-simple-history` / `django-auditlog`) — es
  otro tipo de auditoría, candidato a extensión futura.
- Campos `created_year` / `created_year_month` de snapping — redundantes en PostgreSQL.
- Middleware con thread-local para setear el actor automáticamente — se descartó por "magia"
  global y dificultad de testeo.
- Aplicar el `BaseModel` a las tablas existentes — depende del análisis de las tablas.

---

## 9. Preguntas abiertas

1. ¿Las tablas existentes pasan a `managed=True` o se mantiene la base externa? (Lo resuelve
   Roberto al analizar las tablas; no bloquea esta entrega.)
2. ¿`pytest` ya está en el entorno o hay que agregarlo a los requirements de desarrollo?

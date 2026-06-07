# Plan de implementación — Modelo base de auditoría (`common`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear una app `common` con un modelo base abstracto (`BaseModel`) que dé PK UUID, auditoría (`created_at`/`updated_at`/`created_by`/`updated_by`) y soft delete (`deleted_at`) a cualquier tabla que lo herede.

**Architecture:** Modelo base abstracto idiomático de Django (equivalente del macro `addTrackableColumns` de snapping-api). El actor se setea explícito en la capa de servicios, con mixins DRF opcionales como red de seguridad. El soft delete se implementa con un manager que por defecto oculta los registros borrados.

**Tech Stack:** Django 6.0.5, Django REST Framework 3.17.1, tests con el runner nativo de Django (`manage.py test`) sobre SQLite en memoria.

**Spec:** `docs/superpowers/specs/2026-06-07-audit-base-model-design.md`

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---------|-----------------|
| `common/__init__.py` | Marca el paquete |
| `common/apps.py` | `CommonConfig` |
| `common/managers.py` | `SoftDeleteQuerySet`, `SoftDeleteManager` |
| `common/models.py` | `UUIDPrimaryKeyModel`, `AuditModel`, `BaseModel` (abstractos) |
| `common/mixins.py` | `AuditViewMixin` (DRF) |
| `common/serializers.py` | `AuditSerializerMixin` (DRF) |
| `common/tests/__init__.py` | Marca el paquete de tests |
| `common/tests/base.py` | `AuditModelTestCase` (construye un modelo concreto efímero) |
| `common/tests/test_models.py` | Tests de timestamps, soft delete, actor |
| `common/tests/test_mixins.py` | Tests de `AuditViewMixin` |
| `config/settings/test.py` | Settings de test (SQLite en memoria, SECRET_KEY de test) |
| `config/settings/base.py` | Modificar: registrar `common` en `INSTALLED_APPS` |

---

## Task 1: Scaffold de la app `common` y settings de test

**Files:**
- Create: `common/__init__.py`, `common/apps.py`
- Create: `config/settings/test.py`
- Modify: `config/settings/base.py` (INSTALLED_APPS)

- [ ] **Step 1: Crear el paquete `common`**

Crear `common/__init__.py` vacío.

Crear `common/apps.py`:

```python
from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "common"
```

- [ ] **Step 2: Registrar la app en `INSTALLED_APPS`**

En `config/settings/base.py`, dentro de `INSTALLED_APPS`, agregar `"common",` debajo de `"rest_framework_simplejwt",` y arriba de `"core",`:

```python
    "rest_framework",
    "rest_framework_simplejwt",
    "common",
    "core",
    "authentication",
    "patients",
    "professionals",
]
```

- [ ] **Step 3: Crear settings de test**

Crear `config/settings/test.py`:

```python
"""Settings para correr la suite de tests: aislados, rápidos, sin .env."""
from .base import *  # noqa: F401,F403

SECRET_KEY = "django-insecure-test-key-only-for-tests"

# simplejwt fija SIGNING_KEY al importar base.py (cuando SECRET_KEY aún era None);
# lo realineamos al SECRET_KEY de test.
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": SECRET_KEY}  # noqa: F405

# SQLite en memoria: evita depender de Postgres y de las tablas managed=False.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Hashing rápido para tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
```

- [ ] **Step 4: Verificar que el proyecto chequea con los settings de test**

Run: `python manage.py check --settings=config.settings.test`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit**

```bash
git add common/__init__.py common/apps.py config/settings/test.py config/settings/base.py
git commit -m "feat(common): scaffold de la app common y settings de test

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Manager de soft delete y modelos base abstractos

**Files:**
- Create: `common/managers.py`
- Create: `common/models.py`
- Create: `common/tests/__init__.py`, `common/tests/base.py`, `common/tests/test_models.py`

- [ ] **Step 1: Escribir el manager y los modelos (necesarios para que los tests importen)**

Crear `common/managers.py`:

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

Crear `common/models.py`:

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
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="created_by",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        db_column="updated_by",
    )
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

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

- [ ] **Step 2: Escribir el harness de test (modelo concreto efímero) y los tests fallidos**

Crear `common/tests/__init__.py` vacío.

Crear `common/tests/base.py`:

```python
from django.db import connection, models
from django.test import TestCase
from django.test.utils import isolate_apps

from common.models import BaseModel


class AuditModelTestCase(TestCase):
    """Construye un modelo concreto efímero que hereda BaseModel.

    BaseModel es abstracto (no tiene tabla). Para probarlo creamos un modelo
    concreto en un registro de apps aislado y su tabla con schema_editor, y la
    borramos al terminar. Así no ensuciamos el esquema real.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._app_isolation = isolate_apps("common")
        cls._app_isolation.enable()

        class AuditExample(BaseModel):
            name = models.CharField(max_length=50, blank=True, default="")

            class Meta:
                app_label = "common"

        cls.AuditExample = AuditExample

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(AuditExample)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(cls.AuditExample)
        cls._app_isolation.disable()
        super().tearDownClass()
```

Crear `common/tests/test_models.py`:

```python
import time

from django.contrib.auth import get_user_model

from common.tests.base import AuditModelTestCase

User = get_user_model()


class TimestampTests(AuditModelTestCase):
    def test_created_and_updated_at_set_on_create(self):
        obj = self.AuditExample.objects.create(name="a")
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)

    def test_updated_at_changes_on_save(self):
        obj = self.AuditExample.objects.create(name="a")
        first = obj.updated_at
        time.sleep(0.01)
        obj.name = "b"
        obj.save()
        obj.refresh_from_db()
        self.assertGreater(obj.updated_at, first)


class SoftDeleteTests(AuditModelTestCase):
    def test_delete_sets_deleted_at_and_keeps_row(self):
        obj = self.AuditExample.objects.create(name="a")
        obj.delete()
        self.assertIsNotNone(obj.deleted_at)
        self.assertTrue(self.AuditExample.all_objects.filter(pk=obj.pk).exists())

    def test_default_manager_hides_deleted(self):
        obj = self.AuditExample.objects.create(name="a")
        obj.delete()
        self.assertFalse(self.AuditExample.objects.filter(pk=obj.pk).exists())
        self.assertTrue(self.AuditExample.all_objects.filter(pk=obj.pk).exists())

    def test_hard_delete_removes_row(self):
        obj = self.AuditExample.objects.create(name="a")
        obj.hard_delete()
        self.assertFalse(self.AuditExample.all_objects.filter(pk=obj.pk).exists())

    def test_restore_brings_back(self):
        obj = self.AuditExample.objects.create(name="a")
        obj.delete()
        obj.restore()
        self.assertIsNone(obj.deleted_at)
        self.assertTrue(self.AuditExample.objects.filter(pk=obj.pk).exists())

    def test_queryset_delete_is_soft(self):
        self.AuditExample.objects.create(name="a")
        self.AuditExample.objects.create(name="b")
        self.AuditExample.objects.all().delete()
        self.assertEqual(self.AuditExample.objects.count(), 0)
        self.assertEqual(self.AuditExample.all_objects.count(), 2)


class ActorTests(AuditModelTestCase):
    def test_created_by_and_updated_by_stored(self):
        user = User.objects.create_user(email="t@t.com", password="x")
        obj = self.AuditExample.objects.create(
            name="a", created_by=user, updated_by=user
        )
        self.assertEqual(obj.created_by, user)
        self.assertEqual(obj.updated_by, user)
```

- [ ] **Step 3: Correr los tests y verificar que pasan**

Run: `python manage.py test common.tests.test_models --settings=config.settings.test -v 2`
Expected: `Ran 8 tests` y `OK`.

(Step 1 ya implementó el código de producción, por eso esta tanda pasa en verde. Si algún test falla, corregí `common/models.py` o `common/managers.py` antes de seguir.)

- [ ] **Step 4: Commit**

```bash
git add common/managers.py common/models.py common/tests/
git commit -m "feat(common): AuditModel/BaseModel con soft delete y auditoría

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Mixins DRF para sellar el actor

**Files:**
- Create: `common/mixins.py`
- Create: `common/serializers.py`
- Create: `common/tests/test_mixins.py`

- [ ] **Step 1: Escribir el view mixin y el serializer mixin**

Crear `common/mixins.py`:

```python
class AuditViewMixin:
    """Para vistas/viewsets genéricas de DRF: sella el actor desde request.user.

    Úsese como primera clase base:
        class NNAViewSet(AuditViewMixin, viewsets.ModelViewSet): ...
    """

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user, updated_by=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
```

Crear `common/serializers.py`:

```python
class AuditSerializerMixin:
    """Sella el actor desde el request en serializers que no usan AuditViewMixin.

    Los serializers concretos deberían marcar los campos de auditoría como
    read-only, por ejemplo en Meta:
        read_only_fields = AuditSerializerMixin.AUDIT_READ_ONLY_FIELDS
    """

    AUDIT_READ_ONLY_FIELDS = (
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
    )

    def _actor(self):
        request = self.context.get("request")
        return getattr(request, "user", None) if request is not None else None

    def create(self, validated_data):
        actor = self._actor()
        if actor is not None and getattr(actor, "is_authenticated", False):
            validated_data.setdefault("created_by", actor)
            validated_data.setdefault("updated_by", actor)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        actor = self._actor()
        if actor is not None and getattr(actor, "is_authenticated", False):
            validated_data["updated_by"] = actor
        return super().update(instance, validated_data)
```

- [ ] **Step 2: Escribir los tests del view mixin**

Crear `common/tests/test_mixins.py`:

```python
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from common.mixins import AuditViewMixin
from common.tests.base import AuditModelTestCase

User = get_user_model()


class AuditViewMixinTests(AuditModelTestCase):
    def _serializer_class(self):
        model = self.AuditExample

        class _ExampleSerializer(serializers.ModelSerializer):
            class Meta:
                model = model
                fields = ["id", "name", "created_by", "updated_by"]
                read_only_fields = ["created_by", "updated_by"]

        return _ExampleSerializer

    def _view_with_user(self, user):
        class _View(AuditViewMixin):
            pass

        view = _View()
        request = APIRequestFactory().post("/")
        request.user = user
        view.request = request
        return view

    def test_perform_create_stamps_actor(self):
        user = User.objects.create_user(email="v@v.com", password="x")
        serializer = self._serializer_class()(data={"name": "a"})
        serializer.is_valid(raise_exception=True)

        self._view_with_user(user).perform_create(serializer)

        obj = serializer.instance
        self.assertEqual(obj.created_by, user)
        self.assertEqual(obj.updated_by, user)

    def test_perform_update_stamps_updated_by(self):
        creator = User.objects.create_user(email="c@c.com", password="x")
        editor = User.objects.create_user(email="e@e.com", password="x")
        obj = self.AuditExample.objects.create(
            name="a", created_by=creator, updated_by=creator
        )

        serializer = self._serializer_class()(
            instance=obj, data={"name": "b"}, partial=True
        )
        serializer.is_valid(raise_exception=True)

        self._view_with_user(editor).perform_update(serializer)

        obj.refresh_from_db()
        self.assertEqual(obj.created_by, creator)
        self.assertEqual(obj.updated_by, editor)
```

- [ ] **Step 3: Correr los tests del mixin y verificar que pasan**

Run: `python manage.py test common.tests.test_mixins --settings=config.settings.test -v 2`
Expected: `Ran 2 tests` y `OK`.

- [ ] **Step 4: Correr toda la suite de `common`**

Run: `python manage.py test common --settings=config.settings.test -v 2`
Expected: `Ran 10 tests` y `OK`.

- [ ] **Step 5: Commit**

```bash
git add common/mixins.py common/serializers.py common/tests/test_mixins.py
git commit -m "feat(common): mixins DRF para sellar created_by/updated_by

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Documentar el uso en el README de la app

**Files:**
- Create: `common/README.md`

- [ ] **Step 1: Escribir el README de uso**

Crear `common/README.md`:

```markdown
# common — infraestructura transversal

Modelo base de auditoría reutilizable. La mayoría de las tablas del dominio
heredan de `BaseModel`.

## Uso

```python
from common.models import BaseModel

class ControlIntegralSalud(BaseModel):
    numero_planilla = models.CharField(max_length=50)
    # id (UUID), created_at, updated_at, created_by, updated_by, deleted_at
    # vienen heredados.
```

> Las columnas de auditoría solo se crean si Django controla el esquema
> (`managed=True`) o si ya existen en la base externa. Ver
> `docs/reconciliacion-modelo.md`.

## Soft delete

- `Modelo.objects.all()` → solo registros vivos.
- `Modelo.all_objects.all()` → incluye los borrados.
- `obj.delete()` → soft delete (marca `deleted_at`).
- `obj.hard_delete()` → borrado real.
- `obj.restore()` → revive un registro borrado.

## Sellar el actor (created_by / updated_by)

La regla es setearlo explícito en los services:

```python
NNA.objects.create(**data, created_by=actor, updated_by=actor)
```

En vistas DRF genéricas, usar `AuditViewMixin` como red de seguridad:

```python
from common.mixins import AuditViewMixin

class NNAViewSet(AuditViewMixin, viewsets.ModelViewSet):
    ...
```

Los campos de auditoría nunca se aceptan desde el payload del cliente.
```

- [ ] **Step 2: Commit**

```bash
git add common/README.md
git commit -m "docs(common): guia de uso del modelo base de auditoría

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Verificación final

- [ ] `python manage.py test common --settings=config.settings.test -v 2` → 10 tests OK.
- [ ] `python manage.py check --settings=config.settings.test` → sin issues.
- [ ] No se modificó ninguna tabla de dominio (`core`, `patients`, `professionals`, `authentication`).
- [ ] `common/` contiene: `models.py`, `managers.py`, `mixins.py`, `serializers.py`, `tests/`, `README.md`.

## Notas para quien ejecute

- **No** aplicar `BaseModel` a tablas existentes en este plan: depende del análisis de las tablas `managed=False` que hace Roberto (ver `docs/reconciliacion-modelo.md`).
- El `created_by`/`updated_by` apunta a `authentication.Usuarios` vía `settings.AUTH_USER_MODEL`.
- Si en el futuro se agrega `pytest-django`, estos tests (escritos como `TestCase`) corren igual con `pytest`.

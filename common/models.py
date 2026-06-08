import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.managers import SoftDeleteManager, SoftDeleteQuerySet


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
    # Unfiltered: ve TODOS los registros (incluidos los borrados) y expone
    # alive()/dead(). El delete() masivo por este manager también es soft;
    # el borrado real es explícito vía hard_delete().
    all_objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete: marca deleted_at en vez de borrar la fila.

        Nota: devuelve None (no la tupla (count, {label: count}) de Django).
        """
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

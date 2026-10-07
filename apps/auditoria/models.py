from django.db import models

from common.models import BaseModel


class AuditoriaCambio(BaseModel):
    """Quién hizo cada alta/modificación/baja de datos del dominio.

    Una sola tabla genérica (sin FK al recurso para no acoplar apps):
    `entidad` + `entidad_id` identifican qué se tocó. El `detalle` lleva
    solo nombres de campos e identificadores (nombre/DNI/email/conteos),
    nunca valores clínicos (minimización, Ley N° 25.326).
    """

    CREAR = "crear"
    EDITAR = "editar"
    ELIMINAR = "eliminar"
    DESACTIVAR = "desactivar"
    IMPORTAR = "importar"
    CAMBIAR_ESTADO = "cambiar_estado"
    LEER = "leer"

    ACCIONES = (
        (CREAR, "Crear"),
        (EDITAR, "Editar"),
        (DESACTIVAR, "Desactivar"),
        (ELIMINAR, "Eliminar"),
        (IMPORTAR, "Importar"),
        (CAMBIAR_ESTADO, "Cambiar estado"),
        (LEER, "Leer"),
    )

    actor = models.ForeignKey(
        "usuarios.Usuario",
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_cambios",
        db_column="id_actor",
    )
    entidad = models.CharField(max_length=50, db_index=True)
    entidad_id = models.UUIDField(null=True, blank=True, db_index=True)
    accion = models.CharField(max_length=32)
    detalle = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "auditoria_cambios"
        ordering = ["-created_at"]

from django.conf import settings
from django.db import models

from common.models import BaseModel


class AuditoriaUsuario(BaseModel):
    """Registro de quién gestionó cuentas sensibles (solo superadmins).

    Cada vez que un superadmin crea, desactiva, reactiva o reenvía la
    contraseña temporal a otro superadmin, se deja constancia con actor,
    objetivo, acción e IP.
    """

    CREAR = "crear"
    DESACTIVAR = "desactivar"
    REACTIVAR = "reactivar"
    RESEND_TEMP = "resend_temp"

    ACCIONES = (
        (CREAR, "Crear superadmin"),
        (DESACTIVAR, "Desactivar superadmin"),
        (REACTIVAR, "Reactivar superadmin"),
        (RESEND_TEMP, "Reenviar contraseña temporal"),
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_realizadas",
        db_column="id_actor",
    )
    objetivo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_recibidas",
        db_column="id_objetivo",
    )
    accion = models.CharField(max_length=32)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "auditoria_usuarios"

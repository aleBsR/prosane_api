from django.db import models
from common.models import BaseModel


class Tutor(BaseModel):
    parentesco = models.CharField(max_length=50)
    persona = models.ForeignKey(
        "personas.Persona",
        models.DO_NOTHING,
        db_column="id_persona",
        null=True,
        blank=True,
    )
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        models.DO_NOTHING,
        db_column="usuario",
        null=True,
        blank=True,
    )
    consentimiento_aceptado = models.BooleanField(default=False)
    fecha_consentimiento = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "responsables"

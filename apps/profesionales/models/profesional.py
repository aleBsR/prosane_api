from django.db import models
from common.models import BaseModel


class Profesional(BaseModel):
    matricula = models.CharField(max_length=256)
    nombre = models.CharField(max_length=256, blank=True, null=True)
    apellido = models.CharField(max_length=256, blank=True, null=True)
    id_usuario = models.ForeignKey(
        "usuarios.Usuario",
        models.DO_NOTHING,
        db_column="id_usuario",
    )

    class Meta:
        managed = True
        db_table = "profesionales"

from django.db import models
from common.models import BaseModel

from apps.escuelas.models.escuela import Escuela


class ObservacionEscuela(BaseModel):
    paciente = models.ForeignKey(
        "pacientes.Paciente",
        models.DO_NOTHING,
        db_column="id_paciente",
    )
    escuela = models.ForeignKey(
        Escuela,
        models.DO_NOTHING,
        db_column="id_escuela",
    )
    dificultad_comunicacion = models.CharField(max_length=255, db_column="dificultad_comunicacion")
    esta_bajo_tratamiento = models.BooleanField(db_column="bajo_tratamiento")
    preocupaciones = models.CharField(max_length=255, db_column="preocupaciones")

    class Meta:
        managed = True
        db_table = "observacionEscuela"
        unique_together = (("paciente", "escuela"),)

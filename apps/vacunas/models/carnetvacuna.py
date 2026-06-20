from django.db import models
from common.models import BaseModel

from apps.vacunas.models.vacuna import Vacuna


class CarnetVacuna(BaseModel):
    vacuna = models.ForeignKey(
        Vacuna,
        models.DO_NOTHING,
        db_column="id_vacuna",
    )
    paciente = models.ForeignKey(
        "pacientes.Paciente",
        models.DO_NOTHING,
        db_column="id_paciente",
    )

    class Meta:
        managed = True
        db_table = "carnetVacunas"
        unique_together = (("vacuna", "paciente"),)

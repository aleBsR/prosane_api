from django.db import models
from common.models import BaseModel


class AntecedenteFamiliar(BaseModel):
    paciente = models.ForeignKey(
        "pacientes.Paciente",
        models.DO_NOTHING,
        db_column="id_paciente",
    )
    problemas_salud = models.CharField(max_length=10, blank=True, null=True)
    detalle_problema_salud = models.CharField(max_length=255, blank=True, null=True)
    familiar_con_muerte_subita = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "antecedentesfamiliares"

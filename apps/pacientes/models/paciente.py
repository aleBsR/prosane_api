from django.db import models
from common.models import BaseModel


class Paciente(BaseModel):
    domicilio = models.ForeignKey(
        "personas.Domicilio",
        models.DO_NOTHING,
        db_column="id_domicilio",
    )
    tutor = models.ForeignKey(
        "tutores.Tutor",
        models.DO_NOTHING,
        db_column="id_responsable",
        null=True,
    )
    persona = models.ForeignKey(
        "personas.Persona",
        models.DO_NOTHING,
        db_column="id_persona",
    )
    edad = models.IntegerField()
    tiene_cud = models.CharField(max_length=2, blank=True, null=True)
    tipo_cobertura = models.CharField(max_length=20, blank=True, null=True)
    nombre_cobertura = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "pacientes"

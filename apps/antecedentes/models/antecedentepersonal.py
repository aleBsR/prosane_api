from django.db import models
from common.models import BaseModel


class AntecedentePersonal(BaseModel):
    paciente = models.ForeignKey(
        "pacientes.Paciente",
        models.DO_NOTHING,
        db_column="id_paciente",
    )
    nacio_prematuro = models.CharField(max_length=10, default="NO")
    peso_nacimiento = models.CharField(max_length=10, default="0")
    convulsiones_epilepsia = models.CharField(max_length=10, default="NO")
    mareos_desmayos = models.CharField(max_length=10, default="NO")
    infecciones_urinarias = models.CharField(max_length=10, default="NO")
    asma_espasmos = models.CharField(max_length=10, default="NO")
    tuberculosis = models.CharField(max_length=10, default="NO")
    diabetes = models.CharField(max_length=10, default="NO")
    hipertension = models.CharField(max_length=10, default="NO")
    cardiopatia_congenita = models.CharField(max_length=10, default="NO")
    traumatismo_internacion = models.CharField(max_length=255, default="NO")
    diarrea_frecuente = models.CharField(max_length=255, default="NO")
    infecciones_oido = models.CharField(max_length=255, default="NO")
    internacion_previa = models.CharField(max_length=255, default="NO")
    causa_hospitalizacion = models.CharField(max_length=255, default="NO")
    tratamiento_actual = models.CharField(max_length=255, default="NO")
    descripcion_tratamiento = models.CharField(max_length=255, default="NINGUNO")
    ultima_consulta_medica = models.CharField(max_length=255, default="NINGUNA")
    otros_problemas_salud = models.CharField(max_length=255, default="NINGUNO")
    primera_menstruacion = models.CharField(max_length=255, default="NO")
    edad_primera_menstruacion = models.IntegerField(default=0)

    class Meta:
        managed = True
        db_table = "antecedentespersonales"

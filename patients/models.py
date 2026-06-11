import uuid

from django.db import models
from common.models import BaseModel


class Responsables(BaseModel):
    parentesco = models.CharField(max_length=50)
    persona = models.ForeignKey('core.Personas', models.DO_NOTHING, db_column='id_persona', null=True, blank=True)
    usuario = models.ForeignKey('authentication.Usuarios', models.DO_NOTHING, db_column='usuario', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'responsables'


class Vacunas():

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id_vacuna')
    nombre = models.CharField(max_length=100, null=False)


    class Meta:
        managed = False
        db_table = 'vacunas'





class Pacientes(BaseModel):
    domicilio = models.ForeignKey('core.Domicilio', models.DO_NOTHING, db_column='id_domicilio')
    responsable = models.ForeignKey(Responsables, models.DO_NOTHING, db_column='id_responsable', null=True)
    persona = models.ForeignKey('core.Personas', models.DO_NOTHING, db_column='id_persona')
    edad = models.IntegerField()
    tiene_cud = models.CharField(max_length=2, blank=True, null=True)
    tipo_cobertura = models.CharField(max_length=20, blank=True, null=True)
    nombre_cobertura = models.CharField(max_length=20, blank=True, null=True)

    vacunas = models.ManyToManyField(
        Vacunas,
        through='CarnetVacunas',
        through_fields=('id_vacuna','id_paciente')
        related_name='usuarios'
    )
    class Meta:
        managed = False
        db_table = 'pacientes'

class CarnetVacunas():

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id_carnet')

    vacuna = models.ForeignKey(Vacunas,models.DO_NOTHING, db_column='id_vacuna')
    paciente = models.ForeignKey(Pacientes,models.DO_NOTHING, db_column='id_paciente')



    class Meta:
        managed = False
        db_table = 'carnetVacunas'
        unique_together = (('id_vacuna','id_paciente'),)


class Antecedentesfamiliares(BaseModel):
    paciente = models.ForeignKey(Pacientes, models.DO_NOTHING, db_column='id_paciente')
    problemas_salud = models.CharField(max_length=10, blank=True, null=True)
    detalle_problema_salud = models.CharField(max_length=255, blank=True, null=True)
    familiar_con_muerte_subita = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'antecedentesfamiliares'


class Antecedentespersonales(BaseModel):
    paciente = models.ForeignKey(Pacientes, models.DO_NOTHING, db_column='id_paciente')
    nacio_prematuro = models.CharField(max_length=10)
    peso_nacimiento = models.CharField(max_length=10)
    convulsiones_epilepsia = models.CharField(max_length=10)
    mareos_desmayos = models.CharField(max_length=10)
    infecciones_urinarias = models.CharField(max_length=10)
    asma_espasmos = models.CharField(max_length=10)
    tuberculosis = models.CharField(max_length=10)
    diabetes = models.CharField(max_length=10)
    hipertension = models.CharField(max_length=10)
    cardiopatia_congenita = models.CharField(max_length=10)
    traumatismo_internacion = models.CharField(max_length=255)
    diarrea_frecuente = models.CharField(max_length=255)
    infecciones_oido = models.CharField(max_length=255)
    causa_hospitalizacion = models.CharField(max_length=255)
    rabia_tratamiento = models.CharField(max_length=255)
    descripcion_tratamiento = models.CharField(max_length=255)
    ultima_consulta_medica = models.CharField(max_length=255)
    otros_problemas_salud = models.CharField(max_length=255)
    primera_menstruacion = models.CharField(max_length=255)
    edad_primera_menstruacion = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'antecedentespersonales'


from django.db import models


class Responsables(models.Model):
    parentesco = models.CharField(max_length=50)
    id_persona = models.ForeignKey('core.Personas', models.DO_NOTHING, db_column='id_persona')

    class Meta:
        managed = False
        db_table = 'responsables'


class Pacientes(models.Model):
    id_domicilio = models.ForeignKey('core.Domicilio', models.DO_NOTHING, db_column='id_domicilio')
    id_responsable = models.ForeignKey(Responsables, models.DO_NOTHING, db_column='id_responsable')
    id_persona = models.ForeignKey('core.Personas', models.DO_NOTHING, db_column='id_persona')
    sexo = models.CharField(max_length=10)
    fecha_nacimiento = models.DateField()
    edad = models.IntegerField()
    tiene_cud = models.CharField(max_length=2, blank=True, null=True)
    tipo_cobertura = models.CharField(max_length=20, blank=True, null=True)
    nombre_cobertura = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pacientes'


class Antecedentesfamiliares(models.Model):
    id_paciente = models.ForeignKey(Pacientes, models.DO_NOTHING, db_column='id_paciente')
    problemas_salud = models.CharField(max_length=10, blank=True, null=True)
    detalle_problema_salud = models.CharField(max_length=255, blank=True, null=True)
    familiar_con_muerte_subita = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'antecedentesfamiliares'


class Antecedentespersonales(models.Model):
    id_antecedente = models.AutoField(primary_key=True)
    id_paciente = models.ForeignKey(Pacientes, models.DO_NOTHING, db_column='id_paciente')
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

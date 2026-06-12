from django.db import models
from common.models import BaseModel


class Responsables(models.Model):
    # Reconciliación #12: integer id, sin auditoría.
    id = models.AutoField(primary_key=True)
    parentesco = models.CharField(max_length=50)
    persona = models.ForeignKey('core.Personas', models.DO_NOTHING, db_column='id_persona', null=True, blank=True)
    usuario = models.ForeignKey('authentication.Usuarios', models.DO_NOTHING, db_column='usuario', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'responsables'


class Pacientes(models.Model):
    # Reconciliación #12: integer id, sin auditoría.
    id = models.AutoField(primary_key=True)
    domicilio = models.ForeignKey('core.Domicilio', models.DO_NOTHING, db_column='id_domicilio')
    responsable = models.ForeignKey(Responsables, models.DO_NOTHING, db_column='id_responsable', null=True)
    persona = models.ForeignKey('core.Personas', models.DO_NOTHING, db_column='id_persona')
    edad = models.IntegerField()
    tiene_cud = models.CharField(max_length=2, blank=True, null=True)
    tipo_cobertura = models.CharField(max_length=20, blank=True, null=True)
    nombre_cobertura = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pacientes'


class Antecedentesfamiliares(models.Model):
    # Reconciliación #12: integer id, sin auditoría.
    id = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(Pacientes, models.DO_NOTHING, db_column='id_paciente')
    problemas_salud = models.CharField(max_length=10, blank=True, null=True)
    detalle_problema_salud = models.CharField(max_length=255, blank=True, null=True)
    familiar_con_muerte_subita = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'antecedentesfamiliares'


class Antecedentespersonales(models.Model):
    # Reconciliación #12: PK real es id_antecedente, integer, sin auditoría.
    id_antecedente = models.AutoField(primary_key=True)
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


class Consentimiento(BaseModel):
    """Consentimiento de la familia (Ley 26.529). Un paso: crear = consentir; inmutable."""
    ADULTO_RESPONSABLE = 'adulto_responsable'
    NNA_MAYOR_13 = 'nna_mayor_13'
    FIRMA_TIPO_CHOICES = (
        (ADULTO_RESPONSABLE, 'Adulto responsable'),
        (NNA_MAYOR_13, 'NNA mayor de 13'),
    )

    paciente = models.ForeignKey('patients.Pacientes', models.PROTECT, related_name='consentimientos')
    firma_tipo = models.CharField(max_length=20, choices=FIRMA_TIPO_CHOICES)

    adulto_nombre = models.CharField(max_length=200)
    adulto_apellido = models.CharField(max_length=200)
    adulto_tipo_documento = models.CharField(max_length=20)
    adulto_dni = models.CharField(max_length=15)

    firma_hash = models.CharField(max_length=128)
    fecha_firma = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'consentimientos'
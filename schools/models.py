from django.db import models

from common.models import BaseModel

# Create your models here.


class Escuelas(BaseModel):

    nombre_escuela = models.CharField(max_length=100,db_column='nombre_escuela')
    ambito_escuela = models.CharField(max_length=20,db_column='ambito_escuela')
    sector_gestion = models.CharField(max_length=20,db_column='sector_gestion')
    modalidad_educativa = models.CharField(max_length=10,db_column='modalidad_educativa')
    escuela_bilingue = models.BooleanField(db_column='escuela_bilingue')
    rural_plurigrado = models.BooleanField(db_column='rural_plurigrado')

    class Meta:
        managed = False
        db_table = 'escuelas'

class ObservacionEscuela(BaseModel):

    paciente = models.ForeignKey('patients.Pacientes', models.DO_NOTHING, db_column='id_paciente')
    escuela = models.ForeignKey(Escuelas, models.DO_NOTHING, db_column='id_escuela')
    dificultad_comunicacion = models.CharField(max_length=255,db_column='dificultad_comunicacion')
    esta_bajo_tratamiento = models.BooleanField(db_column='bajo_tratamiento')
    preocupaciones = models.CharField(max_length=255,db_column='preocupaciones')

    
    class Meta:
        managed = False
        db_table = 'observacionEscuela'
        unique_together = (('id_paciente','id_escuela'),)




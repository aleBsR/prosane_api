from django.db import models
from common.models import BaseModel


class Profesionales(BaseModel):
    matricula = models.CharField(max_length=256)
    id_usuario = models.ForeignKey('authentication.Usuarios', models.DO_NOTHING, db_column='id_usuario')

    class Meta:
        managed = False
        db_table = 'profesionales'


class Matriculas(BaseModel):
    numero = models.CharField(unique=True, max_length=50)
    tipo = models.CharField(max_length=20)
    nombre_completo = models.CharField(max_length=255, blank=True, null=True)
    activa = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'matriculas'
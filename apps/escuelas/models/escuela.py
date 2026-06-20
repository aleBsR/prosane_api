from django.db import models
from common.models import BaseModel


class Escuela(BaseModel):
    nombre_escuela = models.CharField(max_length=100, db_column="nombre_escuela")
    ambito_escuela = models.CharField(max_length=20, db_column="ambito_escuela")
    sector_gestion = models.CharField(max_length=20, db_column="sector_gestion")
    modalidad_educativa = models.CharField(max_length=10, db_column="modalidad_educativa")
    escuela_bilingue = models.BooleanField(db_column="escuela_bilingue")
    rural_plurigrado = models.BooleanField(db_column="rural_plurigrado")

    class Meta:
        managed = True
        db_table = "escuelas"

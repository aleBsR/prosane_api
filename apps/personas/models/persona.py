from django.db import models
from common.models import BaseModel


class Persona(BaseModel):
    nombre = models.CharField(max_length=256, blank=True, null=True)
    apellido = models.CharField(max_length=256, blank=True, null=True)
    dni = models.CharField(unique=True, max_length=256, blank=True, null=True)
    tipo_dni = models.CharField(max_length=256, blank=True, null=True)
    sexo = models.CharField(max_length=10)
    fecha_nacimiento = models.DateField()

    class Meta:
        managed = True
        db_table = "personas"

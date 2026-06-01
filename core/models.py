from django.db import models


class Domicilio(models.Model):
    calle = models.CharField(max_length=100, blank=True, null=True)
    nro_calle = models.CharField(max_length=10, blank=True, null=True)
    piso = models.CharField(max_length=10, blank=True, null=True)
    dpto = models.CharField(max_length=10, blank=True, null=True)
    manzana = models.CharField(max_length=10, blank=True, null=True)
    casa = models.CharField(max_length=10, blank=True, null=True)
    nro_casa = models.CharField(max_length=10, blank=True, null=True)
    pieza = models.CharField(max_length=20, blank=True, null=True)
    provincia = models.CharField(max_length=20, blank=True, null=True)
    departamento = models.CharField(max_length=20, blank=True, null=True)
    localidad = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'domicilio'


class Personas(models.Model):
    nombre = models.CharField(max_length=256, blank=True, null=True)
    apellido = models.CharField(max_length=256, blank=True, null=True)
    dni = models.CharField(unique=True, max_length=256, blank=True, null=True)
    tipo_dni = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'personas'

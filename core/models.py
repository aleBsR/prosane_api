from django.db import models


class Domicilio(models.Model):
    # Reconciliación #12: tabla integer sin auditoría (no BaseModel).
    id = models.AutoField(primary_key=True)
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
    # Reconciliación de schema (#12): la tabla real `personas` usa id INTEGER y NO
    # tiene las columnas de auditoría de BaseModel. El modelo refleja exactamente la
    # tabla (no hereda BaseModel) para que los writes por ORM (register, seed/people)
    # funcionen. Mismo patrón de bajo riesgo que Roles/UserRole.
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=256, blank=True, null=True)
    apellido = models.CharField(max_length=256, blank=True, null=True)
    dni = models.CharField(unique=True, max_length=256, blank=True, null=True)
    tipo_dni = models.CharField(max_length=256, blank=True, null=True)
    sexo = models.CharField(max_length=10)
    fecha_nacimiento = models.DateField()

    class Meta:
        managed = False
        db_table = 'personas'


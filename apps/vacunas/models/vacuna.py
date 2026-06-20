from django.db import models
from common.models import BaseModel


class Vacuna(BaseModel):
    nombre = models.CharField(max_length=100, null=False)

    class Meta:
        managed = True
        db_table = "vacunas"

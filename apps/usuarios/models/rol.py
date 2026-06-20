from django.db import models
from common.models import BaseModel
from apps.usuarios.models.usuario import Usuario


class Rol(BaseModel):
    rol = models.CharField(max_length=50, blank=True, null=True)
    ruta = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "roles"


class RoleUsuario(BaseModel):
    id_rol = models.ForeignKey(Rol, models.DO_NOTHING, db_column="id_rol")
    id_user = models.ForeignKey(Usuario, models.DO_NOTHING, db_column="id_user")

    class Meta:
        managed = True
        db_table = "roleUsuario"
        unique_together = (("id_rol", "id_user"),)

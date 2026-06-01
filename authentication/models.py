from django.db import models
from django.contrib.auth.models import AbstractUser


class Roles(models.Model):
    rol = models.CharField(max_length=50, blank=True, null=True)
    ruta = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'


class Usuarios(AbstractUser):
    id = models.UUIDField(primary_key=True)
    id_persona = models.ForeignKey(
        'core.Personas', models.DO_NOTHING,
        db_column='id_persona', blank=True, null=True
    )
    email = models.CharField(unique=True, max_length=256, blank=True, null=True)
    password_hash = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuarios'


class UserRole(models.Model):
    id = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Roles, models.DO_NOTHING, db_column='id_rol')
    id_user = models.ForeignKey(Usuarios, models.DO_NOTHING, db_column='id_user')
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_role'
        unique_together = (('id_rol', 'id_user'),)

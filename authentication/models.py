import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from common.models import BaseModel


class Roles(BaseModel):
    rol = models.CharField(max_length=50, blank=True, null=True)
    ruta = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The email field must be provided')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class Usuarios(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    persona = models.ForeignKey(
        'core.Personas', models.DO_NOTHING,
        db_column='id_persona', blank=True, null=True
    )
    email = models.EmailField(unique=True, max_length=256, blank=True, null=True)
    password = models.CharField(max_length=256, db_column='password_hash', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    objects = UserManager()

    roles = models.ManyToManyField(
        Roles,
        through='UserRole',
        through_fields=('id_user', 'id_rol'),
        related_name='usuarios'
    )

    class Meta:
        managed = False
        db_table = 'usuarios'


class UserRole(BaseModel):
    id_rol = models.ForeignKey(Roles, models.DO_NOTHING, db_column='id_rol')
    id_user = models.ForeignKey(Usuarios, models.DO_NOTHING, db_column='id_user')

    class Meta:
        managed = False
        db_table = 'user_role'
        unique_together = (('id_rol', 'id_user'),)
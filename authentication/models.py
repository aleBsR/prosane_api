import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from common.models import BaseModel


class Roles(BaseModel):
    # La tabla real `roles` usa id INTEGER (igual que personas/user_role), no el
    # UUID que trae BaseModel. Override para que el modelo matchee la realidad y
    # los FKs a roles (p. ej. role_actions, user_role) resuelvan bien.
    # NOTA: mismo desfasaje pendiente en personas/user_role/pacientes (ver tarea de
    # reconciliación de schema).
    id = models.AutoField(primary_key=True)
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


class UserRole(models.Model):
    # Reconciliación de schema (#12): la tabla real `user_role` NO tiene las columnas
    # de auditoría de BaseModel — solo id (integer), id_rol, id_user, created_at,
    # updated_at. El modelo refleja exactamente eso (no hereda BaseModel) para que
    # los writes por ORM (seed_users, register, asignar_rol) funcionen.
    id = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Roles, models.DO_NOTHING, db_column='id_rol')
    id_user = models.ForeignKey(Usuarios, models.DO_NOTHING, db_column='id_user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'user_role'
        unique_together = (('id_rol', 'id_user'),)


# ───────────────────────────────────────────────────────────────────────────
# Permisos data-driven — Fase 2 (tablas propias, managed=True)
# Spec: docs/superpowers/specs/2026-06-09-permisos-data-driven-design.md §4
# A diferencia de las tablas de inspectdb (managed=False), estas 4 son nuevas y
# propias de esta feature → Django es dueño de su esquema (migraciones reales).
# ───────────────────────────────────────────────────────────────────────────

class Action(BaseModel):
    """Unidad de permiso + metadata visual liviana (contrato congelado del /me)."""
    name = models.CharField(max_length=64, unique=True)   # camelCase, clave de permiso
    label = models.CharField(max_length=191)
    icon = models.CharField(max_length=64, blank=True, null=True)
    color = models.CharField(max_length=9, blank=True, null=True)   # hex
    type = models.CharField(max_length=32)                # form | list | map
    category = models.CharField(max_length=32, blank=True, null=True)  # salud | administrativo | …
    is_sensitive = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'actions'

    def __str__(self):
        return self.name


class RoleAction(BaseModel):
    """Acciones que otorga un rol por defecto (base del cálculo de permisos)."""
    role = models.ForeignKey(Roles, on_delete=models.CASCADE, db_column='role_id', related_name='role_actions')
    action = models.ForeignKey(Action, on_delete=models.CASCADE, db_column='action_id', related_name='role_actions')

    class Meta:
        managed = True
        db_table = 'role_actions'
        unique_together = (('role', 'action'),)


class UserActionOverride(BaseModel):
    """Excepción manual: suma ('grant') o resta ('deny') una acción a un usuario."""
    GRANT = 'grant'
    DENY = 'deny'
    EFFECT_CHOICES = ((GRANT, 'grant'), (DENY, 'deny'))

    user = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column='user_id', related_name='action_overrides')
    action = models.ForeignKey(Action, on_delete=models.CASCADE, db_column='action_id', related_name='overrides')
    effect = models.CharField(max_length=8, choices=EFFECT_CHOICES)

    class Meta:
        managed = True
        db_table = 'user_action_overrides'
        unique_together = (('user', 'action'),)


class ActionLog(BaseModel):
    """Auditoría de uso de acciones sensibles. action_name es snapshot (no FK)."""
    user = models.ForeignKey(Usuarios, on_delete=models.SET_NULL, null=True, blank=True, db_column='user_id', related_name='action_logs')
    action_name = models.CharField(max_length=64)   # snapshot estable
    used_at = models.DateTimeField(db_index=True)
    context = models.JSONField(null=True, blank=True)   # sin DNI/diagnósticos en texto plano

    class Meta:
        managed = True
        db_table = 'action_logs'
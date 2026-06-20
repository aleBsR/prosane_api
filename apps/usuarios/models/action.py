
from django.db import models
from common.models import BaseModel


class Action(BaseModel):

    name = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=200)
    icon = models.CharField(max_length=64, blank=True, null=True)
    color = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=20)
    category = models.CharField(max_length=50, blank=True, null=True)
    is_sensitive = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'actions'
        ordering = ['category', 'sort_order']

    def __str__(self):
        return f'{self.label} ({self.name})'


class ActionRole(BaseModel):
    role = models.ForeignKey(
        'usuarios.Rol',
        on_delete=models.CASCADE,
        related_name='action_roles',
        db_column='id_rol',
    )
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name='action_roles',
        db_column='id_action',
    )

    class Meta:
        db_table = 'action_roles'
        unique_together = (('role', 'action'),)

    def __str__(self):
        return f'{self.role.rol} → {self.action.name}'





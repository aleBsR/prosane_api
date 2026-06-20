# Paso 02: Sistema de permisos data-driven

## Objetivo

Crear los modelos `Action` y `RoleAction`, el backend `ActionPermissionBackend`, el resolver `effective_actions`, y el permission class `require_action`.

## 1. Modelo Action

**Archivo:** `apps/usuarios/models/action.py`
```python
from django.db import models
from common.models import BaseModel


class Action(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=200)
    type = models.CharField(max_length=20, default='crud')
    category = models.CharField(max_length=50, blank=True, default='')
    is_sensitive = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'acciones'
        ordering = ['category', 'sort_order']

    def __str__(self):
        return f'{self.label} ({self.name})'
```

## 2. Modelo RoleAction

**Archivo:** `apps/usuarios/models/action.py`
```python
class RoleAction(BaseModel):
    role = models.ForeignKey(
        'usuarios.Rol', on_delete=models.CASCADE, related_name='role_actions',
    )
    action = models.ForeignKey(
        Action, on_delete=models.CASCADE, related_name='role_actions',
    )

    class Meta:
        db_table = 'roles_acciones'
        unique_together = ('role', 'action')

    def __str__(self):
        return f'{self.role.rol} → {self.action.name}'
```

## 3. ActionPermissionBackend + effective_actions

**Archivo:** `apps/usuarios/action_resolution.py`
```python
from django.contrib.auth.backends import BaseBackend
from .models import Action
from .models.action import RoleAction


class ActionPermissionBackend(BaseBackend):
    def has_perm(self, user_obj, perm):
        return perm in self.get_all_permissions(user_obj)

    def get_all_permissions(self, user_obj):
        if user_obj.is_superuser:
            return set(
                Action.objects.filter(is_active=True)
                .values_list('name', flat=True)
            )
        return set(
            RoleAction.objects.filter(
                role__roleusuario__id_user=user_obj,
                action__is_active=True,
            ).values_list('action__name', flat=True)
        )


def effective_actions(user):
    """Retorna las acciones del user como lista de dicts (para endpoint /me)."""
    if user.is_superuser:
        qs = Action.objects.filter(is_active=True)
    else:
        qs = Action.objects.filter(
            role_actions__role__roleusuario__id_user=user,
            is_active=True,
        ).distinct()
    return list(qs.values(
        'name', 'label', 'type', 'category', 'is_sensitive', 'sort_order',
    ))
```

## 4. Permission class require_action

**Archivo:** `apps/usuarios/permissions.py`
```python
from rest_framework.permissions import BasePermission


def require_action(action_name):
    class RequireAction(BasePermission):
        def has_permission(self, request, view):
            return request.user.has_perm(action_name)
    return RequireAction
```

**Nota:** `request.user.has_perm()` delega en `ActionPermissionBackend` (registrado en settings paso 01).

## 5. Migrar

```bash
python manage.py makemigrations usuarios
python manage.py migrate usuarios
```

## 6. Tests

**Archivo:** `apps/usuarios/tests.py`
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.usuarios.models.action import Action, RoleAction
from apps.usuarios.models import Rol
from apps.usuarios.action_resolution import effective_actions

Usuario = get_user_model()


class PermissionTest(TestCase):
    def setUp(self):
        self.action = Action.objects.create(
            name='test_action', label='Test Action',
        )
        self.rol = Rol.objects.create(rol='test_role')
        RoleAction.objects.create(role=self.rol, action=self.action)
        self.user = Usuario.objects.create_user(
            email='test@test.com', password='test1234',
        )
        self.user.roles.add(self.rol)

    def test_require_action_passes(self):
        from apps.usuarios.permissions import require_action
        perm = require_action('test_action')()
        request = type('Req', (), {'user': self.user, 'method': 'GET'})()
        self.assertTrue(perm.has_permission(request, None))

    def test_require_action_fails_without_role(self):
        user2 = Usuario.objects.create_user(
            email='no_role@test.com', password='test1234',
        )
        from apps.usuarios.permissions import require_action
        perm = require_action('test_action')()
        request = type('Req', (), {'user': user2, 'method': 'GET'})()
        self.assertFalse(perm.has_permission(request, None))

    def test_superuser_bypasses(self):
        admin = Usuario.objects.create_superuser(
            email='admin@test.com', password='test1234',
        )
        from apps.usuarios.permissions import require_action
        perm = require_action('nonexistent')()
        request = type('Req', (), {'user': admin, 'method': 'GET'})()
        self.assertTrue(perm.has_permission(request, None))

    def test_effective_actions_returns_list(self):
        actions = effective_actions(self.user)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['name'], 'test_action')
```

```bash
python manage.py test apps.usuarios.tests.PermissionTest
```

## Criterio de aceptación

- `Action` + `RoleAction` creados en tablas `acciones` y `roles_acciones`
- `ActionPermissionBackend` resuelve permisos vía DB
- `effective_actions(user)` devuelve lista de acciones del usuario
- `require_action` usa `has_perm()` que delega en el backend
- Superuser bypass: ve todas las acciones activas
- Tests pasan

"""Resolución de acciones desde la DB (Slice 2) + backend de permisos de Django.

Resolución computada en vivo (spec §5): acciones efectivas =
   (⋃ role_actions de los roles del usuario) ∪ grants − denies   [superuser → catálogo].

El backend (spec §6) engancha esto al motor nativo de Django (has_perm / decoradores /
DRF) leyendo de las mismas tablas, sin usar auth.Permission/Group.
"""
from django.contrib.auth.backends import BaseBackend

from authentication.models import Action, RoleAction, UserActionOverride


def _action_to_dict(a):
    # Orden de claves idéntico al mapa en código (actions_map._a) → JSON byte-por-byte.
    return {
        "name": a.name,
        "label": a.label,
        "icon": a.icon,
        "color": a.color,
        "type": a.type,
        "category": a.category,
        "is_sensitive": a.is_sensitive,
        "sort_order": a.sort_order,
    }


def effective_actions(user):
    """Acciones efectivas del usuario (lista de dicts con las 8 claves, ordenada)."""
    if getattr(user, "is_superuser", False):
        actions = Action.objects.filter(is_active=True)
    else:
        role_ids = list(user.roles.values_list("id", flat=True))
        from_roles = set(
            RoleAction.objects.filter(role_id__in=role_ids).values_list("action_id", flat=True)
        )
        grants = set(
            UserActionOverride.objects.filter(user=user, effect=UserActionOverride.GRANT)
            .values_list("action_id", flat=True)
        )
        denies = set(
            UserActionOverride.objects.filter(user=user, effect=UserActionOverride.DENY)
            .values_list("action_id", flat=True)
        )
        action_ids = (from_roles | grants) - denies
        actions = Action.objects.filter(id__in=action_ids, is_active=True)

    dicts = [_action_to_dict(a) for a in actions]
    return sorted(dicts, key=lambda a: (a["sort_order"], a["name"]))


class ActionPermissionBackend(BaseBackend):
    """Resuelve permisos por nombre de acción desde la DB. No participa del login."""

    def authenticate(self, request, **kwargs):
        return None

    def get_all_permissions(self, user_obj, obj=None):
        if not getattr(user_obj, "is_active", False) or getattr(user_obj, "is_anonymous", True):
            return set()
        cache = getattr(user_obj, "_action_perm_cache", None)
        if cache is None:
            cache = {a["name"] for a in effective_actions(user_obj)}
            user_obj._action_perm_cache = cache
        return cache

    def has_perm(self, user_obj, perm, obj=None):
        return perm in self.get_all_permissions(user_obj, obj)

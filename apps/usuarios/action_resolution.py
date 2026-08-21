from django.contrib.auth.backends import BaseBackend

from apps.usuarios.models.action import Action, ActionRole


def _action_to_dict(action):
    """Convierte una Action en el dict del contrato del /me."""
    return {
        "name": action.name,
        "label": action.label,
        "icon": action.icon,
        "color": action.color,
        "type": action.type,
        "category": action.category,
        "is_sensitive": action.is_sensitive,
        "sort_order": action.sort_order,
        "show_in_menu": action.show_in_menu,
    }


def effective_actions(user):
    """Devuelve todas las acciones efectivas del usuario (permisos reales)."""
    role_ids = list(user.roles.values_list("id", flat=True))
    action_ids = set(
        ActionRole.objects.filter(role_id__in=role_ids)
        .values_list("action_id", flat=True)
    )
    actions = Action.objects.filter(id__in=action_ids, is_active=True)

    return sorted(
        [_action_to_dict(a) for a in actions],
        key=lambda a: (a["sort_order"], a["name"]),
    )


def effective_menu_actions(user):
    """Devuelve las acciones que deben renderizarse como tiles del menú principal.

    Las acciones con `show_in_menu=False` otorgan permiso para ejecutar una
    funcionalidad contextual (ej. dentro de un operativo) pero no se renderizan
    como tile.
    """
    return [a for a in effective_actions(user) if a.get("show_in_menu", True)]


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

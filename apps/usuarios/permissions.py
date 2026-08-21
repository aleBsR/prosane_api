from rest_framework.permissions import IsAuthenticated


class EsAdmin(IsAuthenticated):
    """Gate de bootstrap admin (superuser).

    Se usa solo en endpoints administrativos que no se modelan como acciones por rol.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.is_superuser


def require_action(action_name):
    """Enforcement server-side por acción (data-driven).

    Permission class de DRF que exige que el usuario TENGA la acción, resuelta vía
    `request.user.has_perm(action_name)` → ActionPermissionBackend (lee de la DB).
    - Sin autenticar → 401.
    - Autenticado sin la acción → 403.
    - Superuser → pasa (short-circuit de Django).

    Uso: permission_classes = [require_action('verFichaClinica')]
    """

    class _RequireAction(IsAuthenticated):
        def has_permission(self, request, view):
            if not super().has_permission(request, view):
                return False
            return bool(request.user.has_perm(action_name))

    return _RequireAction


def require_any_action(*action_names):
    """Permission class that accepts any one of the supplied actions."""
    if not action_names:
        raise ValueError("require_any_action necesita al menos una acción")

    class _RequireAnyAction(IsAuthenticated):
        def has_permission(self, request, view):
            if not super().has_permission(request, view):
                return False
            return any(request.user.has_perm(name) for name in action_names)

    return _RequireAnyAction

from rest_framework.permissions import IsAuthenticated


class EsAdmin(IsAuthenticated):
    """Gate de bootstrap admin (superuser).

    Se usa solo en endpoints administrativos que no se modelan como acciones por rol.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.is_superuser


def _check_must_change(request):
    """Si must_change_password, solo permite /auth/change-password/, /auth/logout/, /auth/me/, /auth/refresh/."""
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False) and getattr(user, 'must_change_password', False):
        from django.utils import timezone
        from rest_framework.exceptions import PermissionDenied
        exp = getattr(user, 'temporal_password_expires_at', None)
        path = getattr(request, 'path', '') or ''
        allowed = (
            "/api/v1/auth/change-password/",
            "/api/v1/auth/logout/",
            "/api/v1/auth/me/",
            "/api/v1/auth/refresh/",
            "/api/v1/auth/token/refresh/",
        )
        if exp and exp < timezone.now():
            # Expirada: bloquear todo salvo logout/me para poder mostrar mensaje
            if not any(path.startswith(p) for p in ("/api/v1/auth/logout/", "/api/v1/auth/me/")):
                raise PermissionDenied({"code": "TEMP_EXPIRED", "detail": "Tu contraseña temporal expiró (72h). Contactá al administrador para que te reenvíe una nueva."})
            # Para /me y logout permitimos, pero para change-password con temp expirada también bloqueamos
            if path.startswith("/api/v1/auth/change-password/"):
                raise PermissionDenied({"code": "TEMP_EXPIRED", "detail": "Tu contraseña temporal expiró (72h). Contactá al administrador para que te reenvíe una nueva."})
        if not any(path.startswith(p) for p in allowed):
            raise PermissionDenied({"code": "MUST_CHANGE_PASSWORD", "detail": "Debes cambiar tu contraseña temporal antes de continuar."})
    return True


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
            _check_must_change(request)
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
            _check_must_change(request)
            return any(request.user.has_perm(name) for name in action_names)

    return _RequireAnyAction


class MustChangePasswordBlock(IsAuthenticated):
    """Mantener por compatibilidad con DEFAULT_PERMISSION_CLASSES. Delega a _check_must_change."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        _check_must_change(request)
        return True


class MustChangePasswordBlock(IsAuthenticated):
    """Bloquea toda API salvo cambio de contraseña si must_change_password es True.

    - Si temporal_password_expires_at expiró (72h) → 403 TEMP_EXPIRED.
    - Si must_change_password → solo permite /auth/change-password/, /auth/logout/, /auth/me/ y /auth/refresh/.
    """

    ALLOWED_PATHS = (
        "/api/v1/auth/change-password/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/me/",
        "/api/v1/auth/refresh/",
        "/api/v1/auth/token/refresh/",
    )

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'must_change_password', False):
            return True
        from django.utils import timezone
        from rest_framework.exceptions import PermissionDenied
        exp = getattr(user, 'temporal_password_expires_at', None)
        if exp and exp < timezone.now():
            raise PermissionDenied({
                'code': 'TEMP_EXPIRED',
                'detail': 'Tu contraseña temporal expiró (72h). Contactá al administrador para que te reenvíe una nueva.',
            })
        path = getattr(request, 'path', '') or ''
        for allowed in self.ALLOWED_PATHS:
            if path.startswith(allowed):
                return True
        raise PermissionDenied({
            'code': 'MUST_CHANGE_PASSWORD',
            'detail': 'Debes cambiar tu contraseña temporal antes de continuar.',
        })

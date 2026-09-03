from django.http import JsonResponse
from django.utils import timezone


ALLOWED_PREFIXES = (
    "/api/v1/auth/change-password/",
    "/api/v1/auth/logout/",
    "/api/v1/auth/me/",
    "/api/v1/auth/refresh/",
    "/api/v1/auth/token/refresh/",
)


class MustChangePasswordMiddleware:
    """Bloquea toda API si must_change_password y no está en lista blanca. 403 con código."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        import sys
        print(f"[MustChange] {request.path} user={getattr(user,'email','anon') if user else 'none'} must={getattr(user,'must_change_password',False) if user else 'no'} auth={getattr(user,'is_authenticated',False) if user else 'no'}", file=sys.stderr)
        if user and getattr(user, 'is_authenticated', False) and getattr(user, 'must_change_password', False):
            path = request.path or ""
            # Permitir solo los prefijos de cambio/logout/me
            if not any(path.startswith(p) for p in ALLOWED_PREFIXES):
                exp = getattr(user, 'temporal_password_expires_at', None)
                if exp and exp < timezone.now():
                    return JsonResponse(
                        {"code": "TEMP_EXPIRED", "detail": "Tu contraseña temporal expiró (72h). Contactá al administrador para que te reenvíe una nueva."},
                        status=403,
                    )
                return JsonResponse(
                    {"code": "MUST_CHANGE_PASSWORD", "detail": "Debes cambiar tu contraseña temporal antes de continuar."},
                    status=403,
                )
            # Si está en la lista blanca pero expiró, también bloquear incluso ahí (salvo logout)
            if any(path.startswith(p) for p in ALLOWED_PREFIXES):
                exp = getattr(user, 'temporal_password_expires_at', None)
                if exp and exp < timezone.now() and not path.startswith("/api/v1/auth/logout/"):
                    # Permitir me para que el frontend pueda mostrar el mensaje, pero bloquear change con temp expirada
                    # El change-password con temp expirada debería fallar por check_password (temp sigue válida) pero el permiso de expiración lo bloquea acá
                    # Devolvemos 403 para que el frontend sepa que debe pedir reenvío
                    return JsonResponse(
                        {"code": "TEMP_EXPIRED", "detail": "Tu contraseña temporal expiró (72h). Contactá al administrador para que te reenvíe una nueva."},
                        status=403,
                    )
        return self.get_response(request)

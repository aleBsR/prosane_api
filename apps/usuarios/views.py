from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.tutores.models import Tutor
from apps.usuarios.action_resolution import effective_actions


class LoginView(TokenObtainPairView):
    """POST /auth/login/ — devuelve access + refresh tokens."""
    permission_classes = [AllowAny]


class RefreshView(TokenRefreshView):
    """POST /auth/refresh/ — devuelve un nuevo access token."""
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """POST /auth/logout/ — invalida el refresh token (blacklist)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET /auth/me/ — contrato congelado: user + roles + actions + meta."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        persona = getattr(user, "persona", None)
        tutor = Tutor.objects.filter(usuario=user).first()
        roles = [
            {"name": r.rol, "label": r.rol.capitalize()}
            for r in user.roles.all()
        ]
        data = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "nombre": getattr(persona, "nombre", "") or "",
                "apellido": getattr(persona, "apellido", "") or "",
                "is_staff": user.is_staff,
                "tutor_id": str(tutor.id) if tutor else None,
            },
            "roles": roles,
            "actions": effective_actions(user),
            "meta": {
                "version": "1",
                "permissions_synced_at": timezone.now().isoformat(),
            },
        }
        return Response(data)

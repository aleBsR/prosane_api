from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.usuarios.serializers import UserSerializer
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
    """GET /auth/me/ — perfil del usuario autenticado + roles + acciones."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        data = serializer.data
        data['roles'] = list(user.roles.values('id', 'rol'))
        data['actions'] = effective_actions(user)
        return Response(data)

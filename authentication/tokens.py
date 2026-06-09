"""Token JWT con claim `roles` (login del front).

`/api/v1/auth/token/`         → access + refresh (ambos con el claim `roles`)
`/api/v1/auth/token/refresh/` → nuevo access (hereda `roles` del refresh)

El refresh de simplejwt copia los claims al access regenerado, así que basta con
inyectar `roles` en el token de get_token para que ambos lo lleven y el refresh lo
preserve (incluso con ROTATE_REFRESH_TOKENS activo).
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from authentication.serializers import RolesSerializer


class RolesTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["roles"] = RolesSerializer(user.roles.all(), many=True).data
        return token


class RolesTokenObtainPairView(TokenObtainPairView):
    serializer_class = RolesTokenObtainPairSerializer

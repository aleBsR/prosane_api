from rest_framework import serializers
from apps.usuarios.models import Usuario, Rol, RoleUsuario


class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = "__all__"


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleUsuario
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "email", "persona", "is_active", "is_staff"]
        read_only_fields = ["id"]

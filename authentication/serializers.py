from rest_framework import serializers
from authentication.models import Roles, UserRole, Usuarios


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True) 
    #Esto asegura que la contraseña no se incluya en la representación serializada del usuario,
    #pero aún se pueda proporcionar al crear o actualizar un usuario.
    class Meta:
        model = Usuarios
        fields = ['id', 'email', 'password', 'persona']
        read_only_fields = ['id']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        user = Usuarios.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            persona=validated_data.get('persona'),
        )
        return user

class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ['rol', 'ruta']
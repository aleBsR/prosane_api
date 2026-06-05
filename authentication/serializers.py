from rest_framework import serializers
from django.contrib.auth import authenticate
from authentication.models import Roles, UserRole, Usuarios
from core.serializers import PersonasSerializer
from core.models import Personas

from django.db import transaction
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True) 
    #Esto asegura que la contraseña no se incluya en la representación serializada del usuario,

    #por el body se manda persona={JSON}
    persona = PersonasSerializer()
     

    class Meta:
        model = Usuarios
        fields = ['id', 'email', 'password', 'persona']
        read_only_fields = ['id']
        extra_kwargs = {
            'password': {'write_only': True},
        }

  
    @transaction.atomic
    def create(self, validated_data):

        persona_data = validated_data.pop('persona')
        persona = Personas.objects.create(**persona_data)
        user = Usuarios.objects.create_user(
            persona=persona,
            **validated_data
        )
        # por defecto el rol sera usuario
        UserRole.objects.create(
            id_rol= Roles.objects.get(rol='usuario'),
            id_user=user
        )
    
        return user

class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ['rol', 'ruta']

class UserRoleSerializer(serializers.ModelSerializer):

    id_rol = serializers.SlugRelatedField(
        slug_field='rol', #devuel rol en ves del id
        queryset=Roles.objects.all() # mapea en la db el rol
    )

    class Meta:
        model = UserRole
        fields =['id_rol'] #lo que se muestra y viaja por body

    def validate(self, attrs):
        # id_user viene por context, no por body — el unique_together automático
        # de DRF no lo cubre porque id_user no está en fields
        if UserRole.objects.filter(
            id_user=self.context['id_user'],
            id_rol=attrs['id_rol']
        ).exists():
            raise serializers.ValidationError('User already has this role')
        return attrs


class LoginSerializer(serializers.Serializer):
    # Serializer plano (no ModelSerializer) porque login no crea ni modifica modelos
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        # authenticate() usa el backend de Django configurado (USERNAME_FIELD='email')
        user = authenticate(
            request=self.context.get('request'),
            username=attrs['email'],
            password=attrs['password']
        )
        if not user:
            raise serializers.ValidationError('Invalid email or password')
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled')
        #Guardamos el user en attrs para que la vista lo use (generar JWT),
        #pero no se expone en validated_data para evitar incluirlo en la respuesta
        attrs['user'] = user
        return attrs
        
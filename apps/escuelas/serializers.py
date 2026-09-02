from rest_framework import serializers
from apps.personas.models import Domicilio
from apps.personas.serializers import DomicilioSerializer
from apps.usuarios.models import Usuario
from .models import Escuela, Curso


class UsuarioEscuelaSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['id', 'email', 'nombre', 'roles', 'is_active']

    def get_nombre(self, obj):
        if obj.persona:
            return f'{obj.persona.nombre} {obj.persona.apellido}'.strip()
        return ''

    def get_roles(self, obj):
        return list(obj.roles.values_list('rol', flat=True))


class EscuelaSerializer(serializers.ModelSerializer):
    domicilio = DomicilioSerializer(required=False, allow_null=True)
    usuarios_asociados = serializers.SerializerMethodField()

    class Meta:
        model = Escuela
        fields = [
            'id', 'nombre', 'cue', 'ambito', 'sector_gestion',
            'modalidad_educativa', 'intercultural_bilingue', 'plurigrado_rural',
            'domicilio', 'telefono', 'activa', 'usuarios_asociados',
        ]
    read_only_fields = ['id']

    def get_usuarios_asociados(self, obj):
        return UsuarioEscuelaSerializer(obj.usuarios_escuela.all(), many=True).data

    def create(self, validated_data):
        domicilio_data = validated_data.pop('domicilio', None)
        if domicilio_data:
            domicilio = Domicilio.objects.create(**domicilio_data)
            validated_data['domicilio'] = domicilio
        return super().create(validated_data)

    def update(self, instance, validated_data):
        domicilio_data = validated_data.pop('domicilio', None)
        if domicilio_data:
            if instance.domicilio:
                for key, value in domicilio_data.items():
                    setattr(instance.domicilio, key, value)
                instance.domicilio.save()
            else:
                instance.domicilio = Domicilio.objects.create(**domicilio_data)
        return super().update(instance, validated_data)


class EscuelaListSerializer(serializers.ModelSerializer):
    localidad = serializers.SerializerMethodField()
    usuarios_asociados = serializers.SerializerMethodField()

    class Meta:
        model = Escuela
        fields = ['id', 'nombre', 'cue', 'ambito', 'activa', 'localidad', 'usuarios_asociados']

    def get_usuarios_asociados(self, obj):
        return UsuarioEscuelaSerializer(obj.usuarios_escuela.all(), many=True).data

    def get_localidad(self, obj):
        if obj.domicilio:
            return obj.domicilio.localidad
        return ''


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = '__all__'
        read_only_fields = ['id']
        extra_kwargs = {
            'escuela': {'required': False},
        }

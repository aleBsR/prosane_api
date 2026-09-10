from django.db import models
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
        fields = ['id', 'nombre', 'cue', 'ambito', 'activa', 'localidad', 'usuarios_asociados',
                  'plurigrado_rural']

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
        # La unicidad se valida en validate() porque la escuela en el
        # POST viene por URL (contexto), no en el body. El validador
        # automático de DRF exigiría 'escuela' en el body y rompería el flujo.
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        from apps.escuelas.models.curso import normalizar_division, normalizar_grado

        escuela = attrs.get('escuela')
        if escuela is None:
            escuela = self.context.get('escuela')
        if escuela is None and self.instance is not None:
            escuela = self.instance.escuela
        if escuela is None:
            return attrs

        grado = attrs.get('sala_grado_anio', getattr(self.instance, 'sala_grado_anio', ''))
        division = attrs.get('division', getattr(self.instance, 'division', ''))
        ciclo = attrs.get('ciclo_lectivo', getattr(self.instance, 'ciclo_lectivo', None))
        escuela_id = getattr(escuela, 'id', escuela)

        qs = Curso.objects.filter(
            escuela_id=escuela_id,
            sala_grado_anio__iexact=normalizar_grado(grado),
            division__iexact=normalizar_division(division),
        )
        if ciclo is not None:
            qs = qs.filter(
                models.Q(ciclo_lectivo=ciclo)
                | models.Q(ciclo_lectivo__isnull=True)
            )
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'Ya existe un curso con ese grado, división y ciclo lectivo en esta escuela.'
            )
        return attrs

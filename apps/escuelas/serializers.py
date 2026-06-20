from rest_framework import serializers
from apps.personas.models import Domicilio
from apps.personas.serializers import DomicilioSerializer
from .models import Escuela, Curso


class EscuelaSerializer(serializers.ModelSerializer):
    domicilio = DomicilioSerializer(required=False, allow_null=True)

    class Meta:
        model = Escuela
        fields = [
            'id', 'nombre', 'cue', 'ambito', 'sector_gestion',
            'modalidad_educativa', 'intercultural_bilingue', 'plurigrado_rural',
            'domicilio', 'telefono', 'activa',
        ]
        read_only_fields = ['id']

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

    class Meta:
        model = Escuela
        fields = ['id', 'nombre', 'cue', 'ambito', 'activa', 'localidad']

    def get_localidad(self, obj):
        if obj.domicilio:
            return obj.domicilio.localidad
        return ''


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = '__all__'
        read_only_fields = ['id']

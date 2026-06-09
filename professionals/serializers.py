from rest_framework import serializers
from django.db import transaction
from core.serializers import PersonasSerializer
from core.models import Personas
from authentication.models import Usuarios
from .models import Profesionales
from .services.services_refeps import RefepsService


class ProfesionalesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profesionales
        fields = ['id', 'matricula']


class ProfesionalPerfilSerializer(serializers.Serializer):
    email = serializers.EmailField(read_only=True)
    persona = PersonasSerializer(read_only=True)
    profesional = ProfesionalesSerializer(read_only=True)

    @transaction.atomic
    def update(self, instance, validated_data):
        user = instance['user']
        persona = instance['persona_obj']
        profesional = instance['profesional_obj']

        persona_data = validated_data.get('persona', {})
        for attr, value in persona_data.items():
            setattr(persona, attr, value)
        persona.save()

        return {
            'email': user.email,
            'persona': persona,
            'profesional': profesional,
        }


class ValidarMatriculaSerializer(serializers.Serializer):
    matricula = serializers.CharField(max_length=50)

    def validate_matricula(self, value):
        datos = RefepsService.consultar(value)
        if datos is None:
            raise serializers.ValidationError('Matrícula no válida o no encontrada')
        return value

from rest_framework import serializers
from .models import Personas, Domicilio


class PersonasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personas
        fields = '__all__'

        # No se muestra en la salida pero es necesario para 
        # validar que se proporcionen estos campos al crear una persona.
        extra_kwargs = {
            'dni': {'required': True},
            'tipo_dni': {'required': True}
        }

class DomicilioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domicilio
        fields = '__all__'
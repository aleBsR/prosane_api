from rest_framework import serializers
from apps.personas.models import Persona, Domicilio


class PersonasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = "__all__"


class DomicilioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domicilio
        fields = "__all__"

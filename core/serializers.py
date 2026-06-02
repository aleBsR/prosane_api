

from rest_framework import serializers
from .models import Personas



class PersonasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personas
        fields = '__all__'

        extra_kwargs = {
            'dni': {'required': True},
            'tipo_dni': {'required': True}
        }
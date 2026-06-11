from rest_framework import serializers
from .models import Personas, Domicilio


class PersonasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Personas
        # Lista explícita (no __all__): tabla con datos de menores (Ley 25.326).
        fields = ['id', 'nombre', 'apellido', 'dni', 'tipo_dni', 'sexo', 'fecha_nacimiento']
        extra_kwargs = {
            # dni: se acepta al CREAR (input) pero NUNCA se devuelve en respuestas.
            # Si un endpoint puntual necesita mostrar DNI → serializer dedicado con su control.
            'dni': {'required': True, 'write_only': True},
            'tipo_dni': {'required': True},
        }


class DomicilioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domicilio
        # Lista explícita (no __all__): solo los campos de dirección, sin metadata de
        # auditoría. Domicilio de un menor también es dato personal.
        fields = [
            'id', 'calle', 'nro_calle', 'piso', 'dpto', 'manzana', 'casa',
            'nro_casa', 'pieza', 'provincia', 'departamento', 'localidad',
        ]

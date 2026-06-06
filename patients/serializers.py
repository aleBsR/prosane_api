from rest_framework import serializers
from django.db import transaction
from core.models import Personas, Domicilio
from core.serializers import PersonasSerializer, DomicilioSerializer
from .models import Pacientes, Responsables, Antecedentesfamiliares, Antecedentespersonales

class ResponsablesSerializer(serializers.ModelSerializer):
    # La ForeignKey en el modelo Responsables ahora se llama 'persona'
    persona = PersonasSerializer()

    class Meta:
        model = Responsables
        fields = ['id', 'persona', 'parentesco']

    @transaction.atomic
    def create(self, validated_data):
        persona_data = validated_data.pop('persona')
        persona = Personas.objects.create(**persona_data)
        responsable = Responsables.objects.create(persona=persona, **validated_data)
        return responsable

    @transaction.atomic
    def update(self, instance, validated_data):
        persona_data = validated_data.pop('persona', None)
        if persona_data:
            persona = instance.persona
            for attr, value in persona_data.items():
                setattr(persona, attr, value)
            persona.save()
        
        instance.parentesco = validated_data.get('parentesco', instance.parentesco)
        instance.save()
        return instance


class PacientesSerializer(serializers.ModelSerializer):
    # Las ForeignKeys en Pacientes ahora se llaman 'persona', 'domicilio', 'responsable'
    persona = PersonasSerializer()
    domicilio = DomicilioSerializer()

    class Meta:
        model = Pacientes
        fields = [
            'id', 'persona', 'domicilio', 'responsable',
            'edad', 'tiene_cud', 'tipo_cobertura', 'nombre_cobertura'
        ]

    @transaction.atomic
    def create(self, validated_data):
        persona_data = validated_data.pop('persona')
        domicilio_data = validated_data.pop('domicilio')

        # 1. Crear Persona
        persona = Personas.objects.create(**persona_data)

        # 2. Crear Domicilio
        domicilio = Domicilio.objects.create(**domicilio_data)

        # 3. Crear Paciente
        paciente = Pacientes.objects.create(
            persona=persona,
            domicilio=domicilio,
            **validated_data
        )
        return paciente

    @transaction.atomic
    def update(self, instance, validated_data):
        persona_data = validated_data.pop('persona', None)
        domicilio_data = validated_data.pop('domicilio', None)

        # 1. Actualizar Persona
        if persona_data:
            persona = instance.persona
            for attr, value in persona_data.items():
                setattr(persona, attr, value)
            persona.save()

        # 2. Actualizar Domicilio
        if domicilio_data:
            domicilio = instance.domicilio
            for attr, value in domicilio_data.items():
                setattr(domicilio, attr, value)
            domicilio.save()

        # 3. Actualizar Paciente
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

    def to_representation(self, instance):
        # Personalizamos la salida para que sea más amigable para el frontend
        rep = super().to_representation(instance)
        if instance.responsable:
            rep['responsable_detalle'] = {
                'id': instance.responsable.id,
                'parentesco': instance.responsable.parentesco,
                'nombre': instance.responsable.persona.nombre if instance.responsable.persona else "",
                'apellido': instance.responsable.persona.apellido if instance.responsable.persona else ""
            }
        return rep


class AntecedentesfamiliaresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Antecedentesfamiliares
        fields = '__all__'


class AntecedentespersonalesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Antecedentespersonales
        fields = '__all__'

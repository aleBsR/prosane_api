from rest_framework import serializers
from django.db import transaction
from core.models import Personas, Domicilio
from core.serializers import PersonasSerializer, DomicilioSerializer
from .models import Pacientes, Responsables, Antecedentesfamiliares, Antecedentespersonales

class ResponsablesSerializer(serializers.ModelSerializer):

    #Persona ya no tiene FK en Responsable
    # Porque Responsable sera un usuario (tendra su parte visual...)
    class Meta:
        model = Responsables
        fields = ['id', 'usuario', 'parentesco']

    #@transaction.atomic
    def create(self, validated_data):
        #el usuario viene en validated_data
        responsable = Responsables.objects.create(**validated_data)
        return responsable

        #persona_data = validated_data.pop('id_persona')
        #persona = Personas.objects.create(**persona_data)
        #responsable = Responsables.objects.create(id_persona=persona, **validated_data)
        #return responsable

    @transaction.atomic
    def update(self, instance, validated_data):
       # persona_data = validated_data.pop('id_persona', None)
        #if persona_data:
         #   persona = instance.id_persona
          #  for attr, value in persona_data.items():
           #     setattr(persona, attr, value)
            #persona.save()
        instance.parentesco = validated_data.get('parentesco', instance.parentesco)
        instance.save()
        return instance


class PacientesSerializer(serializers.ModelSerializer):
    # Usamos 'source' para renombrar las claves en el JSON de salida a nombres más limpios
    persona = PersonasSerializer(source='id_persona')
    domicilio = DomicilioSerializer(source='id_domicilio')

    class Meta:
        model = Pacientes
        fields = [
            'id', 'persona', 'domicilio', 'id_responsable',
            'sexo', 'fecha_nacimiento', 'edad', 'tiene_cud',
            'tipo_cobertura', 'nombre_cobertura'
        ]

    @transaction.atomic
    def create(self, validated_data):
        persona_data = validated_data.pop('id_persona')
        domicilio_data = validated_data.pop('id_domicilio')

        # 1. Crear Persona
        persona = Personas.objects.create(**persona_data)

        # 2. Crear Domicilio
        domicilio = Domicilio.objects.create(**domicilio_data)

        # 3. Crear Paciente
        paciente = Pacientes.objects.create(
            id_persona=persona,
            id_domicilio=domicilio,
            **validated_data
        )
        return paciente

    @transaction.atomic
    def update(self, instance, validated_data):
        persona_data = validated_data.pop('id_persona', None)
        domicilio_data = validated_data.pop('id_domicilio', None)

        # 1. Actualizar Persona
        if persona_data:
            persona = instance.id_persona
            for attr, value in persona_data.items():
                setattr(persona, attr, value)
            persona.save()

        # 2. Actualizar Domicilio
        if domicilio_data:
            domicilio = instance.id_domicilio
            for attr, value in domicilio_data.items():
                setattr(domicilio, attr, value)
            domicilio.save()

        # 3. Actualizar Paciente
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.id_responsable and instance.id_responsable.persona:
            persona = instance.id_responsable.persona
            rep['responsable_detalle'] = {
                'id': instance.id_responsable.id,
                'parentesco': instance.id_responsable.parentesco,
                'nombre': persona.nombre or '',
                'apellido': persona.apellido or ''
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

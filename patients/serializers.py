from rest_framework import serializers
from django.db import transaction
from core.models import Personas, Domicilio
from core.serializers import PersonasSerializer, DomicilioSerializer
from .models import Pacientes, Responsables, Antecedentesfamiliares, Antecedentespersonales, Consentimiento


class ResponsablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Responsables
        # Reconciliación #12: campos explícitos del modelo reconciliado (sin auditoría).
        fields = ['id', 'usuario', 'persona', 'parentesco']

    def create(self, validated_data):
        responsable = Responsables.objects.create(**validated_data)
        return responsable

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.parentesco = validated_data.get('parentesco', instance.parentesco)
        instance.save()
        return instance


class PacientesSerializer(serializers.ModelSerializer):
    # Reconciliación #12: sin AuditSerializerMixin — la tabla no tiene columnas de auditoría.
    persona = PersonasSerializer()
    domicilio = DomicilioSerializer()

    class Meta:
        model = Pacientes
        # Campos explícitos del modelo reconciliado (sin columnas de auditoría).
        fields = [
            'id', 'persona', 'domicilio', 'responsable',
            'edad', 'tiene_cud', 'tipo_cobertura', 'nombre_cobertura'
        ]

    @transaction.atomic
    def create(self, validated_data):
        persona_data = validated_data.pop('persona')
        domicilio_data = validated_data.pop('domicilio')

        persona = Personas.objects.create(**persona_data)
        domicilio = Domicilio.objects.create(**domicilio_data)
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

        if persona_data:
            persona = instance.persona
            for attr, value in persona_data.items():
                setattr(persona, attr, value)
            persona.save()

        # Actualizar Domicilio
        if domicilio_data:
            domicilio = instance.domicilio
            for attr, value in domicilio_data.items():
                setattr(domicilio, attr, value)
            domicilio.save()

        # Actualizar Paciente
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.responsable and instance.responsable.persona:
            persona = instance.responsable.persona
            rep['responsable_detalle'] = {
                'id': instance.responsable.id,
                'parentesco': instance.responsable.parentesco,
                'nombre': persona.nombre or '',
                'apellido': persona.apellido or ''
            }
        return rep


class AntecedentesfamiliaresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Antecedentesfamiliares
        fields = ['problemas_salud', 'detalle_problema_salud', 'familiar_con_muerte_subita']


class AntecedentespersonalesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Antecedentespersonales
        exclude = ['antecedente', 'paciente']


class ConsentimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consentimiento
        fields = ['id', 'paciente', 'firma_tipo', 'adulto_nombre', 'adulto_apellido',
                  'adulto_tipo_documento', 'adulto_dni', 'firma_hash', 'fecha_firma']
        extra_kwargs = {'adulto_dni': {'write_only': True}}
        read_only_fields = ['firma_hash', 'fecha_firma']

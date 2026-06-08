from rest_framework import serializers
from django.db import transaction
from core.models import Personas, Domicilio
from core.serializers import PersonasSerializer, DomicilioSerializer
from common.serializers import AuditSerializerMixin
from .models import Pacientes, Responsables, Antecedentesfamiliares, Antecedentespersonales

class ResponsablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Responsables
        fields = ['id', 'usuario', 'persona', 'parentesco']

    def create(self, validated_data):
        responsable = Responsables.objects.create(**validated_data)
        return responsable

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.parentesco = validated_data.get('parentesco', instance.parentesco)
        instance.save()
        return instance


class PacientesSerializer(AuditSerializerMixin, serializers.ModelSerializer):
    persona = PersonasSerializer()
    domicilio = DomicilioSerializer()

    class Meta:
        model = Pacientes
        fields = [
            'id', 'persona', 'domicilio', 'responsable',
            'edad', 'tiene_cud', 'tipo_cobertura', 'nombre_cobertura'
        ]
        read_only_fields = AuditSerializerMixin.AUDIT_READ_ONLY_FIELDS

    @transaction.atomic
    def create(self, validated_data):
        persona_data = validated_data.pop('persona')
        domicilio_data = validated_data.pop('domicilio')

        actor = self._actor()
        if actor is not None and getattr(actor, 'is_authenticated', False):
            validated_data['created_by'] = actor
            validated_data['updated_by'] = actor

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

        actor = self._actor()
        if actor is not None and getattr(actor, 'is_authenticated', False):
            validated_data['updated_by'] = actor

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

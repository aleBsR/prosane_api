from rest_framework import serializers

from health.models import Apto


class AptoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Apto
        fields = [
            'id', 'paciente', 'profesional', 'estado',
            'peso_kg', 'altura_cm', 'observaciones',
            'nna_nombre_completo', 'nna_edad',
            'profesional_nombre', 'matricula_firmante',
            'fecha_emision', 'validez_hasta', 'firma_hash', 'timestamp_firma',
        ]
        read_only_fields = [
            'estado', 'profesional', 'nna_nombre_completo', 'nna_edad',
            'profesional_nombre', 'matricula_firmante',
            'fecha_emision', 'validez_hasta', 'firma_hash', 'timestamp_firma',
        ]

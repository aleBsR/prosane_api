from rest_framework import serializers

from apps.auditoria.models import AuditoriaCambio


class AuditoriaCambioSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True, default=None)

    class Meta:
        model = AuditoriaCambio
        fields = [
            'id', 'created_at', 'actor', 'actor_email', 'entidad',
            'entidad_id', 'accion', 'detalle', 'ip',
        ]
        read_only_fields = fields

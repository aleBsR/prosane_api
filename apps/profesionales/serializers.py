from rest_framework import serializers
from apps.profesionales.models import Profesional


class ProfesionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profesional
        fields = "__all__"

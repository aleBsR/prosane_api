from rest_framework import serializers
from apps.antecedentes.models import AntecedenteFamiliar, AntecedentePersonal


class AntecedentesfamiliaresSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedenteFamiliar
        fields = "__all__"


class AntecedentespersonalesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedentePersonal
        fields = "__all__"

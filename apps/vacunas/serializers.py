from rest_framework import serializers
from apps.vacunas.models import Vacuna, CarnetVacuna


class VacunasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vacuna
        fields = "__all__"


class CarnetVacunasSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarnetVacuna
        fields = "__all__"

from rest_framework import serializers
from apps.escuelas.models import Escuela, ObservacionEscuela


class EscuelasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escuela
        fields = "__all__"


class ObservacionEscuelaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObservacionEscuela
        fields = "__all__"

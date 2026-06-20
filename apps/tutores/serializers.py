from rest_framework import serializers
from apps.tutores.models import Tutor


class TutoresSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tutor
        fields = "__all__"

from rest_framework import serializers

from apps.antecedentes.models import AntecedenteFamiliar, AntecedenteFamiliarTutor, AntecedentePersonal
from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
from apps.tutores.models import Tutor


class PersonaInputSerializer(serializers.ModelSerializer):
    """Serializer de entrada para datos de Persona."""

    class Meta:
        model = Persona
        fields = ["nombre", "apellido", "dni", "tipo_dni", "sexo", "fecha_nacimiento"]


class DomicilioInputSerializer(serializers.ModelSerializer):
    """Serializer de entrada para datos de Domicilio."""

    class Meta:
        model = Domicilio
        fields = [
            "calle", "nro_calle", "piso", "dpto", "manzana",
            "casa", "nro_casa", "pieza", "provincia", "departamento", "localidad",
        ]


class TutorRegistrationSerializer(serializers.Serializer):
    """Serializer de entrada para registro de tutor."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    persona = PersonaInputSerializer(required=True)
    parentesco = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        from apps.usuarios.models import Usuario

        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def validate(self, attrs):
        dni = attrs.get("persona", {}).get("dni")
        if dni and Persona.objects.filter(dni=dni).exists():
            raise serializers.ValidationError({"persona.dni": "Ya existe una persona con este DNI."})
        return attrs


_AUDIT_FIELDS = [
    "id", "paciente", "created_at", "created_year", "created_year_month",
    "updated_at", "updated_year", "updated_year_month",
    "created_by", "updated_by", "deleted_at",
]


class AntecedentePersonalInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedentePersonal
        exclude = _AUDIT_FIELDS


class AntecedenteFamiliarInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedenteFamiliar
        exclude = _AUDIT_FIELDS


class HijoCreateSerializer(serializers.Serializer):
    """Serializer de entrada para crear un hijo (Paciente)."""

    persona = PersonaInputSerializer(required=True)
    domicilio = DomicilioInputSerializer(required=True)
    edad = serializers.IntegerField(required=True, min_value=0)
    tiene_cud = serializers.CharField(required=False, allow_blank=True)
    tipo_cobertura = serializers.CharField(required=False, allow_blank=True)
    nombre_cobertura = serializers.CharField(required=False, allow_blank=True)
    telefono_fijo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    celular = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    parentesco = serializers.CharField(required=False, allow_blank=True)
    antecedentes_personales = AntecedentePersonalInputSerializer(required=False)

    def validate(self, attrs):
        dni = attrs.get("persona", {}).get("dni")
        if dni and Persona.objects.filter(dni=dni).exists():
            raise serializers.ValidationError({"persona.dni": "Ya existe una persona con este DNI."})
        return attrs


class PersonaOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = ["id", "nombre", "apellido", "dni", "tipo_dni", "sexo", "fecha_nacimiento"]


class DomicilioOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domicilio
        fields = [
            "id", "calle", "nro_calle", "piso", "dpto", "manzana",
            "casa", "nro_casa", "pieza", "provincia", "departamento", "localidad",
        ]


class HijoOutputSerializer(serializers.ModelSerializer):
    """Serializer de salida para un Paciente (hijo)."""

    persona = PersonaOutputSerializer(read_only=True)
    domicilio = DomicilioOutputSerializer(read_only=True)
    adulto = serializers.SerializerMethodField()

    class Meta:
        model = Paciente
        fields = [
            "id", "persona", "domicilio", "tutor", "edad",
            "tiene_cud", "tipo_cobertura", "nombre_cobertura",
            "consentimiento_aceptado", "fecha_consentimiento",
            "telefono_fijo", "celular",
            "adulto",
        ]

    def get_adulto(self, obj):
        return obj.adulto


class TutorConsentimientoOutputSerializer(serializers.ModelSerializer):
    """Serializer de salida del consentimiento del tutor."""

    class Meta:
        model = Tutor
        fields = ["id", "consentimiento_aceptado", "fecha_consentimiento"]


class AntecedenteFamiliarTutorSerializer(serializers.ModelSerializer):
    """Serializer de entrada/salida de antecedentes familiares del tutor."""

    class Meta:
        model = AntecedenteFamiliarTutor
        fields = [
            "id", "tutor",
            "problema_salud_importante", "problema_salud_cual",
            "muerte_subita_familiar",
        ]
        read_only_fields = ["id", "tutor"]


class TutorOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tutor
        fields = ["id", "parentesco", "persona", "usuario"]

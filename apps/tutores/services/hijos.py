"""Servicio de gestión de hijos de un tutor.

Un 'hijo' es un Paciente vinculado a un Tutor.
"""
from django.db import transaction
from django.utils import timezone

from apps.antecedentes.models import AntecedenteFamiliar, AntecedentePersonal
from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
from apps.tutores.models import Tutor


class HijosError(Exception):
    """Error controlado durante la gestión de hijos."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def _validar_dni_unico(dni):
    if Persona.objects.filter(dni=dni).exists():
        raise HijosError("Ya existe una persona con este DNI.", field="dni")


def crear_hijo(tutor_id, data):
    """Crea un hijo (Paciente) con antecedentes y consentimiento, atómicamente."""
    try:
        tutor = Tutor.objects.get(id=tutor_id)
    except Tutor.DoesNotExist:
        raise HijosError("Tutor no encontrado.", field="tutor")

    persona_data = data.get("persona", {})
    _validar_dni_unico(persona_data.get("dni"))

    consent = data.get("consentimiento") or {}
    ant_personales = data.get("antecedentes_personales") or {}
    ant_familiares = data.get("antecedentes_familiares") or {}
    parentesco = data.get("parentesco")

    with transaction.atomic():
        domicilio = Domicilio.objects.create(**data.get("domicilio", {}))
        persona = Persona.objects.create(**persona_data)
        paciente = Paciente.objects.create(
            persona=persona,
            domicilio=domicilio,
            tutor=tutor,
            edad=data.get("edad"),
            tiene_cud=data.get("tiene_cud"),
            tipo_cobertura=data.get("tipo_cobertura"),
            nombre_cobertura=data.get("nombre_cobertura"),
            consentimiento_aceptado=bool(consent),
            fecha_consentimiento=timezone.now() if consent else None,
            adulto_nombre=consent.get("adulto_nombre"),
            adulto_apellido=consent.get("adulto_apellido"),
            adulto_tipo_documento=consent.get("adulto_tipo_documento"),
            adulto_dni=consent.get("adulto_dni"),
        )
        AntecedentePersonal.objects.create(paciente=paciente, **ant_personales)
        AntecedenteFamiliar.objects.create(paciente=paciente, **ant_familiares)

        if parentesco:
            tutor.parentesco = parentesco
            tutor.save(update_fields=["parentesco", "updated_at"])

    return paciente


def listar_hijos(tutor_id):
    """Retorna el queryset de Pacientes vinculados al tutor."""
    return Paciente.objects.filter(tutor_id=tutor_id).select_related("persona", "domicilio")

"""Servicio de gestión de hijos de un tutor.

Un 'hijo' es un Paciente vinculado a un Tutor.
"""
from django.db import transaction

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
    """Crea un hijo (Paciente) vinculado a un tutor.

    Args:
        tutor_id: UUID del tutor.
        data: Dict con datos de persona, domicilio y paciente.

    Returns:
        Paciente creado.

    Raises:
        HijosError: Si el tutor no existe o hay problemas de validación.
    """
    try:
        tutor = Tutor.objects.get(id=tutor_id)
    except Tutor.DoesNotExist:
        raise HijosError("Tutor no encontrado.", field="tutor")

    persona_data = data.get("persona", {})
    _validar_dni_unico(persona_data.get("dni"))

    with transaction.atomic():
        domicilio_data = data.get("domicilio", {})
        domicilio = Domicilio.objects.create(**domicilio_data)
        persona = Persona.objects.create(**persona_data)
        paciente = Paciente.objects.create(
            persona=persona,
            domicilio=domicilio,
            tutor=tutor,
            edad=data.get("edad"),
            tiene_cud=data.get("tiene_cud"),
            tipo_cobertura=data.get("tipo_cobertura"),
            nombre_cobertura=data.get("nombre_cobertura"),
        )

    return paciente


def listar_hijos(tutor_id):
    """Retorna el queryset de Pacientes vinculados al tutor."""
    return Paciente.objects.filter(tutor_id=tutor_id).select_related("persona", "domicilio")

"""Servicio de gestión de hijos de un tutor.

Un 'hijo' es un Paciente vinculado a un Tutor.
"""
from django.db import transaction

from apps.antecedentes.models import AntecedentePersonal
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


def crear_hijo(tutor_id, data, requiere_consentimiento=True):
    """Crea un hijo (Paciente) con antecedentes personales, atómicamente.

    Args:
        tutor_id: UUID del tutor.
        data: dict con datos del hijo.
        requiere_consentimiento: si es True, rechaza el alta si el tutor
            no aceptó el consentimiento general.
    """
    try:
        tutor = Tutor.objects.get(id=tutor_id)
    except Tutor.DoesNotExist:
        raise HijosError("Tutor no encontrado.", field="tutor")

    if requiere_consentimiento and not tutor.consentimiento_aceptado:
        raise HijosError(
            "El tutor debe aceptar el consentimiento general antes de registrar hijos.",
            field="consentimiento",
        )

    persona_data = dict(data.get("persona", {}))
    _validar_dni_unico(persona_data.get("dni"))

    telefono_fijo = persona_data.pop("telefono_fijo", None) or None
    celular = persona_data.pop("celular", None) or None

    ant_personales = data.get("antecedentes_personales") or {}
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
            telefono_fijo=telefono_fijo,
            celular=celular,
        )
        AntecedentePersonal.objects.create(paciente=paciente, **ant_personales)

        if parentesco:
            tutor.parentesco = parentesco
            tutor.save(update_fields=["parentesco", "updated_at", "updated_year", "updated_year_month"])

    return paciente


def listar_hijos(tutor_id):
    """Retorna el queryset de Pacientes vinculados al tutor."""
    return Paciente.objects.filter(tutor_id=tutor_id).select_related(
        "persona", "domicilio", "tutor", "tutor__persona"
    )

"""Servicios para gestionar antecedentes de salud del niño."""
from django.shortcuts import get_object_or_404

from apps.antecedentes.models import AntecedentePersonal
from apps.pacientes.models import Paciente
from apps.tutores.models import Tutor


class AntecedenteNinoError(Exception):
    """Error controlado en operaciones de antecedentes del niño."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def verificar_pertenencia_tutor(tutor_id, user):
    """Devuelve el tutor solo si pertenece al usuario autenticado."""
    tutor = get_object_or_404(Tutor, pk=tutor_id)
    if tutor.usuario != user and not user.is_superuser:
        raise AntecedenteNinoError("No tenés permiso para gestionar este tutor.", field="detail")
    return tutor


def upsert_antecedentes_nino(tutor_id, paciente_id, user, datos):
    """
    Upsert antecedentes del niño. El alta ya crea AntecedentePersonal con defaults.
    Esta función actualiza los campos recibidos.

    Args:
        tutor_id: UUID del Tutor
        paciente_id: UUID del Paciente
        user: Usuario autenticado
        datos: dict con campos de AntecedentePersonal

    Returns:
        AntecedentePersonal actualizado

    Raises:
        AntecedenteNinoError si no hay permiso o no existen los registros
    """
    # Verificar que el tutor pertenece al usuario
    tutor = verificar_pertenencia_tutor(tutor_id, user)

    # Verificar que el paciente existe y pertenece al tutor
    try:
        paciente = Paciente.objects.get(id=paciente_id)
    except Paciente.DoesNotExist:
        raise AntecedenteNinoError("Paciente no encontrado.", field="paciente_id")

    if paciente.tutor_id != tutor.id:
        raise AntecedenteNinoError(
            f"Paciente {paciente_id} no pertenece al tutor {tutor_id}.",
            field="paciente_id"
        )

    # Obtener o crear AntecedentePersonal
    antecedente, _ = AntecedentePersonal.objects.get_or_create(paciente=paciente)

    # Actualizar campos
    for campo, valor in datos.items():
        if hasattr(antecedente, campo):
            setattr(antecedente, campo, valor)

    antecedente.save()
    return antecedente

"""Servicios de perfil del tutor: consentimiento y antecedentes familiares."""
from django.utils import timezone
from django.shortcuts import get_object_or_404

from apps.antecedentes.models import AntecedenteFamiliarTutor
from apps.tutores.models import Tutor


class TutorProfileError(Exception):
    """Error controlado en operaciones de perfil del tutor."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def verificar_pertenencia_tutor(tutor_id, user):
    """Devuelve el tutor solo si pertenece al usuario autenticado."""
    tutor = get_object_or_404(Tutor, pk=tutor_id)
    if tutor.usuario != user and not user.is_superuser:
        raise TutorProfileError("No tenés permiso para gestionar este tutor.", field="detail")
    return tutor


def aceptar_consentimiento(tutor_id, user):
    """Acepta el consentimiento general del tutor (idempotente)."""
    tutor = verificar_pertenencia_tutor(tutor_id, user)

    if not tutor.consentimiento_aceptado:
        tutor.consentimiento_aceptado = True
        tutor.fecha_consentimiento = timezone.now()
        tutor.save(update_fields=["consentimiento_aceptado", "fecha_consentimiento", "updated_at"])

    return tutor


def obtener_o_crear_antecedente_familiar(tutor_id, user):
    """Obtiene el antecedente familiar del tutor, validando pertenencia."""
    tutor = verificar_pertenencia_tutor(tutor_id, user)
    antecedente, _ = AntecedenteFamiliarTutor.objects.get_or_create(tutor=tutor)
    return antecedente


def actualizar_antecedente_familiar(tutor_id, user, data):
    """Crea o actualiza los antecedentes familiares del tutor."""
    tutor = verificar_pertenencia_tutor(tutor_id, user)

    antecedente, _ = AntecedenteFamiliarTutor.objects.get_or_create(tutor=tutor)
    for field in ["problema_salud_importante", "problema_salud_cual", "muerte_subita_familiar"]:
        if field in data:
            setattr(antecedente, field, data[field])
    antecedente.save()

    return antecedente

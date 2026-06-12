"""Lógica de negocio del Apto físico (Slice A)."""
import hashlib
import json
from datetime import timedelta

from django.db import transaction


class AptoInmutableError(Exception):
    """Se intentó editar/firmar un apto ya firmado."""


def crear_apto(*, paciente, profesional):
    from health.models import Apto
    return Apto.objects.create(paciente=paciente, profesional=profesional)


def editar_apto(apto, *, peso_kg=None, altura_cm=None, observaciones=None):
    if apto.esta_firmado:
        raise AptoInmutableError("El apto está firmado: es inmutable.")
    if peso_kg is not None:
        apto.peso_kg = peso_kg
    if altura_cm is not None:
        apto.altura_cm = altura_cm
    if observaciones is not None:
        apto.observaciones = observaciones
    apto.save()
    return apto


def _nombre_completo(persona):
    partes = [getattr(persona, "nombre", None), getattr(persona, "apellido", None)]
    return " ".join(p for p in partes if p)


def _firma_hash(apto, timestamp):
    payload = {
        "nna_dni": apto.nna_dni,
        "nna_nombre_completo": apto.nna_nombre_completo,
        "nna_edad": apto.nna_edad,
        "peso_kg": str(apto.peso_kg),
        "altura_cm": str(apto.altura_cm),
        "profesional_nombre": apto.profesional_nombre,
        "matricula_firmante": apto.matricula_firmante,
        "timestamp_firma": timestamp.isoformat(),
    }
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


@transaction.atomic
def firmar_apto(apto, *, now):
    if apto.esta_firmado:
        raise AptoInmutableError("El apto ya está firmado.")
    persona = apto.paciente.persona
    apto.nna_dni = persona.dni
    apto.nna_nombre_completo = _nombre_completo(persona)
    apto.nna_edad = apto.paciente.edad
    prof_persona = getattr(apto.profesional, "persona", None)
    apto.profesional_nombre = _nombre_completo(prof_persona) if prof_persona else apto.profesional.email
    from professionals.models import Profesionales
    prof = Profesionales.objects.filter(id_usuario=apto.profesional).first()
    apto.matricula_firmante = prof.matricula if prof else None
    apto.fecha_emision = now.date()
    apto.validez_hasta = now.date() + timedelta(days=365)
    apto.timestamp_firma = now
    apto.firma_hash = _firma_hash(apto, now)
    apto.estado = apto.FIRMADO
    apto.save()
    return apto

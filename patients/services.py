"""Lógica de negocio de patients (Slice B: consentimiento)."""
import hashlib
import json


def _firma_hash(*, firma_tipo, nombre, apellido, tipo_doc, dni, timestamp):
    payload = {
        "firma_tipo": firma_tipo,
        "nombre": nombre,
        "apellido": apellido,
        "tipo_documento": tipo_doc,
        "dni": dni,
        "fecha_firma": timestamp.isoformat(),
    }
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def crear_consentimiento(*, paciente, firma_tipo, adulto_nombre, adulto_apellido,
                         adulto_tipo_documento, adulto_dni, now):
    """Crea un consentimiento YA firmado (un paso). Inmutable luego."""
    from patients.models import Consentimiento
    return Consentimiento.objects.create(
        paciente=paciente,
        firma_tipo=firma_tipo,
        adulto_nombre=adulto_nombre,
        adulto_apellido=adulto_apellido,
        adulto_tipo_documento=adulto_tipo_documento,
        adulto_dni=adulto_dni,
        fecha_firma=now,
        firma_hash=_firma_hash(
            firma_tipo=firma_tipo, nombre=adulto_nombre, apellido=adulto_apellido,
            tipo_doc=adulto_tipo_documento, dni=adulto_dni, timestamp=now,
        ),
    )

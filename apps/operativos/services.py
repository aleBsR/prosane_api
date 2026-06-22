import csv
import io
from datetime import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Operativo, OperativoAlumno, OperativoProfesional


# ──────────────────────────────────────────────
#  Transiciones válidas de la máquina de estados
# ──────────────────────────────────────────────
ESTADO_TRANSICIONES = {
    Operativo.BORRADOR: [Operativo.CONFIRMADO, Operativo.CANCELADO],
    Operativo.CONFIRMADO: [Operativo.EN_CURSO, Operativo.CANCELADO],
    Operativo.EN_CURSO: [Operativo.FINALIZADO, Operativo.CANCELADO],
    Operativo.FINALIZADO: [],
    Operativo.CANCELADO: [],
}


def transicionar_estado(operativo_id, nuevo_estado):
    operativo = get_object_or_404(Operativo, pk=operativo_id)

    if operativo.estado == nuevo_estado:
        raise ValueError(f'El operativo ya está en estado {nuevo_estado}')

    permitidos = ESTADO_TRANSICIONES.get(operativo.estado, [])
    if nuevo_estado not in permitidos:
        raise ValueError(
            f'No se puede pasar de {operativo.estado} a {nuevo_estado}. '
            f'Transiciones permitidas: {permitidos}'
        )

    operativo.estado = nuevo_estado
    operativo.save(update_fields=['estado', 'updated_at'])
    return operativo


# ──────────────────────────────────────────────
#  Conflictos de fecha
# ──────────────────────────────────────────────
def tiene_conflicto_fecha(profesional_id, fecha, exclude_operativo_id=None):
    qs = OperativoProfesional.objects.filter(
        profesional_id=profesional_id,
        operativo__fecha=fecha,
        operativo__estado__in=[
            Operativo.CONFIRMADO, Operativo.EN_CURSO,
        ],
    )
    if exclude_operativo_id:
        qs = qs.exclude(operativo_id=exclude_operativo_id)
    return qs.exists()


# ──────────────────────────────────────────────
#  Creación
# ──────────────────────────────────────────────
def crear_operativo(escuela_id, fecha, **kwargs):
    return Operativo.objects.create(
        escuela_id=escuela_id,
        fecha=fecha,
        **kwargs,
    )


# ──────────────────────────────────────────────
#  Asignar profesional
# ──────────────────────────────────────────────
def asignar_profesional(operativo_id, profesional_id, rol):
    operativo = get_object_or_404(Operativo, pk=operativo_id)

    if operativo.estado != Operativo.BORRADOR:
        raise ValueError('Solo se pueden asignar profesionales en estado borrador')

    if tiene_conflicto_fecha(profesional_id, operativo.fecha, exclude_operativo_id=operativo_id):
        raise ValueError(
            'El profesional ya tiene un operativo activo en esa fecha'
        )

    _, created = OperativoProfesional.objects.get_or_create(
        operativo=operativo,
        profesional_id=profesional_id,
        defaults={'rol_en_operativo': rol},
    )
    if not created:
        raise ValueError('El profesional ya está asignado a este operativo')

    return OperativoProfesional.objects.get(
        operativo=operativo, profesional_id=profesional_id,
    )


# ──────────────────────────────────────────────
#  Remover profesional
# ──────────────────────────────────────────────
def remover_profesional(operativo_id, profesional_rel_id):
    operativo = get_object_or_404(Operativo, pk=operativo_id)

    if operativo.estado != Operativo.BORRADOR:
        raise ValueError('Solo se pueden remover profesionales en estado borrador')

    rel = get_object_or_404(
        OperativoProfesional, operativo=operativo, pk=profesional_rel_id,
    )
    rel.delete()
    return operativo


# ──────────────────────────────────────────────
#  Confirmar
# ──────────────────────────────────────────────
def confirmar_operativo(operativo_id):
    operativo = get_object_or_404(Operativo, pk=operativo_id)

    if operativo.estado != Operativo.BORRADOR:
        raise ValueError(f'No se puede confirmar un operativo en estado {operativo.estado}')

    if not operativo.profesionales_asignados.exists():
        raise ValueError('Debe haber al menos un profesional asignado')

    if not operativo.alumnos.exists():
        raise ValueError('Debe haber al menos un alumno cargado')

    return transicionar_estado(operativo_id, Operativo.CONFIRMADO)


# ──────────────────────────────────────────────
#  Finalizar
# ──────────────────────────────────────────────
def finalizar_operativo(operativo_id):
    operativo = get_object_or_404(Operativo, pk=operativo_id)

    if operativo.estado != Operativo.EN_CURSO:
        raise ValueError(
            f'Solo se puede finalizar un operativo en curso '
            f'(estado actual: {operativo.estado})'
        )

    no_evaluados = operativo.alumnos.exclude(
        estado__in=[OperativoAlumno.AUSENTE, OperativoAlumno.EVALUADO],
    )
    if no_evaluados.exists():
        raise ValueError(
            f'Todos los alumnos deben estar evaluados o ausentes. '
            f'{no_evaluados.count()} alumnos pendientes.'
        )

    return transicionar_estado(operativo_id, Operativo.FINALIZADO)


# ──────────────────────────────────────────────
#  Cancelar
# ──────────────────────────────────────────────
def cancelar_operativo(operativo_id):
    return transicionar_estado(operativo_id, Operativo.CANCELADO)


# ──────────────────────────────────────────────
#  Importar CSV
# ──────────────────────────────────────────────
def importar_csv(operativo_id, archivo_csv):
    operativo = get_object_or_404(Operativo, pk=operativo_id)

    if operativo.estado not in (Operativo.BORRADOR, Operativo.CONFIRMADO):
        raise ValueError('Solo se puede importar CSV en estado borrador o confirmado')

    decoded = archivo_csv.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))

    creados = 0
    duplicados = 0
    errores = []
    fila = 0

    for row in reader:
        fila += 1
        try:
            dni = row.get('dni', '').strip()
            if not dni:
                errores.append(f'Fila {fila}: DNI vacío')
                continue

            _, created = OperativoAlumno.objects.get_or_create(
                operativo=operativo,
                dni=dni,
                defaults={
                    'apellido': row.get('apellido', '').strip(),
                    'nombre': row.get('nombre', '').strip(),
                    'tipo_dni': row.get('tipo_dni', 'DNI').strip(),
                    'fecha_nacimiento': _parse_fecha(row.get('fecha_nacimiento', '').strip()),
                    'sexo': row.get('sexo', '').strip(),
                },
            )
            if created:
                creados += 1
            else:
                duplicados += 1
        except Exception as e:
            errores.append(f'Fila {fila}: {e}')

    return {
        'creados': creados,
        'duplicados': duplicados,
        'errores': errores,
        'total_filas': fila,
    }


def _parse_fecha(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        return None

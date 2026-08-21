import csv
import io
from datetime import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.escuelas.models import Curso
from apps.pacientes.models import Paciente
from apps.personas.models import Persona

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
#  Iniciar
# ──────────────────────────────────────────────
def iniciar_operativo(operativo_id):
    """
    Transiciona un operativo de CONFIRMADO → EN_CURSO.
    """
    return transicionar_estado(operativo_id, Operativo.EN_CURSO)


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

    if not operativo.puede_finalizar:
        raise ValueError('No se puede finalizar: faltan evaluaciones de alumnos')

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
    creados_por_curso = {}

    for row in reader:
        fila += 1
        try:
            dni = row.get('dni', '').strip()
            if not dni:
                errores.append(f'Fila {fila}: DNI vacío')
                continue

            curso = _buscar_o_crear_curso(
                operativo.escuela_id,
                row.get('grado', '').strip(),
                row.get('division', '').strip(),
                operativo.fecha.year,
            )

            alumno, created = OperativoAlumno.objects.get_or_create(
                operativo=operativo,
                dni=dni,
                defaults={
                    'apellido': row.get('apellido', '').strip(),
                    'nombre': row.get('nombre', '').strip(),
                    'tipo_dni': row.get('tipo_dni', 'DNI').strip(),
                    'fecha_nacimiento': _parse_fecha(row.get('fecha_nacimiento', '').strip()),
                    'sexo': row.get('sexo', '').strip(),
                    'curso': curso,
                },
            )
            if not alumno.paciente_id:
                paciente = _buscar_paciente_por_dni(dni)
                if paciente is not None:
                    alumno.paciente = paciente
                    alumno.save(update_fields=['paciente', 'updated_at'])
            if created:
                creados += 1
                if curso is not None:
                    etiqueta = _curso_etiqueta(curso)
                    creados_por_curso[etiqueta] = creados_por_curso.get(etiqueta, 0) + 1
            else:
                duplicados += 1
        except Exception as e:
            errores.append(f'Fila {fila}: {e}')

    return {
        'creados': creados,
        'duplicados': duplicados,
        'errores': errores,
        'total_filas': fila,
        'creados_por_curso': creados_por_curso,
    }


def _parse_fecha(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        return None


def _buscar_paciente_por_dni(dni):
    persona_id = Persona.objects.filter(dni=dni).values_list('id', flat=True).first()
    if not persona_id:
        return None
    return Paciente.objects.filter(persona_id=persona_id).first()


def _buscar_o_crear_curso(escuela_id, grado, division, ciclo_lectivo):
    """Devuelve el Curso del grado/división en la escuela del operativo.

    Si la fila no trae grado ni división devuelve None (nómina sin curso).
    Si el curso no existe aún, se crea automáticamente.
    """
    if not grado and not division:
        return None
    curso, _ = Curso.objects.get_or_create(
        escuela_id=escuela_id,
        sala_grado_anio=grado,
        division=division,
        defaults={'nivel': '', 'ciclo_lectivo': ciclo_lectivo},
    )
    return curso


def _curso_etiqueta(curso):
    partes = [p for p in [curso.sala_grado_anio, curso.division] if p]
    return ' '.join(partes) or 'Sin curso'

import csv
import io
from datetime import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.antecedentes.models import AntecedentePersonal
from apps.escuelas.models import Curso
from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona

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

# Estados donde el operativo es inmutable (bloqueo total, incluso superadmin)
ESTADOS_NO_EDITABLES = {Operativo.FINALIZADO, Operativo.CANCELADO}


def exigir_operativo_mutable(operativo):
    """Lanza ValueError si el operativo está en estado no editable."""
    if operativo.estado in ESTADOS_NO_EDITABLES:
        raise ValueError('El operativo ya está finalizado o cancelado y no se puede modificar')


def exigir_operativo_en_curso(operativo):
    """Lanza ValueError si el operativo no está en curso (para cargar evaluaciones)."""
    if operativo.estado != Operativo.EN_CURSO:
        if operativo.estado in ESTADOS_NO_EDITABLES:
            raise ValueError('El operativo ya está finalizado o cancelado y no se puede modificar')
        raise ValueError('Solo se puede cargar datos cuando el operativo está en curso')


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
ROLES_PROFESIONALES = ('medico', 'odontologo')


def _rol_profesional(profesional_id, rol=None):
    """Resuelve y valida el rol en el operativo desde los roles del usuario.

    Si no se indica rol y el profesional tiene uno solo, se deriva
    automáticamente. Si tiene ambos, hay que indicarlo. El rol indicado
    debe coincidir con uno real del profesional.
    """
    from apps.usuarios.models import Usuario
    try:
        usuario = Usuario.objects.prefetch_related('roles').get(pk=profesional_id)
    except Usuario.DoesNotExist:
        raise ValueError('Profesional no encontrado')
    roles = [r.rol for r in usuario.roles.all() if r.rol in ROLES_PROFESIONALES]
    if rol is None:
        if len(roles) == 1:
            return roles[0]
        if not roles:
            raise ValueError('El usuario no tiene rol de médico ni odontólogo')
        raise ValueError('El profesional tiene ambos roles: indicá médico u odontólogo')
    if rol not in roles:
        raise ValueError(f'El profesional no tiene el rol {rol}')
    return rol


def asignar_profesional(operativo_id, profesional_id, rol=None):
    operativo = get_object_or_404(Operativo, pk=operativo_id)

    if operativo.estado != Operativo.BORRADOR:
        raise ValueError('Solo se pueden asignar profesionales en estado borrador')

    rol = _rol_profesional(profesional_id, rol)

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
                paciente = _asegurar_paciente_para_operativo(
                    operativo=operativo,
                    dni=dni,
                    apellido=row.get('apellido', '').strip(),
                    nombre=row.get('nombre', '').strip(),
                    tipo_dni=row.get('tipo_dni', 'DNI').strip(),
                    fecha_nacimiento=_parse_fecha(row.get('fecha_nacimiento', '').strip()),
                    sexo=row.get('sexo', '').strip(),
                    curso=curso,
                )
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


def _buscar_paciente_por_dni(dni, escuela_id=None):
    """Busca Paciente por DNI, opcionalmente filtrado por escuela."""
    persona_id = Persona.objects.filter(dni=dni).values_list('id', flat=True).first()
    if not persona_id:
        return None
    qs = Paciente.objects.filter(persona_id=persona_id)
    if escuela_id is not None:
        qs = qs.filter(escuela_id=escuela_id)
    return qs.first()


def _asegurar_paciente_para_operativo(operativo, dni, apellido, nombre, tipo_dni, fecha_nacimiento, sexo, curso):
    """Asegura que exista un Paciente para la escuela del operativo.

    Usado por importar_csv para que los alumnos del operativo también aparezcan
    en 'Alumnos de mi escuela' (Paciente con escuela_id). Reutiliza Persona por DNI
    pero crea un Paciente por escuela (un mismo DNI puede estar en varias escuelas).
    Si ya existe un Paciente para ese dni Y esa escuela se reutiliza; si no, se crea
    uno nuevo para esa escuela.
    """
    # 1) Reusar Paciente existente para esa misma escuela
    paciente = _buscar_paciente_por_dni(dni, escuela_id=operativo.escuela_id)
    if paciente is not None:
        return paciente
    # 2) Si existe Paciente con mismo DNI en otra escuela, no reutilizar: crear uno nuevo para esta escuela
    #    (Persona se reutiliza, Paciente es por escuela)

    # Crear Persona si no existe
    try:
        persona = Persona.objects.get(dni=dni)
    except Persona.DoesNotExist:
        # sexo y fecha_nacimiento son obligatorios en Persona; usar defaults si faltan
        persona = Persona.objects.create(
            nombre=nombre or '',
            apellido=apellido or '',
            dni=dni,
            tipo_dni=tipo_dni or 'DNI',
            sexo=sexo or 'otro',
            fecha_nacimiento=fecha_nacimiento or '2015-01-01',
        )
    # Crear domicilio vacío o con localidad de la escuela si se conoce
    try:
        escuela = operativo.escuela
        localidad = ''
        if escuela and escuela.domicilio:
            localidad = escuela.domicilio.localidad or ''
    except Exception:
        localidad = ''
    domicilio = Domicilio.objects.create(localidad=localidad)

    # Calcular edad si hay fecha_nacimiento
    edad = 0
    if fecha_nacimiento:
        try:
            hoy = datetime.now().date()
            edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            if edad < 0:
                edad = 0
        except Exception:
            edad = 0

    paciente = Paciente.objects.create(
        escuela_id=operativo.escuela_id,
        persona=persona,
        domicilio=domicilio,
        tutor=None,
        edad=edad,
        consentimiento_aceptado=False,
    )
    AntecedentePersonal.objects.get_or_create(paciente=paciente)
    return paciente


def _normalizar_grado(grado: str) -> str:
    """Normaliza el grado para evitar duplicados por distinto símbolo de grado.

    El CSV usa '1°' (U+00B0) y el seed usa '1º' (U+00BA); se unifican a '°'.
    Un número solo ('1') equivale a '1°' (autocompletado de la app).
    """
    import re

    if not grado:
        return grado
    v = grado.strip().replace('\u00ba', '\u00b0').replace('\u00B0', '\u00b0')
    if re.fullmatch(r'\d{1,2}', v):
        return f'{v}\u00b0'
    return v


def _buscar_o_crear_curso(escuela_id, grado, division, ciclo_lectivo):
    """Devuelve el Curso del grado/división en la escuela del operativo.

    Si la fila no trae grado ni división devuelve None (nómina sin curso).
    Si el curso no existe aún, se crea automáticamente.
    Normaliza el grado para no duplicar por '°' vs 'º'.
    """
    grado_norm = _normalizar_grado(grado)
    division_norm = division.strip().upper() if division else division
    if not grado_norm and not division_norm:
        return None
    # Buscar por grado normalizado (en DB puede haber con 'º' o '°', probamos ambos)
    # Primero intenta con el normalizado; si no encuentra, busca con la variante.
    curso = Curso.objects.filter(
        escuela_id=escuela_id,
        sala_grado_anio__iexact=grado_norm,
        division__iexact=division_norm,
    ).first()
    if curso:
        return curso
    # Buscar variante con 'º' si el normalizado es '°'
    variante = grado_norm.replace('\u00b0', '\u00ba') if '\u00b0' in grado_norm else grado_norm.replace('\u00ba', '\u00b0')
    if variante != grado_norm:
        curso = Curso.objects.filter(
            escuela_id=escuela_id,
            sala_grado_anio__iexact=variante,
            division__iexact=division_norm,
        ).first()
        if curso:
            # Actualizar a la forma normalizada para futuro
            curso.sala_grado_anio = grado_norm
            curso.save(update_fields=['sala_grado_anio', 'updated_at'])
            return curso
    curso, _ = Curso.objects.get_or_create(
        escuela_id=escuela_id,
        sala_grado_anio=grado_norm,
        division=division_norm,
        defaults={'nivel': '', 'ciclo_lectivo': ciclo_lectivo},
    )
    return curso


def _curso_etiqueta(curso):
    partes = [p for p in [curso.sala_grado_anio, curso.division] if p]
    return ' '.join(partes) or 'Sin curso'

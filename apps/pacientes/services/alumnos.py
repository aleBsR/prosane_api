from django.db import transaction

from apps.antecedentes.models import AntecedentePersonal
from apps.escuelas.models import Curso
from apps.operativos.models import Operativo, OperativoAlumno
from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona


class AlumnoEscuelaError(Exception):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def crear_alumno_escuela(escuela_id, data):
    operativo = None
    curso = None
    operativo_id = data.get('operativo_id')
    curso_id = data.get('curso_id')
    if operativo_id:
        operativo = Operativo.objects.filter(
            id=operativo_id, escuela_id=escuela_id,
        ).first()
        if operativo is None:
            raise AlumnoEscuelaError('El operativo no pertenece a tu escuela.', field='operativo_id')
    if curso_id:
        curso = Curso.objects.filter(id=curso_id, escuela_id=escuela_id).first()
        if curso is None:
            raise AlumnoEscuelaError('El curso no pertenece a tu escuela.', field='curso_id')
    if operativo_id and not curso_id:
        raise AlumnoEscuelaError('Elegí un curso para asociar el alumno al operativo.', field='curso_id')
    if operativo is not None and operativo.estado not in (Operativo.BORRADOR, Operativo.CONFIRMADO):
        raise AlumnoEscuelaError('Solo se puede asociar alumnos en operativos en borrador o confirmado.', field='operativo_id')
    persona_data = dict(data['persona'])
    dni = persona_data.get('dni')
    if Persona.objects.filter(dni=dni).exists():
        raise AlumnoEscuelaError('Ya existe una persona con este DNI.', field='persona.dni')

    antecedentes_data = data.get('antecedentes') or {}
    with transaction.atomic():
        domicilio = Domicilio.objects.create(**data.get('domicilio', {}))
        persona = Persona.objects.create(**persona_data)
        paciente = Paciente.objects.create(
            escuela_id=escuela_id,
            persona=persona,
            domicilio=domicilio,
            tutor=None,
            edad=data['edad'],
            tiene_cud=data.get('tiene_cud') or None,
            tipo_cobertura=data.get('tipo_cobertura') or None,
            nombre_cobertura=data.get('nombre_cobertura') or None,
            telefono_fijo=data.get('telefono_fijo') or None,
            celular=data.get('celular') or None,
            consentimiento_aceptado=False,
        )
        ant, _ = AntecedentePersonal.objects.get_or_create(paciente=paciente)
        if antecedentes_data:
            for k, v in antecedentes_data.items():
                if hasattr(ant, k):
                    setattr(ant, k, v)
            ant.save()
        if operativo is not None:
            OperativoAlumno.objects.create(
                operativo=operativo,
                paciente=paciente,
                curso=curso,
                apellido=persona.apellido or '',
                nombre=persona.nombre or '',
                tipo_dni=persona.tipo_dni or 'DNI',
                dni=persona.dni,
                fecha_nacimiento=persona.fecha_nacimiento,
                sexo=persona.sexo or '',
            )

    return paciente


def actualizar_antecedentes_paciente(paciente, data):
    ant, _ = AntecedentePersonal.objects.get_or_create(paciente=paciente)
    for k, v in data.items():
        if hasattr(ant, k):
            setattr(ant, k, v)
    ant.save()
    return ant


def listar_alumnos_escuela(escuela_id):
    return Paciente.objects.filter(escuela_id=escuela_id).select_related(
        'persona', 'domicilio', 'escuela',
    ).order_by('persona__apellido', 'persona__nombre')

"""Seed de desarrollo: flujo PROSANE completo con datos bien llenos.

Parte de operativos en BORRADOR con alumnos (ver seed_escuelas_operativos) y
los avanza para mostrar todos los estados y las 4 secciones (E/A/M/O):

- 1er operativo -> FINALIZADO (todos completos o ausentes).
- 2do operativo -> EN_CURSO mezclado (completos, parciales, ausentes).
- 3er operativo -> CONFIRMADO (solo E+A, sin evaluaciones).
- El resto queda en BORRADOR sin tocar.

Solo para desarrollo local (SEEDS_ENABLED).
"""
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.antecedentes.models import AntecedentePersonal
from apps.escuelas.models import Escuela
from apps.operativos import services
from apps.operativos.models import (
    EvaluacionMedica, EvaluacionOdontologica, Operativo, OperativoAlumno,
)
from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
from apps.usuarios.models import Usuario


def _edad(fecha):
    if not fecha:
        return 9
    hoy = date.today()
    return max(5, hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day)))


def _asegurar_paciente(alumno, escuela):
    """Crea Persona+Domicilio+Paciente vinculados si el alumno no tiene."""
    if alumno.paciente_id:
        return alumno.paciente
    persona = Persona.objects.create(
        nombre=alumno.nombre or 'Sin nombre',
        apellido=alumno.apellido or 'Sin apellido',
        dni=alumno.dni,
        tipo_dni=alumno.tipo_dni or 'DNI',
        sexo=alumno.sexo or 'otro',
        fecha_nacimiento=alumno.fecha_nacimiento or date(2018, 1, 1),
    )
    domicilio = Domicilio.objects.create(localidad='Salta')
    paciente = Paciente.objects.create(
        persona=persona,
        domicilio=domicilio,
        escuela=escuela,
        edad=_edad(alumno.fecha_nacimiento),
        celular='3875000000',
        tipo_cobertura='obra_social',
        nombre_cobertura='OSDE',
    )
    AntecedentePersonal.objects.get_or_create(paciente=paciente)
    alumno.paciente = paciente
    alumno.save(update_fields=['paciente', 'updated_at'])
    return paciente


def _cargar_e(alumno, i):
    """Sección escuela (E) con datos variados pero creíbles."""
    alumno.escuela_preocupa_salud = (i % 4 == 0)
    alumno.escuela_preocupa_detalle = 'Control de peso' if i % 4 == 0 else ''
    alumno.escuela_dificultad_lenguaje = (i % 5 == 0)
    alumno.escuela_bajo_tratamiento = (i % 6 == 0)
    alumno.escuela_completado = True
    alumno.save(update_fields=[
        'escuela_preocupa_salud', 'escuela_preocupa_detalle',
        'escuela_dificultad_lenguaje', 'escuela_bajo_tratamiento',
        'escuela_completado', 'updated_at',
    ])


def _cargar_a(alumno, escuela):
    """Datos personales y familia (A): paciente + antecedentes."""
    paciente = _asegurar_paciente(alumno, escuela)
    paciente.edad = _edad(alumno.fecha_nacimiento)
    paciente.celular = '3875123456'
    paciente.tipo_cobertura = 'obra_social'
    paciente.nombre_cobertura = 'OSDE'
    paciente.save(update_fields=['edad', 'celular', 'tipo_cobertura', 'nombre_cobertura', 'updated_at'])
    ant, _ = AntecedentePersonal.objects.get_or_create(paciente=paciente)
    ant.nacio_prematuro = 'NO'
    ant.peso_nacimiento = '3200'
    ant.asma_espasmos = 'SI' if (alumno.id.int % 3 == 0) else 'NO'
    ant.otros_problemas_salud = 'NINGUNO'
    # Debe ser un valor del desplegable (menos_1_anio, mas_1_anio,
    # no_recuerda o NINGUNA): cualquier otro rompe la pantalla de datos.
    ant.ultima_consulta_medica = (
        'menos_1_anio' if (alumno.id.int % 2 == 0) else 'mas_1_anio'
    )
    ant.save()
    alumno.antecedentes_completado = True
    alumno.save(update_fields=['antecedentes_completado', 'updated_at'])


def _cargar_m(alumno, medico):
    """Evaluación médica (M) completa y variada."""
    peso = Decimal(22 + (alumno.id.int % 12)) + Decimal('0.5')
    talla = Decimal(115 + (alumno.id.int % 20)) + Decimal('0.0')
    imc = (peso / ((talla / 100) ** 2)).quantize(Decimal('0.01'))
    EvaluacionMedica.objects.update_or_create(
        operativo_alumno=alumno,
        defaults={
            'profesional': medico,
            'fecha_evaluacion': timezone.now(),
            'examen_realizado': True,
            'lugar_examen': 'escuela',
            'trajo_carnet': True,
            'carnet_completo': alumno.id.int % 2 == 0,
            'peso': peso,
            'talla': talla,
            'imc': imc,
            'percentil_talla': 'mayor_igual_3',
            'percentil_imc': 'entre_10_84',
            'pas': 100,
            'pad': 60,
            'presion_clasificacion': 'normal',
            'agudeza_evaluada': True,
            'ojo_derecho': '10/10',
            'ojo_izquierdo': '10/10',
            'usa_lentes': False,
            'audiometria_realizada': True,
            'audiometria_resultado': 'pasa',
            'hallazgos': {'piel': {'estado': 'sin', 'detalle': ''}},
            'derivaciones': {'odontologia': {'deriva': alumno.id.int % 2 == 0, 'motivo': 'Control'}},
            'completada': True,
        },
    )


def _cargar_o(alumno, odontologo):
    """Evaluación odontológica (O) completa y variada."""
    EvaluacionOdontologica.objects.update_or_create(
        operativo_alumno=alumno,
        defaults={
            'profesional': odontologo,
            'fecha_evaluacion': timezone.now(),
            'salud_bucal': 'sin_hallazgos' if alumno.id.int % 2 == 0 else 'con_hallazgos',
            'caries': alumno.id.int % 2 == 1,
            'topicacion_fluor': True,
            'ensenanza_cepillado': True,
            'alta_basica': True,
            'cpo_c': 0,
            'cpo_p': 0,
            'cpo_o': 0,
            'ceo_c': 1 if alumno.id.int % 2 == 1 else 0,
            'ceo_e': 0,
            'ceo_o': 0,
            'odontograma': {'51': 'sano', '55': 'sano', '61': 'sano', '65': 'sano'},
            'completada': True,
        },
    )


def _completo(alumno):
    alumno.estado = OperativoAlumno.PRESENTE
    alumno.save(update_fields=['estado', 'updated_at'])
    if alumno.completo:
        alumno.estado = OperativoAlumno.EVALUADO
        alumno.save(update_fields=['estado', 'updated_at'])


class Command(BaseCommand):
    help = "Completa el flujo demo E/A/M/O y avanza estados (solo dev)."

    def handle(self, *args, **options):
        if not getattr(settings, "SEEDS_ENABLED", False):
            raise CommandError(
                "SEEDS_ENABLED no está activo: este comando es SOLO para desarrollo local."
            )
        medico = Usuario.objects.filter(email='medico@prosane.test').first()
        odontologo = Usuario.objects.filter(email='odontologo@prosane.test').first()
        if not medico or not odontologo:
            raise CommandError("Faltan medico@prosane.test u odontologo@prosane.test")

        borradores = [
            op for op in
            Operativo.objects.filter(estado=Operativo.BORRADOR).order_by('fecha')
            if op.alumnos.exists()
        ]
        if not borradores:
            raise CommandError(
                "No hay operativos en borrador con alumnos. "
                "Corré seed_escuelas_operativos primero."
            )

        planes = ['finalizado', 'en_curso', 'confirmado']
        for i, operativo in enumerate(borradores):
            plan = planes[i % len(planes)]
            alumnos = list(operativo.alumnos.order_by('apellido', 'nombre', 'dni'))
            self.stdout.write(f"> {operativo} -> {plan} ({len(alumnos)} alumnos)")

            for i, alumno in enumerate(alumnos):
                if plan == 'finalizado':
                    # Todos completos salvo 1 ausente (también cuenta como completo).
                    if i == len(alumnos) - 1:
                        alumno.estado = OperativoAlumno.AUSENTE
                        alumno.save(update_fields=['estado', 'updated_at'])
                        continue
                    _cargar_e(alumno, i)
                    _cargar_a(alumno, operativo.escuela)
                    _cargar_m(alumno, medico)
                    _cargar_o(alumno, odontologo)
                    _completo(alumno)
                elif plan == 'en_curso':
                    mod = i % 5
                    if mod == 4:
                        alumno.estado = OperativoAlumno.AUSENTE
                        alumno.save(update_fields=['estado', 'updated_at'])
                    elif mod in (0, 1):
                        _cargar_e(alumno, i)
                        _cargar_a(alumno, operativo.escuela)
                        _cargar_m(alumno, medico)
                        _cargar_o(alumno, odontologo)
                        _completo(alumno)
                    elif mod == 2:
                        _cargar_e(alumno, i)
                        _cargar_a(alumno, operativo.escuela)
                        _cargar_m(alumno, medico)
                        alumno.estado = OperativoAlumno.PRESENTE
                        alumno.save(update_fields=['estado', 'updated_at'])
                    else:
                        _cargar_e(alumno, i)
                        alumno.estado = OperativoAlumno.PRESENTE
                        alumno.save(update_fields=['estado', 'updated_at'])
                else:  # confirmado: solo E+A, sin evaluaciones
                    _cargar_e(alumno, i)
                    if i % 4 != 3:
                        _cargar_a(alumno, operativo.escuela)
                    alumno.estado = OperativoAlumno.PRESENTE
                    alumno.save(update_fields=['estado', 'updated_at'])

            services.confirmar_operativo(operativo.id)
            self.stdout.write("    + confirmado")
            if plan in ('finalizado', 'en_curso'):
                services.iniciar_operativo(operativo.id)
                self.stdout.write("    + en curso")
            if plan == 'finalizado':
                services.finalizar_operativo(operativo.id)
                self.stdout.write("    + finalizado")

        self.stdout.write(self.style.SUCCESS("seed_demo_flujo completado"))

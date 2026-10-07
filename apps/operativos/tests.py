import io
import csv
from datetime import date

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from rest_framework.test import APITestCase

from apps.escuelas.models import Escuela, Curso
from apps.personas.models import Domicilio, Persona
from apps.usuarios.models import Usuario
from apps.operativos.models import (
    Operativo, OperativoProfesional, OperativoAlumno,
    EvaluacionMedica, EvaluacionOdontologica,
)
from apps.operativos import services
from apps.operativos.serializers import EvaluacionOdontologicaSerializer


# ──────────────────────────────────────────────
#  Helpers de test
# ──────────────────────────────────────────────
_user_counter = 0


def _create_administrativo(**kwargs):
    global _user_counter
    _user_counter += 1
    return Usuario.objects.create_user(
        email=kwargs.get('email', f'administrativo{_user_counter}@test.com'),
        password='pass1234',
    )


def _create_medico(**kwargs):
    global _user_counter
    _user_counter += 1
    user = Usuario.objects.create_user(
        email=kwargs.get('email', f'medico{_user_counter}@test.com'),
        password='pass1234',
    )
    _asignar_rol(user, 'medico')
    return user


def _create_odontologo(**kwargs):
    global _user_counter
    _user_counter += 1
    user = Usuario.objects.create_user(
        email=kwargs.get('email', f'odontologo{_user_counter}@test.com'),
        password='pass1234',
    )
    _asignar_rol(user, 'odontologo')
    return user


def _create_escuela():
    return Escuela.objects.create(nombre='Escuela Test', cue='TEST001')


def _create_curso(escuela):
    return Curso.objects.create(
        escuela=escuela, nivel='primario',
        sala_grado_anio='1°', division='A', ciclo_lectivo=2026,
    )


def _create_operativo(escuela, **kwargs):
    defaults = {'fecha': date(2026, 6, 20)}
    defaults.update(kwargs)
    return services.crear_operativo(escuela.id, **defaults)


def _completar_alumno(alumno):
    """Deja un alumno completo: evaluaciones cargadas + sección escuela + datos personales y familia."""
    EvaluacionMedica.objects.update_or_create(
        operativo_alumno=alumno, defaults={'completada': True},
    )
    EvaluacionOdontologica.objects.update_or_create(
        operativo_alumno=alumno, defaults={'completada': True},
    )
    alumno.escuela_completado = True
    alumno.antecedentes_completado = True
    alumno.estado = OperativoAlumno.EVALUADO
    alumno.save()


def _asignar_rol(usuario, rol_nombre):
    from apps.usuarios.models import Rol, ActionRole, Action
    rol, _ = Rol.objects.get_or_create(rol=rol_nombre)
    for action in Action.objects.filter(
        name__in=ActionRole.objects.filter(role=rol).values_list('action__name', flat=True),
    ):
        pass
    usuario.roles.add(rol)


# ──────────────────────────────────────────────
#  Tests de modelos
# ──────────────────────────────────────────────
class OperativoModelTest(TestCase):
    def test_estado_default_borrador(self):
        op = Operativo(escuela_id='00000000-0000-0000-0000-000000000000', fecha='2026-06-20')
        self.assertEqual(op.estado, Operativo.BORRADOR)

    def test_lugar_default_escuela(self):
        op = Operativo(escuela_id='00000000-0000-0000-0000-000000000000', fecha='2026-06-20')
        self.assertEqual(op.lugar_realizacion, 'escuela')

    def test_str_con_nombre(self):
        escuela = _create_escuela()
        op = Operativo.objects.create(
            nombre='Mi operativo', escuela=escuela, fecha='2026-06-20',
        )
        self.assertIn('Mi operativo', str(op))

    def test_str_sin_nombre(self):
        escuela = Escuela.objects.create(nombre='Escuela X', cue='TEST002')
        op = Operativo.objects.create(escuela=escuela, fecha='2026-06-20')
        self.assertIn('Escuela X', str(op))

    def test_db_table(self):
        self.assertEqual(Operativo._meta.db_table, 'operativos')

    def test_ordering(self):
        self.assertEqual(Operativo._meta.ordering, ['-fecha', '-created_at'])


class OperativoProfesionalModelTest(TestCase):
    def test_unique_together(self):
        self.assertIn(
            ('operativo', 'profesional'),
            OperativoProfesional._meta.unique_together,
        )

    def test_str(self):
        escuela = _create_escuela()
        op = _create_operativo(escuela)
        user = _create_administrativo()
        rel = OperativoProfesional.objects.create(
            operativo=op, profesional=user, rol_en_operativo='medico',
        )
        self.assertIn(user.email, str(rel))


class OperativoAlumnoModelTest(TestCase):
    def test_unique_together(self):
        self.assertIn(
            ('operativo', 'dni'),
            OperativoAlumno._meta.unique_together,
        )

    def test_estado_default_pendiente(self):
        alumno = OperativoAlumno(
            operativo_id='00000000-0000-0000-0000-000000000000',
            apellido='García', nombre='Juan', dni='12345678',
        )
        self.assertEqual(alumno.estado, OperativoAlumno.PENDIENTE)

    def test_str(self):
        escuela = _create_escuela()
        op = _create_operativo(escuela)
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Juan', dni='12345678',
        )
        self.assertIn('García', str(alumno))
        self.assertIn('Juan', str(alumno))
        self.assertIn('12345678', str(alumno))


# ──────────────────────────────────────────────
#  Tests de modelos de evaluación clínica (Fase 1)
# ──────────────────────────────────────────────
class EvaluacionModelTest(TestCase):
    def setUp(self):
        self.escuela = _create_escuela()
        self.operativo = _create_operativo(self.escuela)
        self.alumno = OperativoAlumno.objects.create(
            operativo=self.operativo,
            apellido='Pérez', nombre='Ana', dni='30111222',
        )
        self.medico = _create_medico()
        self.odontologo = _create_odontologo()

    def test_crear_evaluacion_medica(self):
        ev = EvaluacionMedica.objects.create(
            operativo_alumno=self.alumno,
            profesional=self.medico,
        )
        self.assertEqual(ev.operativo_alumno, self.alumno)
        self.assertEqual(ev.profesional, self.medico)
        # Acceso vía related_name OneToOne
        self.assertEqual(self.alumno.evaluacion_medica, ev)
        self.assertFalse(ev.completada)
        self.assertFalse(ev.examen_realizado)

    def test_crear_evaluacion_odontologica(self):
        ev = EvaluacionOdontologica.objects.create(
            operativo_alumno=self.alumno,
            profesional=self.odontologo,
        )
        self.assertEqual(ev.operativo_alumno, self.alumno)
        self.assertEqual(ev.profesional, self.odontologo)
        self.assertEqual(self.alumno.evaluacion_odontologica, ev)
        self.assertFalse(ev.completada)

    def test_jsonfields_default_dict_vacio_medica(self):
        ev = EvaluacionMedica.objects.create(operativo_alumno=self.alumno)
        ev.refresh_from_db()
        self.assertEqual(ev.hallazgos, {})
        self.assertEqual(ev.derivaciones, {})

    def test_jsonfield_default_dict_vacio_odontologica(self):
        ev = EvaluacionOdontologica.objects.create(operativo_alumno=self.alumno)
        ev.refresh_from_db()
        self.assertEqual(ev.odontograma, {})

    def test_jsonfields_persisten_datos(self):
        ev = EvaluacionMedica.objects.create(
            operativo_alumno=self.alumno,
            hallazgos={'piel': {'estado': 'sin', 'detalle': ''}},
            derivaciones={'odontologia': {'deriva': True, 'motivo': 'caries'}},
        )
        ev.refresh_from_db()
        self.assertEqual(ev.hallazgos['piel']['estado'], 'sin')
        self.assertTrue(ev.derivaciones['odontologia']['deriva'])

    def test_odontograma_admite_caras_y_raiz_por_pieza(self):
        serializer = EvaluacionOdontologicaSerializer(data={
            'odontograma': {
                '16': {
                    'denticion': 'permanente',
                    'estado_general': '',
                    'caras': {'oclusal': 'caries', 'mesial': 'restauracion'},
                    'raiz': 'conducto_pendiente',
                    'notas': 'Controlar',
                },
            },
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_odontograma_rechaza_caras_en_pieza_ausente(self):
        serializer = EvaluacionOdontologicaSerializer(data={
            'odontograma': {
                '16': {
                    'estado_general': 'ausente',
                    'caras': {'oclusal': 'caries'},
                },
            },
        })
        self.assertFalse(serializer.is_valid())

    def test_onetoone_evita_duplicados(self):
        from django.db import IntegrityError, transaction
        EvaluacionMedica.objects.create(operativo_alumno=self.alumno)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EvaluacionMedica.objects.create(operativo_alumno=self.alumno)


class CoercionDependientesTest(TestCase):
    """Al cambiar un estado se limpian sus dependientes (sin checks huérfanos).

    Los frontends ya limpian al alternar; el serializer coacciona como red
    de seguridad para cualquier cliente.
    """

    def setUp(self):
        from apps.operativos.serializers import (
            EvaluacionMedicaSerializer, SeccionEscuelaSerializer,
        )
        self.EvaluacionMedicaSerializer = EvaluacionMedicaSerializer
        self.SeccionEscuelaSerializer = SeccionEscuelaSerializer
        self.escuela = _create_escuela()
        self.operativo = _create_operativo(self.escuela)
        self.alumno = OperativoAlumno.objects.create(
            operativo=self.operativo,
            apellido='Pérez', nombre='Ana', dni='30111222',
        )

    def test_medica_limpia_hallazgos_y_derivaciones(self):
        s = self.EvaluacionMedicaSerializer(data={
            'hallazgos': {
                'piel': {'estado': 'sin', 'detalle': 'x', 'checks': ['escabiosis']},
                'cardiovascular': {'estado': 'con', 'detalle': '', 'checks': ['soplo']},
            },
            'derivaciones': {
                'odontologia': {'deriva': False, 'motivo': 'viejo'},
                'nutricion': {'deriva': True, 'motivo': 'control'},
            },
        })
        self.assertTrue(s.is_valid(), s.errors)
        ev = s.save(operativo_alumno=self.alumno)
        ev.refresh_from_db()
        self.assertEqual(ev.hallazgos['piel']['checks'], [])
        self.assertEqual(ev.hallazgos['piel']['detalle'], '')
        self.assertEqual(ev.hallazgos['cardiovascular']['checks'], ['soplo'])
        self.assertEqual(ev.derivaciones['odontologia']['motivo'], '')
        self.assertEqual(ev.derivaciones['nutricion']['motivo'], 'control')

    def test_medica_limpia_secciones_no_evaluadas(self):
        s = self.EvaluacionMedicaSerializer(data={
            'examen_realizado': True, 'motivo_no_examen': 'ausente', 'lugar_examen': 'escuela',
            'trajo_carnet': False, 'carnet_completo': True,
            'vacunas_aplicadas': 'x', 'vacunas_indicadas': 'y',
            'antropometria_evaluada': False, 'peso': 50, 'percentil_talla': 'mayor_igual_3',
            'presion_evaluada': False, 'pas': 110, 'presion_clasificacion': 'normal',
            'agudeza_evaluada': False, 'ojo_derecho': '10/10', 'usa_lentes': True,
            'audiometria_realizada': False, 'audiometria_resultado': 'pasa',
        })
        self.assertTrue(s.is_valid(), s.errors)
        ev = s.save(operativo_alumno=self.alumno)
        ev.refresh_from_db()
        self.assertEqual(ev.motivo_no_examen, '')
        self.assertEqual(ev.lugar_examen, 'escuela')
        self.assertFalse(ev.carnet_completo)
        self.assertEqual(ev.vacunas_aplicadas, '')
        self.assertIsNone(ev.peso)
        self.assertEqual(ev.percentil_talla, '')
        self.assertIsNone(ev.pas)
        self.assertEqual(ev.ojo_derecho, '')
        self.assertFalse(ev.usa_lentes)
        self.assertEqual(ev.audiometria_resultado, '')

    def test_medica_patch_parcial_coacciona_con_instancia(self):
        ev = EvaluacionMedica.objects.create(
            operativo_alumno=self.alumno, presion_evaluada=True, pas=110, pad=70,
        )
        s = self.EvaluacionMedicaSerializer(
            ev, data={'presion_evaluada': False}, partial=True,
        )
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        ev.refresh_from_db()
        self.assertIsNone(ev.pas)
        self.assertIsNone(ev.pad)

    def test_odontologica_limpia_salud_bucal(self):
        s = EvaluacionOdontologicaSerializer(data={
            'salud_bucal': 'sin_hallazgos',
            'lesiones_tejidos_blandos': True, 'caries': True, 'otros': 'viejo',
        })
        self.assertTrue(s.is_valid(), s.errors)
        ev = s.save(operativo_alumno=self.alumno)
        ev.refresh_from_db()
        self.assertFalse(ev.lesiones_tejidos_blandos)
        self.assertFalse(ev.caries)
        self.assertEqual(ev.otros, '')

    def test_seccion_escuela_limpia_detalle(self):
        s = self.SeccionEscuelaSerializer(
            self.alumno,
            data={'escuela_preocupa_salud': False, 'escuela_preocupa_detalle': 'viejo'},
            partial=True,
        )
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.escuela_preocupa_detalle, '')


class OperativoAlumnoEscuelaFieldsTest(TestCase):
    def test_campos_escuela_existen(self):
        campos = {f.name for f in OperativoAlumno._meta.get_fields()}
        for nombre in (
            'escuela_preocupa_salud',
            'escuela_preocupa_detalle',
            'escuela_dificultad_lenguaje',
            'escuela_bajo_tratamiento',
            'escuela_completado',
        ):
            self.assertIn(nombre, campos)

    def test_defaults_campos_escuela(self):
        escuela = _create_escuela()
        operativo = _create_operativo(escuela)
        alumno = OperativoAlumno.objects.create(
            operativo=operativo,
            apellido='López', nombre='Luis', dni='40555666',
        )
        alumno.refresh_from_db()
        self.assertFalse(alumno.escuela_preocupa_salud)
        self.assertEqual(alumno.escuela_preocupa_detalle, '')
        self.assertFalse(alumno.escuela_dificultad_lenguaje)
        self.assertFalse(alumno.escuela_bajo_tratamiento)
        self.assertFalse(alumno.escuela_completado)


# ──────────────────────────────────────────────
#  Tests de servicios
# ──────────────────────────────────────────────
class ServiciosTest(TestCase):
    def setUp(self):
        self.escuela = _create_escuela()
        self.administrativo = _create_administrativo()
        self.medico = _create_medico()
        self.odontologo = _create_odontologo()

    def test_crear_operativo_borrador(self):
        op = services.crear_operativo(self.escuela.id, fecha=date(2026, 7, 1))
        self.assertEqual(op.estado, Operativo.BORRADOR)
        self.assertEqual(op.fecha, date(2026, 7, 1))

    def test_crear_operativo_con_nombre(self):
        op = services.crear_operativo(
            self.escuela.id, fecha=date(2026, 7, 1),
            nombre='Operativo Julio',
        )
        self.assertEqual(op.nombre, 'Operativo Julio')

    def test_tiene_conflicto_fecha_sin_conflicto(self):
        op = _create_operativo(self.escuela, fecha=date(2026, 7, 1))
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        op.estado = Operativo.CONFIRMADO
        op.save(update_fields=['estado'])
        self.assertTrue(services.tiene_conflicto_fecha(self.medico.id, date(2026, 7, 1)))

    def test_tiene_conflicto_fecha_diferente_dia(self):
        op = _create_operativo(self.escuela, fecha=date(2026, 7, 1))
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        op.estado = Operativo.CONFIRMADO
        op.save(update_fields=['estado'])
        self.assertFalse(services.tiene_conflicto_fecha(self.medico.id, date(2026, 7, 2)))

    def test_asignar_profesional_ok(self):
        op = _create_operativo(self.escuela)
        rel = services.asignar_profesional(op.id, self.medico.id, 'medico')
        self.assertEqual(rel.rol_en_operativo, 'medico')
        self.assertFalse(rel.confirmado)

    def test_asignar_profesional_duplicado(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        with self.assertRaises(ValueError):
            services.asignar_profesional(op.id, self.medico.id, 'odontologo')

    def test_asignar_profesional_deriva_rol(self):
        op = _create_operativo(self.escuela)
        rel = services.asignar_profesional(op.id, self.odontologo.id)
        self.assertEqual(rel.rol_en_operativo, 'odontologo')

    def test_asignar_profesional_rol_distinto_da_error(self):
        op = _create_operativo(self.escuela)
        with self.assertRaises(ValueError):
            services.asignar_profesional(op.id, self.medico.id, 'odontologo')

    def test_asignar_profesional_ambos_roles_exige_rol(self):
        _asignar_rol(self.medico, 'odontologo')
        op = _create_operativo(self.escuela)
        with self.assertRaises(ValueError):
            services.asignar_profesional(op.id, self.medico.id)
        rel = services.asignar_profesional(op.id, self.medico.id, 'odontologo')
        self.assertEqual(rel.rol_en_operativo, 'odontologo')

    def test_asignar_profesional_sin_rol_profesional_da_error(self):
        op = _create_operativo(self.escuela)
        with self.assertRaises(ValueError):
            services.asignar_profesional(op.id, self.administrativo.id)

    def test_asignar_profesional_solo_borrador(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='Test', nombre='Test', dni='99999999',
        )
        services.confirmar_operativo(op.id)
        with self.assertRaises(ValueError):
            services.asignar_profesional(op.id, self.odontologo.id, 'odontologo')

    def test_confirmar_operativo_sin_profesionales(self):
        op = _create_operativo(self.escuela)
        with self.assertRaises(ValueError):
            services.confirmar_operativo(op.id)

    def test_confirmar_operativo_sin_alumnos(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        with self.assertRaises(ValueError):
            services.confirmar_operativo(op.id)

    def test_confirmar_operativo_ok(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Juan', dni='12345678',
        )
        op = services.confirmar_operativo(op.id)
        self.assertEqual(op.estado, Operativo.CONFIRMADO)

    def test_confirmar_ya_confirmado(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Juan', dni='12345678',
        )
        services.confirmar_operativo(op.id)
        with self.assertRaises(ValueError):
            services.confirmar_operativo(op.id)

    def test_finalizar_solo_en_curso(self):
        op = _create_operativo(self.escuela)
        with self.assertRaises(ValueError):
            services.finalizar_operativo(op.id)

    def test_finalizar_con_alumnos_pendientes(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Juan', dni='12345678',
        )
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        with self.assertRaises(ValueError):
            services.finalizar_operativo(op.id)

    def test_finalizar_ok(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Juan', dni='12345678',
        )
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        _completar_alumno(alumno)
        op = services.finalizar_operativo(op.id)
        self.assertEqual(op.estado, Operativo.FINALIZADO)

    def test_cancelar_borrador(self):
        op = _create_operativo(self.escuela)
        op = services.cancelar_operativo(op.id)
        self.assertEqual(op.estado, Operativo.CANCELADO)

    def test_cancelar_confirmado(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        OperativoAlumno.objects.create(
            operativo=op, apellido='Test', nombre='Test', dni='99999999',
        )
        services.confirmar_operativo(op.id)
        op = services.cancelar_operativo(op.id)
        self.assertEqual(op.estado, Operativo.CANCELADO)

    def test_no_cancelar_finalizado(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='Test', nombre='Test', dni='99999999',
        )
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        _completar_alumno(alumno)
        services.finalizar_operativo(op.id)
        with self.assertRaises(ValueError):
            services.cancelar_operativo(op.id)

    def test_transicion_invalida(self):
        op = _create_operativo(self.escuela)
        with self.assertRaises(ValueError):
            services.transicionar_estado(op.id, Operativo.FINALIZADO)


# ──────────────────────────────────────────────
#  Tests de completitud y gating (Fase 3)
# ──────────────────────────────────────────────
class CompletitudTest(TestCase):
    def setUp(self):
        self.escuela = _create_escuela()
        self.medico = _create_medico()

    def _operativo_en_curso(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Juan', dni='12345678',
        )
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        return op, alumno

    def test_alumno_ausente_es_completo(self):
        op, alumno = self._operativo_en_curso()
        alumno.estado = OperativoAlumno.AUSENTE
        alumno.save()
        self.assertTrue(alumno.completo)

    def test_alumno_sin_evaluaciones_no_es_completo(self):
        op, alumno = self._operativo_en_curso()
        self.assertFalse(alumno.completo)

    def test_alumno_solo_medica_no_es_completo(self):
        op, alumno = self._operativo_en_curso()
        EvaluacionMedica.objects.create(operativo_alumno=alumno, completada=True)
        alumno.escuela_completado = True
        alumno.save()
        self.assertFalse(alumno.completo)

    def test_alumno_evaluaciones_no_completadas_no_es_completo(self):
        op, alumno = self._operativo_en_curso()
        EvaluacionMedica.objects.create(operativo_alumno=alumno, completada=False)
        EvaluacionOdontologica.objects.create(operativo_alumno=alumno, completada=False)
        alumno.escuela_completado = True
        alumno.save()
        self.assertFalse(alumno.completo)

    def test_alumno_completo_con_todo(self):
        op, alumno = self._operativo_en_curso()
        _completar_alumno(alumno)
        self.assertTrue(alumno.completo)

    def test_operativo_sin_alumnos_no_puede_finalizar(self):
        op = _create_operativo(self.escuela)
        self.assertFalse(op.puede_finalizar)

    def test_operativo_no_puede_finalizar_si_falta_evaluacion(self):
        op, alumno = self._operativo_en_curso()
        self.assertFalse(op.puede_finalizar)
        with self.assertRaises(ValueError):
            services.finalizar_operativo(op.id)

    def test_operativo_puede_finalizar_todos_completos(self):
        op, alumno = self._operativo_en_curso()
        _completar_alumno(alumno)
        self.assertTrue(op.puede_finalizar)
        op = services.finalizar_operativo(op.id)
        self.assertEqual(op.estado, Operativo.FINALIZADO)

    def test_operativo_puede_finalizar_mezcla_completos_y_ausentes(self):
        op, alumno = self._operativo_en_curso()
        _completar_alumno(alumno)
        ausente = OperativoAlumno.objects.create(
            operativo=op, apellido='Pérez', nombre='Ana', dni='99999999',
            estado=OperativoAlumno.AUSENTE,
        )
        self.assertTrue(op.puede_finalizar)


# ──────────────────────────────────────────────
#  Tests de importar CSV
# ──────────────────────────────────────────────
class ImportarCSVTest(TestCase):
    def setUp(self):
        self.escuela = _create_escuela()
        self.operativo = _create_operativo(self.escuela)

    def _make_csv(self, rows, con_curso=False):
        fieldnames = [
            'apellido', 'nombre', 'tipo_dni', 'dni', 'fecha_nacimiento', 'sexo',
        ]
        if con_curso:
            fieldnames += ['grado', 'division']
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return SimpleUploadedFile(
            'alumnos.csv', output.getvalue().encode('utf-8-sig'),
            content_type='text/csv',
        )

    def test_importar_csv_crea_alumnos(self):
        csv_file = self._make_csv([
            {'apellido': 'García', 'nombre': 'Juan', 'tipo_dni': 'DNI', 'dni': '12345678', 'fecha_nacimiento': '15/03/2015', 'sexo': 'M'},
            {'apellido': 'Pérez', 'nombre': 'María', 'tipo_dni': 'DNI', 'dni': '23456789', 'fecha_nacimiento': '22/07/2014', 'sexo': 'F'},
        ])
        resultado = services.importar_csv(self.operativo.id, csv_file)
        self.assertEqual(resultado['creados'], 2)
        self.assertEqual(resultado['duplicados'], 0)
        self.assertEqual(resultado['errores'], [])
        juan = OperativoAlumno.objects.get(dni='12345678')
        self.assertEqual(juan.fecha_nacimiento, date(2015, 3, 15))
        maria = OperativoAlumno.objects.get(dni='23456789')
        self.assertEqual(maria.fecha_nacimiento, date(2014, 7, 22))

    def test_importar_csv_duplicados(self):
        OperativoAlumno.objects.create(
            operativo=self.operativo, apellido='García', nombre='Juan', dni='12345678',
        )
        csv_file = self._make_csv([
            {'apellido': 'García', 'nombre': 'Juan', 'tipo_dni': 'DNI', 'dni': '12345678', 'fecha_nacimiento': '', 'sexo': ''},
            {'apellido': 'Pérez', 'nombre': 'María', 'tipo_dni': 'DNI', 'dni': '23456789', 'fecha_nacimiento': '', 'sexo': ''},
        ])
        resultado = services.importar_csv(self.operativo.id, csv_file)
        self.assertEqual(resultado['creados'], 1)
        self.assertEqual(resultado['duplicados'], 1)

    def test_importar_csv_dni_vacio(self):
        csv_file = self._make_csv([
            {'apellido': 'García', 'nombre': 'Juan', 'tipo_dni': 'DNI', 'dni': '', 'fecha_nacimiento': '', 'sexo': ''},
        ])
        resultado = services.importar_csv(self.operativo.id, csv_file)
        self.assertEqual(resultado['creados'], 0)
        self.assertEqual(len(resultado['errores']), 1)

    def test_importar_csv_crea_curso_por_grado_division(self):
        csv_file = self._make_csv([
            {'apellido': 'García', 'nombre': 'Juan', 'tipo_dni': 'DNI', 'dni': '12345678', 'fecha_nacimiento': '15/03/2015', 'sexo': 'M', 'grado': '1°', 'division': 'A'},
            {'apellido': 'Pérez', 'nombre': 'María', 'tipo_dni': 'DNI', 'dni': '23456789', 'fecha_nacimiento': '22/07/2014', 'sexo': 'F', 'grado': '2°', 'division': 'B'},
            {'apellido': 'Sosa', 'nombre': 'Ana', 'tipo_dni': 'DNI', 'dni': '34567890', 'fecha_nacimiento': '10/01/2014', 'sexo': 'F', 'grado': '1°', 'division': 'A'},
        ], con_curso=True)
        resultado = services.importar_csv(self.operativo.id, csv_file)
        self.assertEqual(resultado['creados'], 3)
        self.assertEqual(resultado['errores'], [])
        self.assertEqual(resultado['creados_por_curso'], {'1° A': 2, '2° B': 1})

        curso_1a = Curso.objects.get(escuela=self.escuela, sala_grado_anio='1°', division='A')
        curso_2b = Curso.objects.get(escuela=self.escuela, sala_grado_anio='2°', division='B')
        self.assertEqual(OperativoAlumno.objects.get(dni='12345678').curso, curso_1a)
        self.assertEqual(OperativoAlumno.objects.get(dni='34567890').curso, curso_1a)
        self.assertEqual(OperativoAlumno.objects.get(dni='23456789').curso, curso_2b)
        self.assertEqual(curso_1a.ciclo_lectivo, 2026)

    def test_importar_csv_sin_curso_deja_curso_nulo(self):
        csv_file = self._make_csv([
            {'apellido': 'García', 'nombre': 'Juan', 'tipo_dni': 'DNI', 'dni': '12345678', 'fecha_nacimiento': '', 'sexo': ''},
        ])
        resultado = services.importar_csv(self.operativo.id, csv_file)
        self.assertEqual(resultado['creados'], 1)
        self.assertEqual(resultado['creados_por_curso'], {})
        self.assertIsNone(OperativoAlumno.objects.get(dni='12345678').curso)

    def test_importar_csv_reutiliza_curso_existente(self):
        _create_curso(self.escuela)
        csv_file = self._make_csv([
            {'apellido': 'García', 'nombre': 'Juan', 'tipo_dni': 'DNI', 'dni': '12345678', 'fecha_nacimiento': '', 'sexo': '', 'grado': '1°', 'division': 'A'},
        ], con_curso=True)
        resultado = services.importar_csv(self.operativo.id, csv_file)
        self.assertEqual(resultado['creados'], 1)
        self.assertEqual(Curso.objects.filter(escuela=self.escuela).count(), 1)

    def test_importar_csv_vincula_paciente_existente_por_dni(self):
        persona = Persona.objects.create(
            nombre='Alumno', apellido='Registrado', dni='12345678', tipo_dni='DNI',
            sexo='F', fecha_nacimiento='2018-01-01',
        )
        domicilio = Domicilio.objects.create(
            localidad='Salta',
        )
        from apps.pacientes.models import Paciente
        paciente = Paciente.objects.create(
            persona=persona, domicilio=domicilio, escuela=self.escuela, edad=8,
        )
        csv_file = self._make_csv([
            {'apellido': 'Registrado', 'nombre': 'Alumno', 'tipo_dni': 'DNI', 'dni': '12345678', 'fecha_nacimiento': '', 'sexo': ''},
        ])
        services.importar_csv(self.operativo.id, csv_file)
        self.assertEqual(
            OperativoAlumno.objects.get(dni='12345678').paciente_id,
            paciente.id,
        )

    def test_importar_csv_solo_borrador_o_confirmado(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, _create_medico().id, 'medico')
        OperativoAlumno.objects.create(
            operativo=op, apellido='Test', nombre='Test', dni='99999999',
        )
        services.confirmar_operativo(op.id)
        csv_file = self._make_csv([
            {'apellido': 'Nuevo', 'nombre': 'Test', 'tipo_dni': 'DNI', 'dni': '11111111', 'fecha_nacimiento': '', 'sexo': ''},
        ])
        resultado = services.importar_csv(op.id, csv_file)
        self.assertEqual(resultado['creados'], 1)

    def test_importar_csv_rechaza_finalizado(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, _create_medico().id, 'medico')
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='Test', nombre='Test', dni='99999999',
        )
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        _completar_alumno(alumno)
        services.finalizar_operativo(op.id)
        csv_file = self._make_csv([
            {'apellido': 'Nuevo', 'nombre': 'Test', 'tipo_dni': 'DNI', 'dni': '11111111', 'fecha_nacimiento': '', 'sexo': ''},
        ])
        with self.assertRaises(ValueError):
            services.importar_csv(op.id, csv_file)

    def test_conflicto_fecha_excluye_borrador(self):
        op1 = _create_operativo(self.escuela, fecha=date(2026, 7, 1))
        medico = _create_medico()
        services.asignar_profesional(op1.id, medico.id, 'medico')
        self.assertFalse(services.tiene_conflicto_fecha(medico.id, date(2026, 7, 1)))


# ──────────────────────────────────────────────
#  Tests de API
# ──────────────────────────────────────────────
@override_settings(ROOT_URLCONF='config.test_urls')
class OperativoAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def setUp(self):
        self.administrativo = _create_administrativo()
        self.medico = _create_medico()
        self.odontologo = _create_odontologo()
        self.otro_administrativo = _create_administrativo()

        # Assign roles
        from apps.usuarios.models import Rol
        self.rol_administrativo = Rol.objects.get(rol='administrativo')
        self.rol_medico = Rol.objects.get(rol='medico')
        self.rol_odontologo = Rol.objects.get(rol='odontologo')
        self.administrativo.roles.add(self.rol_administrativo)
        self.medico.roles.add(self.rol_medico)
        self.odontologo.roles.add(self.rol_odontologo)
        self.otro_administrativo.roles.add(self.rol_administrativo)

        self.client.force_authenticate(user=self.administrativo)

    def _create_operativo(self, **kwargs):
        defaults = {
            'escuela': self.escuela,
            'fecha': date(2026, 6, 20),
            'created_by': self.administrativo,
        }
        defaults.update(kwargs)
        return Operativo.objects.create(**defaults)

    def _create_alumno(self, operativo, **kwargs):
        defaults = {
            'apellido': 'García', 'nombre': 'Juan', 'dni': '12345678',
        }
        defaults.update(kwargs)
        return OperativoAlumno.objects.create(operativo=operativo, **defaults)

    # ─── List ───
    def test_list_operativos(self):
        self._create_operativo()
        response = self.client.get('/api/v1/operativos/')
        self.assertEqual(response.status_code, 200)

    def test_list_operativos_sin_permiso(self):
        self.client.force_authenticate(user=self.medico)
        response = self.client.get('/api/v1/operativos/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_list_operativos_filtro_escuela(self):
        op = self._create_operativo()
        otra = Escuela.objects.create(nombre='Otra', cue='OTRO')
        self._create_operativo(escuela=otra)
        response = self.client.get(f'/api/v1/operativos/?escuela_id={self.escuela.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_list_operativos_filtro_estado(self):
        self._create_operativo()
        response = self.client.get(f'/api/v1/operativos/?estado={Operativo.BORRADOR}')
        self.assertEqual(response.status_code, 200)

    def test_list_operativos_administrativo_solo_propios(self):
        self._create_operativo(created_by=self.administrativo)
        self._create_operativo(created_by=self.otro_administrativo)
        response = self.client.get('/api/v1/operativos/')
        self.assertEqual(len(response.data), 1)

    def test_list_operativos_medico_solo_asignados(self):
        op = self._create_operativo(created_by=self.otro_administrativo)
        OperativoProfesional.objects.create(
            operativo=op, profesional=self.medico, rol_en_operativo='medico',
        )
        self.client.force_authenticate(user=self.medico)
        response = self.client.get('/api/v1/operativos/')
        self.assertEqual(len(response.data), 1)

    # ─── Create ───
    def test_create_operativo(self):
        data = {
            'escuela': str(self.escuela.id),
            'fecha': '2026-07-01',
            'nombre': 'Nuevo operativo',
        }
        response = self.client.post('/api/v1/operativos/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['estado'], Operativo.BORRADOR)

    def test_create_operativo_sin_permiso(self):
        self.client.force_authenticate(user=self.medico)
        data = {
            'escuela': str(self.escuela.id),
            'fecha': '2026-07-01',
        }
        response = self.client.post('/api/v1/operativos/', data, format='json')
        self.assertEqual(response.status_code, 403)

    # ─── Detail ───
    def test_get_operativo(self):
        op = self._create_operativo()
        response = self.client.get(f'/api/v1/operativos/{op.id}/')
        self.assertEqual(response.status_code, 200)

    def test_patch_operativo(self):
        op = self._create_operativo()
        response = self.client.patch(
            f'/api/v1/operativos/{op.id}/',
            {'nombre': 'Actualizado'}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nombre'], 'Actualizado')

    def test_delete_operativo_cancela(self):
        op = self._create_operativo()
        response = self.client.delete(f'/api/v1/operativos/{op.id}/')
        self.assertEqual(response.status_code, 204)
        op.refresh_from_db()
        self.assertEqual(op.estado, Operativo.CANCELADO)

    # ─── Confirmar ───
    def test_confirmar_operativo(self):
        op = self._create_operativo()
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        self._create_alumno(op)
        response = self.client.post(f'/api/v1/operativos/{op.id}/confirmar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['estado'], Operativo.CONFIRMADO)

    def test_confirmar_operativo_sin_condiciones(self):
        op = self._create_operativo()
        response = self.client.post(f'/api/v1/operativos/{op.id}/confirmar/')
        self.assertEqual(response.status_code, 409)

    # ─── Finalizar ───
    def test_finalizar_operativo(self):
        op = self._create_operativo()
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        alumno = self._create_alumno(op)
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        _completar_alumno(alumno)
        response = self.client.post(f'/api/v1/operativos/{op.id}/finalizar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['estado'], Operativo.FINALIZADO)

    def test_finalizar_con_pendientes(self):
        op = self._create_operativo()
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        self._create_alumno(op)
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        response = self.client.post(f'/api/v1/operativos/{op.id}/finalizar/')
        self.assertEqual(response.status_code, 409)

    # ─── Cancelar ───
    def test_cancelar_operativo(self):
        op = self._create_operativo()
        response = self.client.post(f'/api/v1/operativos/{op.id}/cancelar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['estado'], Operativo.CANCELADO)

    # ─── Profesionales ───
    def test_list_profesionales(self):
        op = self._create_operativo()
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        response = self.client.get(f'/api/v1/operativos/{op.id}/profesionales/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_asignar_profesional(self):
        op = self._create_operativo()
        data = {'profesional': str(self.medico.id), 'rol_en_operativo': 'medico'}
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/profesionales/asignar/',
            data, format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['rol_en_operativo'], 'medico')

    def test_asignar_profesional_sin_datos(self):
        op = self._create_operativo()
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/profesionales/asignar/',
            {}, format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_asignar_profesional_sin_rol_deriva(self):
        op = self._create_operativo()
        data = {'profesional': str(self.odontologo.id)}
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/profesionales/asignar/',
            data, format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['rol_en_operativo'], 'odontologo')

    def test_asignar_profesional_rol_distinto_da_409(self):
        op = self._create_operativo()
        data = {'profesional': str(self.medico.id), 'rol_en_operativo': 'odontologo'}
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/profesionales/asignar/',
            data, format='json',
        )
        self.assertEqual(response.status_code, 409)

    def test_remover_profesional(self):
        op = self._create_operativo()
        rel = services.asignar_profesional(op.id, self.medico.id, 'medico')
        response = self.client.delete(
            f'/api/v1/operativos/{op.id}/profesionales/{rel.id}/remover/',
        )
        self.assertEqual(response.status_code, 204)

    # ─── Alumnos ───
    def test_list_alumnos(self):
        op = self._create_operativo()
        self._create_alumno(op)
        response = self.client.get(f'/api/v1/operativos/{op.id}/alumnos/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_list_alumnos_filtro_estado(self):
        op = self._create_operativo()
        self._create_alumno(op)
        response = self.client.get(
            f'/api/v1/operativos/{op.id}/alumnos/?estado={OperativoAlumno.PENDIENTE}',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_create_alumno(self):
        # El alta de alumnos en el operativo exige importarNominaOperativo
        # (solo escuela y superadmin).
        from apps.usuarios.models import Usuario
        admin = Usuario.objects.create_superuser(
            email='admin-alumno@test.com', password='test1234',
        )
        self.client.force_authenticate(user=admin)
        op = self._create_operativo()
        data = {'apellido': 'López', 'nombre': 'Carlos', 'dni': '34567890'}
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/alumnos/',
            data, format='json',
        )
        self.assertEqual(response.status_code, 201)

    def test_patch_alumno_estado(self):
        # El administrativo solo lee alumnos: el cambio de estado le da 403.
        op = self._create_operativo()
        alumno = self._create_alumno(op)
        response = self.client.patch(
            f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/',
            {'estado': OperativoAlumno.PRESENTE}, format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_patch_alumno_estado_superadmin(self):
        from apps.usuarios.models import Usuario
        admin = Usuario.objects.create_superuser(
            email='admin-estado@test.com', password='test1234',
        )
        self.client.force_authenticate(user=admin)
        op = self._create_operativo()
        alumno = self._create_alumno(op)
        response = self.client.patch(
            f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/',
            {'estado': OperativoAlumno.PRESENTE}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['estado'], OperativoAlumno.PRESENTE)

    def test_delete_alumno(self):
        op = self._create_operativo()
        alumno = self._create_alumno(op)
        response = self.client.delete(
            f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/',
        )
        self.assertEqual(response.status_code, 204)

    # ─── Importar CSV (solo escuela y superadmin) ───
    def test_importar_csv_api(self):
        from apps.usuarios.models import Usuario
        admin = Usuario.objects.create_superuser(
            email='admin-csv@test.com', password='test1234',
        )
        self.client.force_authenticate(user=admin)
        op = self._create_operativo()
        csv_content = 'apellido,nombre,tipo_dni,dni,fecha_nacimiento,sexo\nGarcía,Juan,DNI,12345678,15/03/2015,M\n'
        csv_file = SimpleUploadedFile(
            'alumnos.csv', csv_content.encode('utf-8-sig'),
            content_type='text/csv',
        )
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/alumnos/importar-csv/',
            {'archivo': csv_file}, format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['creados'], 1)

    def test_importar_csv_sin_archivo(self):
        from apps.usuarios.models import Usuario
        admin = Usuario.objects.create_superuser(
            email='admin-csv2@test.com', password='test1234',
        )
        self.client.force_authenticate(user=admin)
        op = self._create_operativo()
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/alumnos/importar-csv/',
            {}, format='multipart',
        )
        self.assertEqual(response.status_code, 400)

    # ─── Permisos por rol ───
    def test_medico_ve_asignados(self):
        op = self._create_operativo(created_by=self.otro_administrativo)
        OperativoProfesional.objects.create(
            operativo=op, profesional=self.medico, rol_en_operativo='medico',
        )
        self.client.force_authenticate(user=self.medico)
        response = self.client.get(f'/api/v1/operativos/{op.id}/')
        self.assertEqual(response.status_code, 200)

    def test_medico_no_ve_no_asignados(self):
        self._create_operativo(created_by=self.otro_administrativo)
        self.client.force_authenticate(user=self.medico)
        response = self.client.get('/api/v1/operativos/')
        self.assertEqual(len(response.data), 0)

    # ─── Aislamiento a nivel de objeto ───
    def test_administrativo_no_ve_operativo_de_otro_administrativo(self):
        op = self._create_operativo(created_by=self.otro_administrativo)
        response = self.client.get(f'/api/v1/operativos/{op.id}/')
        self.assertEqual(response.status_code, 404)

    def test_medico_no_ve_operativo_no_asignado(self):
        op = self._create_operativo(created_by=self.otro_administrativo)
        self.client.force_authenticate(user=self.medico)
        response = self.client.get(f'/api/v1/operativos/{op.id}/')
        self.assertEqual(response.status_code, 404)

    def test_administrativo_no_lista_alumnos_de_otro_administrativo(self):
        op = self._create_operativo(created_by=self.otro_administrativo)
        self._create_alumno(op)
        response = self.client.get(f'/api/v1/operativos/{op.id}/alumnos/')
        self.assertEqual(response.status_code, 404)

    def test_medico_no_lista_alumnos_de_no_asignado(self):
        op = self._create_operativo(created_by=self.otro_administrativo)
        self._create_alumno(op)
        self.client.force_authenticate(user=self.medico)
        response = self.client.get(f'/api/v1/operativos/{op.id}/alumnos/')
        self.assertEqual(response.status_code, 404)

    def test_administrativo_no_confirma_operativo_de_otro_administrativo(self):
        op = self._create_operativo(created_by=self.otro_administrativo)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        self._create_alumno(op)
        response = self.client.post(f'/api/v1/operativos/{op.id}/confirmar/')
        self.assertEqual(response.status_code, 404)

    def test_administrativo_no_cancela_operativo_de_otro_administrativo(self):
        op = self._create_operativo(created_by=self.otro_administrativo)
        response = self.client.delete(f'/api/v1/operativos/{op.id}/')
        self.assertEqual(response.status_code, 404)

    def test_administrativo_no_asigna_profesional_en_operativo_de_otro(self):
        op = self._create_operativo(created_by=self.otro_administrativo)
        data = {'profesional': str(self.medico.id), 'rol_en_operativo': 'medico'}
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/profesionales/asignar/',
            data, format='json',
        )
        self.assertEqual(response.status_code, 404)

    def test_administrativo_no_importa_csv_sin_permiso(self):
        op = self._create_operativo(created_by=self.administrativo)
        csv_content = 'apellido,nombre,tipo_dni,dni,fecha_nacimiento,sexo\nGarcía,Juan,DNI,12345678,15/03/2015,M\n'
        csv_file = SimpleUploadedFile(
            'alumnos.csv', csv_content.encode('utf-8-sig'),
            content_type='text/csv',
        )
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/alumnos/importar-csv/',
            {'archivo': csv_file}, format='multipart',
        )
        self.assertEqual(response.status_code, 403)

    def test_no_remover_profesional_de_operativo_confirmado(self):
        op = self._create_operativo()
        rel = services.asignar_profesional(op.id, self.medico.id, 'medico')
        self._create_alumno(op)
        services.confirmar_operativo(op.id)
        response = self.client.delete(
            f'/api/v1/operativos/{op.id}/profesionales/{rel.id}/remover/',
        )
        self.assertEqual(response.status_code, 409)

    # ─── Completitud / gating (Fase 3) ───
    def test_finalizar_devuelve_409_si_falta_evaluacion(self):
        op = self._create_operativo()
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        self._create_alumno(op)
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        response = self.client.post(f'/api/v1/operativos/{op.id}/finalizar/')
        self.assertEqual(response.status_code, 409)

    def test_completitud_endpoint_pendiente(self):
        op = self._create_operativo()
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        self._create_alumno(op)
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        response = self.client.get(f'/api/v1/operativos/{op.id}/completitud/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_alumnos'], 1)
        self.assertEqual(response.data['completos'], 0)
        self.assertEqual(response.data['pendientes'], 1)
        self.assertFalse(response.data['puede_finalizar'])

    def test_completitud_endpoint_completo(self):
        op = self._create_operativo()
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        alumno = self._create_alumno(op)
        services.confirmar_operativo(op.id)
        services.transicionar_estado(op.id, Operativo.EN_CURSO)
        _completar_alumno(alumno)
        response = self.client.get(f'/api/v1/operativos/{op.id}/completitud/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_alumnos'], 1)
        self.assertEqual(response.data['completos'], 1)
        self.assertEqual(response.data['pendientes'], 0)
        self.assertTrue(response.data['puede_finalizar'])


class PlanillaPdfTest(TestCase):
    """Planilla réplica del papel: genera PDF válido con datos mínimos y completos."""

    def _finalizado_con_alumno(self, **alumno_kwargs):
        escuela = _create_escuela()
        op = _create_operativo(escuela)
        op.estado = Operativo.FINALIZADO
        op.save()
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='Pérez', nombre='Juan', dni='50111222',
            **alumno_kwargs,
        )
        return op, alumno

    def test_genera_pdf_minimo(self):
        from apps.operativos.services_planilla import generar_planilla_pdf
        op, alumno = self._finalizado_con_alumno()
        pdf = generar_planilla_pdf(op, alumno)
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_genera_pdf_completo(self):
        from datetime import date
        from apps.antecedentes.models import AntecedenteFamiliar, AntecedentePersonal
        from apps.operativos.services_planilla import generar_planilla_pdf
        op, alumno = self._finalizado_con_alumno(
            fecha_nacimiento=date(2016, 3, 10), sexo='M',
        )
        persona = Persona.objects.create(
            nombre='Juan', apellido='Pérez', dni='50111222',
            tipo_dni='DNI', sexo='M', fecha_nacimiento=date(2016, 3, 10),
        )
        domicilio = Domicilio.objects.create(
            calle='San Martín', nro_calle='123', localidad='Salta',
            provincia='Salta',
        )
        from apps.pacientes.models import Paciente
        paciente = Paciente.objects.create(
            domicilio=domicilio, persona=persona, edad=10,
            tiene_cud='NO', tipo_cobertura='Obra Social',
            telefono_fijo='3874000000', consentimiento_aceptado=True,
        )
        alumno.paciente = paciente
        alumno.escuela_preocupa_salud = True
        alumno.escuela_preocupa_detalle = 'Corre muy rápido en el recreo'
        alumno.escuela_dificultad_lenguaje = True
        alumno.escuela_completado = True
        alumno.antecedentes_completado = True
        alumno.estado = OperativoAlumno.EVALUADO
        alumno.observaciones = 'Sin observaciones.'
        alumno.save()
        AntecedentePersonal.objects.create(
            paciente=paciente, nacio_prematuro='SI', peso_nacimiento='2,8',
            asma_espasmos='SI', traumatismo_internacion='NO',
            internacion_previa='SI', causa_hospitalizacion='Neumonía a los 4 años',
            tratamiento_actual='SI', descripcion_tratamiento='Salbutamol',
            ultima_consulta_medica='Hace menos de 1 año',
            primera_menstruacion='NO',
        )
        AntecedenteFamiliar.objects.create(
            paciente=paciente, problemas_salud='SI',
            detalle_problema_salud='Asma del padre',
            familiar_con_muerte_subita='NO',
        )
        EvaluacionMedica.objects.create(
            operativo_alumno=alumno, completada=True,
            examen_realizado=True, lugar_examen='escuela',
            trajo_carnet=True, carnet_completo=False,
            vacunas_indicadas='Refuerzo antitetánica',
            antropometria_evaluada=True, peso=32.5, talla=135,
            imc=17.8, percentil_talla='mayor_igual_3', percentil_imc='entre_10_84',
            presion_evaluada=True, pas=95, pad=60,
            agudeza_evaluada=True, ojo_derecho='10/10', ojo_izquierdo='9/10',
            audiometria_realizada=True, audiometria_resultado='pasa',
            hallazgos={
                'piel': {'estado': 'con', 'detalle': '', 'checks': ['pediculosis']},
                'cardiovascular': {'estado': 'sin', 'detalle': '', 'checks': []},
            },
            derivaciones={
                'odontologia': {'deriva': True, 'motivo': 'Caries'},
                'nutricion': {'deriva': False, 'motivo': ''},
            },
        )
        EvaluacionOdontologica.objects.create(
            operativo_alumno=alumno, completada=True,
            salud_bucal='con_hallazgos', caries=True,
            cpo_c=True, cpo_p=False, cpo_o=False,
            ceo_c=False, ceo_e=False, ceo_o=True,
            ensenanza_cepillado=True,
            odontograma={
                '16': {'estado_general': '', 'caras': {'oclusal': 'caries'}, 'raiz': '', 'notas': ''},
                '11': {'estado_general': '', 'caras': {'oclusal': 'tratada'}, 'raiz': '', 'notas': ''},
            },
        )
        pdf = generar_planilla_pdf(op, alumno)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 10000)


class PlanillaAlumnoAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def setUp(self):
        from apps.usuarios.models import Rol
        self.administrativo = _create_administrativo()
        self.administrativo.roles.add(Rol.objects.get(rol='administrativo'))
        self.client.force_authenticate(user=self.administrativo)

    def _finalizado_con_alumno(self):
        op = _create_operativo(self.escuela)
        op.estado = Operativo.FINALIZADO
        op.created_by = self.administrativo
        op.save()
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Ana', dni='50222333',
        )
        return op, alumno

    def test_planilla_pdf_200(self):
        op, alumno = self._finalizado_con_alumno()
        response = self.client.get(f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/planilla/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_planilla_requiere_finalizado(self):
        op = _create_operativo(self.escuela)
        op.created_by = self.administrativo
        op.save()
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Ana', dni='50222333',
        )
        response = self.client.get(f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/planilla/')
        self.assertEqual(response.status_code, 409)

    def test_planilla_sin_permiso_403(self):
        op, alumno = self._finalizado_con_alumno()
        otro = _create_administrativo()
        self.client.force_authenticate(user=otro)
        response = self.client.get(f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/planilla/')
        self.assertEqual(response.status_code, 403)


class AuditoriaDocumentosTest(APITestCase):
    """Cada acceso/impresión de documentos con datos sensibles se audita
    (respalda la leyenda de protección de datos del footer)."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def setUp(self):
        from apps.usuarios.models import Rol
        self.administrativo = _create_administrativo()
        self.administrativo.roles.add(Rol.objects.get(rol='administrativo'))
        self.client.force_authenticate(user=self.administrativo)

    def _finalizado_con_alumno(self):
        op = _create_operativo(self.escuela)
        op.estado = Operativo.FINALIZADO
        op.created_by = self.administrativo
        op.save()
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Ana', dni='50222333',
        )
        return op, alumno

    def test_planilla_audita_acceso(self):
        from apps.operativos.models import AuditoriaDocumento
        op, alumno = self._finalizado_con_alumno()
        response = self.client.get(f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/planilla/')
        self.assertEqual(response.status_code, 200)
        log = AuditoriaDocumento.objects.filter(
            tipo=AuditoriaDocumento.PLANILLA, alumno=alumno,
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.administrativo)
        self.assertEqual(log.operativo, op)
        self.assertEqual(log.ip, '127.0.0.1')

    def test_constancia_audita_acceso(self):
        from apps.operativos.models import AuditoriaDocumento
        op, alumno = self._finalizado_con_alumno()
        response = self.client.get(f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/constancia/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditoriaDocumento.objects.filter(
                tipo=AuditoriaDocumento.CONSTANCIA, alumno=alumno,
            ).exists()
        )

    def test_export_csv_audita_sin_alumno(self):
        from apps.operativos.models import AuditoriaDocumento
        op, _alumno = self._finalizado_con_alumno()
        response = self.client.get(f'/api/v1/operativos/{op.id}/export/?formato=csv')
        self.assertEqual(response.status_code, 200)
        log = AuditoriaDocumento.objects.filter(
            tipo=AuditoriaDocumento.EXPORT_CSV, operativo=op,
        ).first()
        self.assertIsNotNone(log)
        self.assertIsNone(log.alumno)

    def test_no_audita_si_no_finalizado(self):
        from apps.operativos.models import AuditoriaDocumento
        op = _create_operativo(self.escuela)
        op.created_by = self.administrativo
        op.save()
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Ana', dni='50222333',
        )
        response = self.client.get(f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/planilla/')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(AuditoriaDocumento.objects.exists())


class FooterProteccionDatosTest(APITestCase):
    """La leyenda de protección de datos (Leyes 25.326 y 26.529) sale impresa."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def _finalizado_con_alumno(self):
        op = _create_operativo(self.escuela)
        op.estado = Operativo.FINALIZADO
        op.save()
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Ana', dni='50222333',
        )
        return op, alumno

    @staticmethod
    def _texto(pdf_bytes):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join((p.extract_text() or "") for p in reader.pages)

    def test_planilla_sin_footer_solo_datos(self):
        from apps.operativos.services_planilla import generar_planilla_pdf
        op, alumno = self._finalizado_con_alumno()
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(generar_planilla_pdf(op, alumno)))
        paginas = [page.extract_text() or "" for page in reader.pages]
        self.assertEqual(len(paginas), 2)
        for texto in paginas:
            self.assertNotIn('registrados y auditados', texto)

    def test_constancia_trae_leyenda_completa(self):
        from apps.operativos.services_constancia import generar_constancia_pdf
        op, alumno = self._finalizado_con_alumno()
        texto = self._texto(generar_constancia_pdf(op, alumno))
        self.assertIn('dato personal sensible de salud', texto)
        self.assertIn('26.529', texto)
        self.assertIn('registrados y auditados', texto)


class CompletarFlagTest(APITestCase):
    """El flag `completar` del wizard controla completada sin romper legacy."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def _en_curso_con_alumno(self):
        from apps.operativos import services
        op = _create_operativo(self.escuela)
        medico = _create_medico()
        services.asignar_profesional(op.id, medico.id, 'medico')
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='A', nombre='B', dni='40111226')
        services.confirmar_operativo(op.id)
        services.iniciar_operativo(op.id)
        self.client.force_authenticate(user=medico)
        return op, alumno

    def _url(self, op, alumno):
        return f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/evaluacion-medica/'

    def test_parcial_no_marca_completada(self):
        op, alumno = self._en_curso_con_alumno()
        res = self.client.put(self._url(op, alumno), {'peso': 30, 'completar': False},
                              format='json')
        self.assertEqual(res.status_code, 200)
        alumno.refresh_from_db()
        self.assertEqual(alumno.evaluacion_medica.peso, 30)
        self.assertFalse(alumno.evaluacion_medica.completada)

    def test_final_marca_completada(self):
        op, alumno = self._en_curso_con_alumno()
        res = self.client.put(self._url(op, alumno), {'peso': 30, 'completar': True},
                              format='json')
        self.assertEqual(res.status_code, 200)
        alumno.refresh_from_db()
        self.assertTrue(alumno.evaluacion_medica.completada)

    def test_sin_flag_legacy_marca_completada(self):
        op, alumno = self._en_curso_con_alumno()
        res = self.client.put(self._url(op, alumno), {'peso': 30}, format='json')
        self.assertEqual(res.status_code, 200)
        alumno.refresh_from_db()
        self.assertTrue(alumno.evaluacion_medica.completada)


class CompletarFlagOdontoTest(APITestCase):
    """El flag `completar` del wizard controla completada en odontológica."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def _en_curso_con_alumno(self):
        from apps.operativos import services
        op = _create_operativo(self.escuela)
        odontologo = _create_odontologo()
        services.asignar_profesional(op.id, odontologo.id, 'odontologo')
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='A', nombre='B', dni='40111227')
        services.confirmar_operativo(op.id)
        services.iniciar_operativo(op.id)
        self.client.force_authenticate(user=odontologo)
        return op, alumno

    def _url(self, op, alumno):
        return f'/api/v1/operativos/{op.id}/alumnos/{alumno.id}/evaluacion-odontologica/'

    def test_parcial_no_marca_completada(self):
        op, alumno = self._en_curso_con_alumno()
        res = self.client.put(self._url(op, alumno),
                              {'salud_bucal': 'sin_hallazgos', 'completar': False},
                              format='json')
        self.assertEqual(res.status_code, 200)
        alumno.refresh_from_db()
        self.assertEqual(alumno.evaluacion_odontologica.salud_bucal, 'sin_hallazgos')
        self.assertFalse(alumno.evaluacion_odontologica.completada)

    def test_final_marca_completada(self):
        op, alumno = self._en_curso_con_alumno()
        res = self.client.put(self._url(op, alumno),
                              {'salud_bucal': 'sin_hallazgos', 'completar': True},
                              format='json')
        self.assertEqual(res.status_code, 200)
        alumno.refresh_from_db()
        self.assertTrue(alumno.evaluacion_odontologica.completada)


class CompletarFlagDatosSeccionTest(APITestCase):
    """El flag `completar` controla los completado de datos y sección E."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def setUp(self):
        from apps.usuarios.models import Usuario
        self.superadmin = Usuario.objects.create_superuser(
            email='rootflag@test.com', password='Clave1234')
        self.client.force_authenticate(user=self.superadmin)
        self.op = _create_operativo(self.escuela)
        self.alumno = OperativoAlumno.objects.create(
            operativo=self.op, apellido='A', nombre='B', dni='40111228')

    def _url_datos(self):
        return f'/api/v1/operativos/{self.op.id}/alumnos/{self.alumno.id}/datos/'

    def _url_seccion(self):
        return f'/api/v1/operativos/{self.op.id}/alumnos/{self.alumno.id}/seccion-escuela/'

    def test_datos_parcial_no_marca_completado(self):
        res = self.client.patch(self._url_datos(),
                                {'apellido': 'A2', 'completar': False},
                                format='json')
        self.assertEqual(res.status_code, 200)
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.apellido, 'A2')
        self.assertFalse(self.alumno.antecedentes_completado)

    def test_datos_final_marca_completado(self):
        res = self.client.patch(self._url_datos(),
                                {'apellido': 'A2', 'completar': True},
                                format='json')
        self.assertEqual(res.status_code, 200)
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.antecedentes_completado)

    def test_datos_sin_flag_legacy_marca_completado(self):
        res = self.client.patch(self._url_datos(), {'apellido': 'A2'},
                                format='json')
        self.assertEqual(res.status_code, 200)
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.antecedentes_completado)

    def test_seccion_parcial_no_marca_completado(self):
        res = self.client.patch(self._url_seccion(),
                                {'escuela_preocupa_salud': True,
                                 'completar': False},
                                format='json')
        self.assertEqual(res.status_code, 200)
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.escuela_preocupa_salud)
        self.assertFalse(self.alumno.escuela_completado)

    def test_seccion_final_marca_completado(self):
        res = self.client.patch(self._url_seccion(),
                                {'escuela_preocupa_salud': False,
                                 'completar': True},
                                format='json')
        self.assertEqual(res.status_code, 200)
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.escuela_completado)


# ──────────────────────────────────────────────
#  Administrativo solo-lectura en alumnos
# ──────────────────────────────────────────────
class AdministrativoSoloLecturaTest(APITestCase):
    """El administrativo lee todo (verOperativo) pero no modifica alumnos."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def setUp(self):
        self.administrativo = _create_administrativo()
        from apps.usuarios.models import Rol
        self.administrativo.roles.add(Rol.objects.get(rol='administrativo'))
        self.op = Operativo.objects.create(
            escuela=self.escuela, fecha=date(2026, 6, 20),
            created_by=self.administrativo,
        )
        self.alumno = OperativoAlumno.objects.create(
            operativo=self.op, apellido='Lopez', nombre='Mario',
            dni='40111225')
        self.client.force_authenticate(user=self.administrativo)

    def _url_seccion(self):
        return f'/api/v1/operativos/{self.op.id}/alumnos/{self.alumno.id}/seccion-escuela/'

    def _url_datos(self):
        return f'/api/v1/operativos/{self.op.id}/alumnos/{self.alumno.id}/datos/'

    def test_lee_alumnos_y_datos(self):
        res = self.client.get(f'/api/v1/operativos/{self.op.id}/alumnos/')
        self.assertEqual(res.status_code, 200)
        res = self.client.get(
            f'/api/v1/operativos/{self.op.id}/alumnos/{self.alumno.id}/')
        self.assertEqual(res.status_code, 200)
        res = self.client.get(self._url_datos())
        self.assertEqual(res.status_code, 200)

    def test_lee_pero_no_escribe_seccion_escuela(self):
        res = self.client.get(self._url_seccion())
        self.assertEqual(res.status_code, 200)
        res = self.client.patch(
            self._url_seccion(), {'escuela_preocupa_salud': True},
            format='json')
        self.assertEqual(res.status_code, 403)

    def test_no_cambia_estado_ni_datos(self):
        res = self.client.patch(
            f'/api/v1/operativos/{self.op.id}/alumnos/{self.alumno.id}/',
            {'estado': OperativoAlumno.PRESENTE}, format='json')
        self.assertEqual(res.status_code, 403)
        res = self.client.patch(
            self._url_datos(), {'apellido': 'X'}, format='json')
        self.assertEqual(res.status_code, 403)


# ──────────────────────────────────────────────
#  Derivaciones por operativo (Anexo I 4.6)
# ──────────────────────────────────────────────
class DerivacionesOperativoTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def setUp(self):
        self.administrativo = _create_administrativo()
        self.medico = _create_medico()
        self.otro_medico = _create_medico()
        from apps.usuarios.models import Rol
        self.administrativo.roles.add(Rol.objects.get(rol='administrativo'))
        self.medico.roles.add(Rol.objects.get(rol='medico'))
        self.otro_medico.roles.add(Rol.objects.get(rol='medico'))
        self.op = Operativo.objects.create(
            escuela=self.escuela, fecha=date(2026, 6, 20),
            created_by=self.administrativo,
        )
        self.alumno = OperativoAlumno.objects.create(
            operativo=self.op, apellido='Perez', nombre='Ana', dni='40111223')
        OperativoProfesional.objects.create(
            operativo=self.op, profesional=self.medico, rol_en_operativo='medico')
        EvaluacionMedica.objects.update_or_create(
            operativo_alumno=self.alumno,
            defaults={
                'profesional': self.medico,
                'derivaciones': {
                    'oftalmologia': {'deriva': True, 'motivo': 'Disminucion agudeza'},
                    'odontologia': {'deriva': False, 'motivo': ''},
                    'pediatria': {'deriva': True, 'motivo': 'Control'},
                },
            },
        )
        self.url = f'/api/v1/operativos/{self.op.id}/derivaciones/'

    def test_lista_como_administrativo(self):
        self.client.force_authenticate(user=self.administrativo)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total'], 2)
        esps = {d['especialidad'] for d in res.data['derivaciones']}
        self.assertEqual(esps, {'oftalmologia', 'pediatria'})
        item = [d for d in res.data['derivaciones'] if d['especialidad'] == 'oftalmologia'][0]
        self.assertEqual(item['motivo'], 'Disminucion agudeza')
        self.assertEqual(item['dni'], '40111223')
        self.assertEqual(res.data['por_especialidad'], {'oftalmologia': 1, 'pediatria': 1})

    def test_filtro_especialidad(self):
        self.client.force_authenticate(user=self.administrativo)
        res = self.client.get(self.url, {'especialidad': 'pediatria'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total'], 1)

    def test_especialidad_invalida_400(self):
        self.client.force_authenticate(user=self.administrativo)
        res = self.client.get(self.url, {'especialidad': 'traumatologia'})
        self.assertEqual(res.status_code, 400)

    def test_medico_asignado_ve(self):
        self.client.force_authenticate(user=self.medico)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total'], 2)

    def test_medico_no_asignado_404(self):
        self.client.force_authenticate(user=self.otro_medico)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 404)

    def test_sin_derivaciones_total_cero(self):
        EvaluacionMedica.objects.filter(operativo_alumno=self.alumno).update(
            derivaciones={'odontologia': {'deriva': False, 'motivo': ''}})
        self.client.force_authenticate(user=self.administrativo)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total'], 0)


# ──────────────────────────────────────────────
#  Familia + consentimiento en /datos/ (Anexo I, solo lectura + auditoría)
# ──────────────────────────────────────────────
class DatosFamiliaConsentimientoTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_permissions', verbosity=0)
        cls.escuela = _create_escuela()

    def setUp(self):
        from apps.antecedentes.models import AntecedenteFamiliar
        from apps.auditoria.models import AuditoriaCambio
        from apps.pacientes.models import Paciente
        from apps.tutores.models import Tutor
        self.AntecedenteFamiliar = AntecedenteFamiliar
        self.AuditoriaCambio = AuditoriaCambio
        self.medico = _create_medico()
        self.escuela_user = _create_administrativo(email='escuela_fam@test.com')
        from apps.usuarios.models import Rol
        self.medico.roles.add(Rol.objects.get(rol='medico'))
        self.escuela_user.roles.add(Rol.objects.get(rol='escuela'))
        self.escuela_user.escuela = self.escuela
        self.escuela_user.save(update_fields=['escuela'])
        self.op = Operativo.objects.create(
            escuela=self.escuela, fecha=date(2026, 6, 20),
        )
        OperativoProfesional.objects.create(
            operativo=self.op, profesional=self.medico, rol_en_operativo='medico')
        persona_nino = Persona.objects.create(
            nombre='Ana', apellido='Perez', dni='40111224', tipo_dni='DNI',
            sexo='femenino', fecha_nacimiento=date(2018, 3, 4))
        dom = Domicilio.objects.create(localidad='Salta')
        persona_tutor = Persona.objects.create(
            nombre='Maria', apellido='Perez', dni='30111224', tipo_dni='DNI',
            sexo='femenino', fecha_nacimiento=date(1990, 5, 6))
        tutor = Tutor.objects.create(persona=persona_tutor, parentesco='madre')
        self.paciente = Paciente.objects.create(
            persona=persona_nino, domicilio=dom, tutor=tutor,
            escuela=self.escuela, edad=8,
            consentimiento_aceptado=True)
        AntecedenteFamiliar.objects.create(
            paciente=self.paciente, problemas_salud='SI',
            detalle_problema_salud='Diabetes', familiar_con_muerte_subita='NO')
        self.alumno = OperativoAlumno.objects.create(
            operativo=self.op, paciente=self.paciente,
            apellido='Perez', nombre='Ana', dni='40111224')
        self.url = f'/api/v1/operativos/{self.op.id}/alumnos/{self.alumno.id}/datos/'

    def test_medico_ve_familia_y_consentimiento_y_audita(self):
        self.client.force_authenticate(user=self.medico)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['antecedente_familiar']['problemas_salud'], 'SI')
        self.assertTrue(res.data['consentimiento']['aceptado'])
        self.assertEqual(res.data['tutor']['parentesco'], 'madre')
        self.assertEqual(res.data['tutor']['dni'], '30111224')
        aud = self.AuditoriaCambio.objects.filter(
            entidad='alumno_datos', accion='leer', entidad_id=self.alumno.id)
        self.assertEqual(aud.count(), 1)
        self.assertEqual(aud.first().actor_id, self.medico.id)

    def test_escuela_ve_pero_no_audita_lectura(self):
        self.client.force_authenticate(user=self.escuela_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.data['antecedente_familiar'])
        self.assertFalse(self.AuditoriaCambio.objects.filter(
            entidad='alumno_datos', accion='leer').exists())

    def test_medico_patch_sigue_403(self):
        self.client.force_authenticate(user=self.medico)
        res = self.client.patch(self.url, {'apellido': 'X'}, format='json')
        self.assertEqual(res.status_code, 403)

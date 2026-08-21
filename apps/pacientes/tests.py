from django.test import TestCase
from django.utils import timezone

from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
from apps.escuelas.models import Escuela
from apps.escuelas.models import Curso
from apps.operativos.models import Operativo, OperativoAlumno
from apps.tutores.models import Tutor
from apps.usuarios.models import Usuario
from apps.pacientes.services.alumnos import crear_alumno_escuela


class PacienteConsentimientoTest(TestCase):
    def test_paciente_persiste_consentimiento(self):
        usuario = Usuario.objects.create_user(email="tu@example.com", password="test1234")
        tutor_persona = Persona.objects.create(
            nombre="Marta", apellido="Tutora", dni="30000000",
            tipo_dni="DNI", sexo="F", fecha_nacimiento="1980-01-01",
        )
        tutor = Tutor.objects.create(persona=tutor_persona, usuario=usuario, parentesco="madre")
        nna = Persona.objects.create(
            nombre="Niño", apellido="Tutora", dni="55555555",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="2016-05-01",
        )
        dom = Domicilio.objects.create(calle="Falsa", nro_calle="123")

        p = Paciente.objects.create(
            persona=nna, domicilio=dom, tutor=tutor, edad=9,
            consentimiento_aceptado=True,
            fecha_consentimiento=timezone.now(),
        )
        p.refresh_from_db()
        self.assertTrue(p.consentimiento_aceptado)
        self.assertIsNotNone(p.fecha_consentimiento)
        self.assertEqual(p.adulto["dni"], "30000000")
        self.assertEqual(p.adulto["nombre"], "Marta")
        self.assertEqual(p.adulto["apellido"], "Tutora")


class AlumnoEscuelaServiceTest(TestCase):
    def test_crear_alumno_deja_paciente_vinculado_a_escuela_sin_tutor(self):
        escuela = Escuela.objects.create(nombre='Escuela de prueba')
        paciente = crear_alumno_escuela(escuela.id, {
            'persona': {
                'nombre': 'Ana', 'apellido': 'Prueba', 'dni': '70000001',
                'tipo_dni': 'DNI', 'sexo': 'F', 'fecha_nacimiento': '2018-01-01',
            },
            'domicilio': {'localidad': 'Salta'},
            'edad': 8,
        })

        paciente.refresh_from_db()
        self.assertEqual(paciente.escuela_id, escuela.id)
        self.assertIsNone(paciente.tutor_id)
        self.assertFalse(paciente.consentimiento_aceptado)

    def test_crear_alumno_asocia_directamente_curso_y_operativo(self):
        escuela = Escuela.objects.create(nombre='Escuela de operativo')
        curso = Curso.objects.create(
            escuela=escuela, sala_grado_anio='1°', division='A', ciclo_lectivo=2026,
        )
        operativo = Operativo.objects.create(
            escuela=escuela, fecha='2026-08-20', nombre='Operativo test',
        )
        paciente = crear_alumno_escuela(escuela.id, {
            'persona': {
                'nombre': 'Luis', 'apellido': 'Operativo', 'dni': '70000002',
                'tipo_dni': 'DNI', 'sexo': 'M', 'fecha_nacimiento': '2017-01-01',
            },
            'domicilio': {},
            'edad': 9,
            'curso_id': curso.id,
            'operativo_id': operativo.id,
        })

        alumno = OperativoAlumno.objects.get(operativo=operativo, paciente=paciente)
        self.assertEqual(alumno.curso_id, curso.id)
        self.assertEqual(alumno.dni, '70000002')

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
from apps.escuelas.models import Escuela
from apps.escuelas.models import Curso
from apps.operativos.models import Operativo, OperativoAlumno
from apps.tutores.models import Tutor
from apps.usuarios.models import Action, ActionRole, Rol, Usuario
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


class AlumnoEscuelaFiltroAPITest(APITestCase):
    """GET /alumnos/?escuela_id= — solo superadmin; el resto usa su escuela."""

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email='admin@test.com', password='test1234',
        )
        self.escuela_a = Escuela.objects.create(nombre='Escuela A')
        self.escuela_b = Escuela.objects.create(nombre='Escuela B')
        for escuela, dni in ((self.escuela_a, '70000101'), (self.escuela_b, '70000102')):
            crear_alumno_escuela(escuela.id, {
                'persona': {
                    'nombre': 'Ana', 'apellido': 'Prueba', 'dni': dni,
                    'tipo_dni': 'DNI', 'sexo': 'F', 'fecha_nacimiento': '2018-01-01',
                },
                'domicilio': {'localidad': 'Salta'},
                'edad': 8,
            })
        self.url = reverse('escuela-alumnos-list-create')

    def test_superadmin_filtra_por_escuela(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f'{self.url}?escuela_id={self.escuela_a.id}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_superadmin_escuela_id_invalido_da_400(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f'{self.url}?escuela_id=no-es-uuid')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_superadmin_escuela_inexistente_da_404(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(
            f'{self.url}?escuela_id=00000000-0000-0000-0000-000000000000'
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_usuario_escuela_no_puede_filtrar_otra_escuela(self):
        action = Action.objects.create(
            name='verAlumnosEscuela', label='Ver', type='crud',
            category='test', sort_order=1,
        )
        rol = Rol.objects.create(rol='escuela')
        ActionRole.objects.create(role=rol, action=action)
        usuario = Usuario.objects.create_user(
            email='esc@test.com', password='test1234', escuela=self.escuela_a,
        )
        usuario.roles.add(rol)
        self.client.force_authenticate(user=usuario)
        res = self.client.get(f'{self.url}?escuela_id={self.escuela_b.id}')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        # Sin filtro sigue viendo solo su escuela.
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

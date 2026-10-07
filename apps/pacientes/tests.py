from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
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


class AlumnoTutorTest(APITestCase):
    """La escuela carga los datos del tutor: alta anidada + upsert."""

    fixtures = ["roles", "users"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        call_command("seed_permissions", verbosity=0)

    def _auth(self, email):
        user = Usuario.objects.get(email=email)
        self.client.force_authenticate(user=user)
        return user

    def _asignar_escuela(self, email, escuela):
        user = Usuario.objects.get(email=email)
        user.escuela = escuela
        user.save(update_fields=["escuela"])

    def _tutor_data(self, dni='30000001', parentesco='madre'):
        return {
            'persona': {
                'nombre': 'Marta', 'apellido': 'Tutora', 'dni': dni,
                'tipo_dni': 'DNI', 'sexo': 'F', 'fecha_nacimiento': '1980-01-01',
            },
            'parentesco': parentesco,
        }

    def _crear_paciente(self, escuela, dni='70000101'):
        from apps.pacientes.services.alumnos import crear_alumno_escuela
        return crear_alumno_escuela(escuela.id, {
            'persona': {
                'nombre': 'Ana', 'apellido': 'Prueba', 'dni': dni,
                'tipo_dni': 'DNI', 'sexo': 'F', 'fecha_nacimiento': '2018-01-01',
            },
            'domicilio': {'localidad': 'Salta'},
            'edad': 8,
        })

    def test_crear_alumno_con_tutor_anidado(self):
        from apps.pacientes.services.alumnos import crear_alumno_escuela
        escuela = Escuela.objects.create(nombre='Escuela T')
        paciente = crear_alumno_escuela(escuela.id, {
            'persona': {
                'nombre': 'Ana', 'apellido': 'Prueba', 'dni': '70000102',
                'tipo_dni': 'DNI', 'sexo': 'F', 'fecha_nacimiento': '2018-01-01',
            },
            'domicilio': {}, 'edad': 8,
            'tutor': self._tutor_data(),
        })
        paciente.refresh_from_db()
        self.assertIsNotNone(paciente.tutor_id)
        self.assertEqual(paciente.tutor.persona.dni, '30000001')
        self.assertEqual(paciente.tutor.parentesco, 'madre')

    def test_crear_alumno_reutiliza_tutor_existente(self):
        from apps.pacientes.services.alumnos import crear_alumno_escuela
        escuela = Escuela.objects.create(nombre='Escuela T2')
        existente = Persona.objects.create(
            nombre='Marta', apellido='Tutora', dni='30000002',
            tipo_dni='DNI', sexo='F', fecha_nacimiento='1980-01-01',
        )
        tutor = Tutor.objects.create(persona=existente, parentesco='madre')
        paciente = crear_alumno_escuela(escuela.id, {
            'persona': {
                'nombre': 'Luis', 'apellido': 'Prueba', 'dni': '70000103',
                'tipo_dni': 'DNI', 'sexo': 'M', 'fecha_nacimiento': '2017-01-01',
            },
            'domicilio': {}, 'edad': 9,
            'tutor': self._tutor_data(dni='30000002'),
        })
        paciente.refresh_from_db()
        self.assertEqual(paciente.tutor_id, tutor.id)
        self.assertEqual(Persona.objects.filter(dni='30000002').count(), 1)

    def test_tutor_con_mismo_dni_que_alumno_da_error(self):
        from apps.pacientes.services.alumnos import (
            AlumnoEscuelaError, crear_alumno_escuela,
        )
        escuela = Escuela.objects.create(nombre='Escuela T3')
        with self.assertRaises(AlumnoEscuelaError):
            crear_alumno_escuela(escuela.id, {
                'persona': {
                    'nombre': 'Ana', 'apellido': 'Prueba', 'dni': '70000104',
                    'tipo_dni': 'DNI', 'sexo': 'F', 'fecha_nacimiento': '2018-01-01',
                },
                'domicilio': {}, 'edad': 8,
                'tutor': self._tutor_data(dni='70000104'),
            })

    def test_post_alumnos_con_tutor_devuelve_tutor(self):
        escuela = Escuela.objects.create(nombre='Escuela API')
        self._asignar_escuela('escuela@prosane.test', escuela)
        self._auth('escuela@prosane.test')
        res = self.client.post(reverse('escuela-alumnos-list-create'), {
            'persona': {
                'nombre': 'Ana', 'apellido': 'Prueba', 'dni': '70000105',
                'tipo_dni': 'DNI', 'sexo': 'F', 'fecha_nacimiento': '2018-01-01',
            },
            'domicilio': {}, 'edad': 8,
            'tutor': self._tutor_data(dni='30000005'),
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['tutor']['dni'], '30000005')
        self.assertEqual(res.data['tutor']['parentesco'], 'madre')

    def test_post_alumnos_sin_tutor_da_400(self):
        escuela = Escuela.objects.create(nombre='Escuela API 400')
        self._asignar_escuela('escuela@prosane.test', escuela)
        self._auth('escuela@prosane.test')
        res = self.client.post(reverse('escuela-alumnos-list-create'), {
            'persona': {
                'nombre': 'Ana', 'apellido': 'Prueba', 'dni': '70000106',
                'tipo_dni': 'DNI', 'sexo': 'F', 'fecha_nacimiento': '2018-01-01',
            },
            'domicilio': {}, 'edad': 8,
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tutor', res.data)

    def test_upsert_tutor_endpoint(self):
        escuela = Escuela.objects.create(nombre='Escuela UP')
        self._asignar_escuela('escuela@prosane.test', escuela)
        self._auth('escuela@prosane.test')
        paciente = self._crear_paciente(escuela)
        url = reverse('alumno-tutor', kwargs={'pk': paciente.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data['tutor'])
        res = self.client.post(url, self._tutor_data(dni='30000006'), format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['tutor']['dni'], '30000006')
        # Actualiza parentesco del mismo tutor.
        res = self.client.post(
            url, self._tutor_data(dni='30000006', parentesco='padre'), format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['tutor']['parentesco'], 'padre')
        self.assertEqual(Tutor.objects.filter(persona__dni='30000006').count(), 1)

    def test_upsert_tutor_otra_escuela_da_404(self):
        escuela = Escuela.objects.create(nombre='Escuela UP2')
        otra = Escuela.objects.create(nombre='Escuela Ajena')
        self._asignar_escuela('escuela@prosane.test', escuela)
        self._auth('escuela@prosane.test')
        paciente = self._crear_paciente(otra)
        url = reverse('alumno-tutor', kwargs={'pk': paciente.id})
        res = self.client.post(url, self._tutor_data(dni='30000007'), format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_upsert_tutor_sin_permiso_da_403(self):
        escuela = Escuela.objects.create(nombre='Escuela UP3')
        paciente = self._crear_paciente(escuela)
        self._auth('medico@prosane.test')
        url = reverse('alumno-tutor', kwargs={'pk': paciente.id})
        res = self.client.post(url, self._tutor_data(dni='30000008'), format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

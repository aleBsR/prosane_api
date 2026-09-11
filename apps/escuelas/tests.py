from django.test import TestCase
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.escuelas.models import Escuela, Curso
from apps.personas.models import Domicilio, Persona
from apps.usuarios.models import Rol
from apps.escuelas.serializers import (
    EscuelaSerializer, EscuelaListSerializer, CursoSerializer,
)

Usuario = get_user_model()


class EscuelaModelTest(TestCase):
    def test_crear_escuela_minimo(self):
        e = Escuela.objects.create(nombre='Escuela Test')
        self.assertEqual(e.nombre, 'Escuela Test')
        self.assertEqual(e.cue, None)
        self.assertEqual(e.ambito, '')
        self.assertEqual(e.telefono, '')
        self.assertTrue(e.activa)
        self.assertFalse(e.intercultural_bilingue)
        self.assertFalse(e.plurigrado_rural)
        self.assertIsNone(e.domicilio)

    def test_crear_escuela_completa(self):
        domicilio = Domicilio.objects.create(
            calle='Av. Siempre Viva', localidad='Salta'
        )
        e = Escuela.objects.create(
            nombre='Escuela Completa',
            cue='CUE12345',
            ambito='urbana',
            sector_gestion='estatal',
            modalidad_educativa='comun',
            intercultural_bilingue=True,
            plurigrado_rural=False,
            domicilio=domicilio,
            telefono='387-1234567',
            activa=True,
        )
        self.assertEqual(e.nombre, 'Escuela Completa')
        self.assertEqual(e.cue, 'CUE12345')
        self.assertEqual(e.domicilio, domicilio)

    def test_str_representation(self):
        e = Escuela.objects.create(nombre='Escuela 123')
        self.assertIn('Escuela 123', str(e))

    def test_str_con_cue(self):
        e = Escuela.objects.create(nombre='Escuela 123', cue='CUE001')
        self.assertIn('CUE001', str(e))

    def test_cue_unico(self):
        Escuela.objects.create(nombre='E1', cue='CUE-UNICO')
        with self.assertRaises(IntegrityError):
            Escuela.objects.create(nombre='E2', cue='CUE-UNICO')

    def test_cue_puede_ser_nulo(self):
        Escuela.objects.create(nombre='E1')
        Escuela.objects.create(nombre='E2')
        self.assertEqual(Escuela.objects.count(), 2)

    def test_activa_default_true(self):
        e = Escuela.objects.create(nombre='Test')
        self.assertTrue(e.activa)

    def test_ordering(self):
        Escuela.objects.create(nombre='Z')
        Escuela.objects.create(nombre='A')
        qs = Escuela.objects.all()
        self.assertEqual(qs[0].nombre, 'A')
        self.assertEqual(qs[1].nombre, 'Z')

    def test_domicilio_on_delete_set_null(self):
        domicilio = Domicilio.objects.create(calle='Calle 1')
        e = Escuela.objects.create(nombre='Test', domicilio=domicilio)
        domicilio.hard_delete()
        e.refresh_from_db()
        self.assertIsNone(e.domicilio)


class CursoModelTest(TestCase):
    def setUp(self):
        self.escuela = Escuela.objects.create(nombre='Escuela Test')

    def test_crear_curso_minimo(self):
        c = Curso.objects.create(escuela=self.escuela)
        self.assertEqual(c.nivel, '')
        self.assertEqual(c.sala_grado_anio, '')
        self.assertEqual(c.division, '')
        self.assertIsNone(c.ciclo_lectivo)

    def test_crear_curso_completo(self):
        c = Curso.objects.create(
            escuela=self.escuela,
            nivel='primario',
            sala_grado_anio='1°',
            division='A',
            ciclo_lectivo=2026,
        )
        self.assertEqual(c.nivel, 'primario')
        self.assertEqual(c.sala_grado_anio, '1°')
        self.assertEqual(c.division, 'A')
        self.assertEqual(c.ciclo_lectivo, 2026)

    def test_str_representation(self):
        c = Curso.objects.create(
            escuela=self.escuela, sala_grado_anio='1°', ciclo_lectivo=2026
        )
        self.assertIn('1°', str(c))

    def test_relacion_con_escuela(self):
        Curso.objects.create(escuela=self.escuela, sala_grado_anio='1°')
        Curso.objects.create(escuela=self.escuela, sala_grado_anio='2°')
        self.assertEqual(self.escuela.cursos.count(), 2)

    def test_curso_soft_delete(self):
        Curso.objects.create(escuela=self.escuela)
        self.escuela.delete()
        self.assertIsNotNone(self.escuela.deleted_at)

    def test_ciclo_lectivo_puede_ser_nulo(self):
        c = Curso.objects.create(escuela=self.escuela)
        self.assertIsNone(c.ciclo_lectivo)


class EscuelaSerializerTest(TestCase):
    def test_serialize_escuela_minima(self):
        e = Escuela.objects.create(nombre='Test')
        s = EscuelaSerializer(e)
        self.assertEqual(s.data['nombre'], 'Test')
        self.assertIsNone(s.data['cue'])
        self.assertIsNone(s.data['domicilio'])
        self.assertTrue(s.data['activa'])
        self.assertIn('id', s.data)

    def test_deserialize_crear_escuela(self):
        data = {'nombre': 'Nueva Escuela', 'cue': 'CUE999'}
        s = EscuelaSerializer(data=data)
        self.assertTrue(s.is_valid(), msg=s.errors)
        e = s.save()
        self.assertEqual(e.nombre, 'Nueva Escuela')
        self.assertEqual(e.cue, 'CUE999')

    def test_deserialize_con_domicilio_anidado(self):
        data = {
            'nombre': 'Con Domicilio',
            'domicilio': {
                'calle': 'Av. Principal',
                'localidad': 'Salta',
                'provincia': 'Salta',
            },
        }
        s = EscuelaSerializer(data=data)
        self.assertTrue(s.is_valid(), msg=s.errors)
        e = s.save()
        self.assertIsNotNone(e.domicilio)
        self.assertEqual(e.domicilio.calle, 'Av. Principal')
        self.assertEqual(e.domicilio.localidad, 'Salta')

    def test_nombre_requerido(self):
        s = EscuelaSerializer(data={'cue': 'CUE001'})
        self.assertFalse(s.is_valid())
        self.assertIn('nombre', s.errors)

    def test_cue_unico_validacion(self):
        Escuela.objects.create(nombre='E1', cue='CUE-UNICO')
        s = EscuelaSerializer(data={'nombre': 'E2', 'cue': 'CUE-UNICO'})
        self.assertFalse(s.is_valid())

    def test_update_escuela(self):
        e = Escuela.objects.create(nombre='Original')
        s = EscuelaSerializer(e, data={'nombre': 'Actualizado'}, partial=True)
        self.assertTrue(s.is_valid(), msg=s.errors)
        s.save()
        e.refresh_from_db()
        self.assertEqual(e.nombre, 'Actualizado')

    def test_id_read_only(self):
        s = EscuelaSerializer(data={'id': 'fake-id', 'nombre': 'Test'})
        self.assertTrue(s.is_valid(), msg=s.errors)
        self.assertNotIn('id', s.validated_data)


class EscuelaListSerializerTest(TestCase):
    def test_localidad_vacia_sin_domicilio(self):
        e = Escuela.objects.create(nombre='Test')
        s = EscuelaListSerializer(e)
        self.assertEqual(s.data['localidad'], '')

    def test_localidad_con_domicilio(self):
        dom = Domicilio.objects.create(localidad='Cafayate')
        e = Escuela.objects.create(nombre='Test', domicilio=dom)
        s = EscuelaListSerializer(e)
        self.assertEqual(s.data['localidad'], 'Cafayate')

    def test_campos_lista(self):
        e = Escuela.objects.create(nombre='Test')
        s = EscuelaListSerializer(e)
        expected = {
            'id', 'nombre', 'cue', 'ambito', 'activa', 'localidad',
            'usuarios_asociados', 'plurigrado_rural', 'perfil_completo',
        }
        self.assertEqual(set(s.data.keys()), expected)

    def test_usuarios_asociados(self):
        persona = Persona.objects.create(
            nombre='Ana', apellido='Gómez', dni='99999999',
            sexo='femenino', fecha_nacimiento='1990-01-01',
        )
        e = Escuela.objects.create(nombre='Test')
        user = Usuario.objects.create_user(
            email='escuela-test@example.com', password='test',
            persona=persona, escuela=e,
        )
        user.roles.add(Rol.objects.create(rol='escuela'))

        data = EscuelaListSerializer(e).data

        self.assertEqual(len(data['usuarios_asociados']), 1)
        self.assertEqual(data['usuarios_asociados'][0]['email'], user.email)
        self.assertEqual(data['usuarios_asociados'][0]['nombre'], 'Ana Gómez')


class CursoSerializerTest(TestCase):
    def setUp(self):
        self.escuela = Escuela.objects.create(nombre='Test')

    def test_serialize_curso(self):
        c = Curso.objects.create(
            escuela=self.escuela, sala_grado_anio='1°', ciclo_lectivo=2026
        )
        s = CursoSerializer(c)
        self.assertEqual(s.data['sala_grado_anio'], '1°')
        self.assertEqual(s.data['ciclo_lectivo'], 2026)
        self.assertEqual(s.data['escuela'], self.escuela.id)

    def test_deserialize_crear_curso(self):
        data = {
            'escuela': self.escuela.id,
            'sala_grado_anio': '2°',
            'division': 'B',
            'ciclo_lectivo': 2026,
        }
        s = CursoSerializer(data=data)
        self.assertTrue(s.is_valid(), msg=s.errors)
        c = s.save()
        self.assertEqual(c.sala_grado_anio, '2°')
        self.assertEqual(c.division, 'B')

    def test_escuela_no_requerida_en_data(self):
        s = CursoSerializer(data={'sala_grado_anio': '1°'})
        self.assertTrue(s.is_valid(), msg=s.errors)

    def test_update_curso(self):
        c = Curso.objects.create(
            escuela=self.escuela, sala_grado_anio='1°'
        )
        s = CursoSerializer(c, data={'sala_grado_anio': '2°'}, partial=True)
        self.assertTrue(s.is_valid(), msg=s.errors)
        s.save()
        c.refresh_from_db()
        self.assertEqual(c.sala_grado_anio, '2°')

    def test_curso_duplicado_no_valido(self):
        Curso.objects.create(
            escuela=self.escuela, sala_grado_anio='1°', division='A', ciclo_lectivo=2026,
        )
        s = CursoSerializer(
            data={'sala_grado_anio': '1°', 'division': 'A', 'ciclo_lectivo': 2026},
            context={'escuela': self.escuela},
        )
        self.assertFalse(s.is_valid())
        self.assertIn('non_field_errors', s.errors)

    def test_curso_duplicado_insensible_a_mayusculas_y_simbolo_grado(self):
        Curso.objects.create(
            escuela=self.escuela, sala_grado_anio='1°', division='A', ciclo_lectivo=2026,
        )
        s = CursoSerializer(
            data={'sala_grado_anio': '1º', 'division': 'a', 'ciclo_lectivo': 2026},
            context={'escuela': self.escuela},
        )
        self.assertFalse(s.is_valid())

    def test_curso_numero_solo_equivale_a_grado_con_simbolo(self):
        Curso.objects.create(
            escuela=self.escuela, sala_grado_anio='1°', division='A', ciclo_lectivo=2026,
        )
        s = CursoSerializer(
            data={'sala_grado_anio': '1', 'division': 'A', 'ciclo_lectivo': 2026},
            context={'escuela': self.escuela},
        )
        self.assertFalse(s.is_valid())

    def test_curso_mismo_grado_distinto_ciclo_es_valido(self):
        Curso.objects.create(
            escuela=self.escuela, sala_grado_anio='1°', division='A', ciclo_lectivo=2026,
        )
        s = CursoSerializer(
            data={'sala_grado_anio': '1°', 'division': 'A', 'ciclo_lectivo': 2027},
            context={'escuela': self.escuela},
        )
        self.assertTrue(s.is_valid(), msg=s.errors)


class EscuelaAPITest(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.core.management import call_command
        call_command("seed_permissions", verbosity=0)

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email='admin@test.com', password='test1234',
        )
        self.client.force_authenticate(user=self.admin)

    def test_listar_escuelas(self):
        Escuela.objects.create(nombre='Test Escuela')
        url = reverse('escuela-list-create')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_listar_escuelas_filtro_activa(self):
        Escuela.objects.create(nombre='Activa', activa=True)
        Escuela.objects.create(nombre='Inactiva', activa=False)
        url = reverse('escuela-list-create')
        res = self.client.get(f'{url}?activa=true')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['nombre'], 'Activa')

    def test_listar_escuelas_filtro_q(self):
        Escuela.objects.create(nombre='Manuel Belgrano', cue='CUE001')
        Escuela.objects.create(nombre='San Martin', cue='CUE002')
        url = reverse('escuela-list-create')
        res = self.client.get(f'{url}?q=belgrano')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['nombre'], 'Manuel Belgrano')

    def test_listar_escuelas_filtro_q_por_cue(self):
        Escuela.objects.create(nombre='Escuela A', cue='CUE-ABC')
        Escuela.objects.create(nombre='Escuela B', cue='CUE-XYZ')
        url = reverse('escuela-list-create')
        res = self.client.get(f'{url}?q=abc')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_crear_escuela(self):
        url = reverse('escuela-list-create')
        data = {'nombre': 'Escuela Nueva', 'cue': 'CUE001'}
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Escuela.objects.count(), 1)

    def test_crear_escuela_con_domicilio_anidado(self):
        url = reverse('escuela-list-create')
        data = {
            'nombre': 'Escuela con Domicilio',
            'domicilio': {
                'calle': 'Av. Principal 123',
                'localidad': 'Salta',
            },
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(res.data['domicilio'])

    def test_crear_escuela_sin_nombre_da_400(self):
        url = reverse('escuela-list-create')
        res = self.client.post(url, {'cue': 'CUE001'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_crear_escuela_modalidad_larga(self):
        # La app envía la modalidad como texto libre (ej. "Primaria común").
        url = reverse('escuela-list-create')
        res = self.client.post(
            url,
            {'nombre': 'Escuela Nueva', 'modalidad_educativa': 'Primaria común'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['modalidad_educativa'], 'Primaria común')

    def test_ver_detalle_escuela(self):
        escuela = Escuela.objects.create(nombre='Test Detalle')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['nombre'], 'Test Detalle')

    def test_actualizar_escuela_put(self):
        escuela = Escuela.objects.create(nombre='Original')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.put(url, {'nombre': 'Actualizado'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        escuela.refresh_from_db()
        self.assertEqual(escuela.nombre, 'Actualizado')

    def test_actualizar_escuela_patch(self):
        escuela = Escuela.objects.create(nombre='Original', cue='CUE001')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.patch(url, {'cue': 'CUE002'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        escuela.refresh_from_db()
        self.assertEqual(escuela.cue, 'CUE002')

    def test_soft_delete_escuela(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        escuela.refresh_from_db()
        self.assertFalse(escuela.activa)

    def test_eliminar_escuela_con_usuarios_da_409(self):
        from apps.usuarios.models import Rol
        escuela = Escuela.objects.create(nombre='Test')
        usuario = Usuario.objects.create_user(
            email='esc409@test.com', password='test1234', escuela=escuela,
        )
        usuario.roles.add(Rol.objects.create(rol='escuela-test-409'))
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        escuela.refresh_from_db()
        self.assertTrue(escuela.activa)
        usuario.refresh_from_db()
        self.assertEqual(usuario.escuela_id, escuela.id)

    def test_eliminar_escuela_con_operativos_da_409(self):
        from apps.operativos.models import Operativo
        escuela = Escuela.objects.create(nombre='Test')
        Operativo.objects.create(escuela=escuela, fecha='2026-09-01')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        escuela.refresh_from_db()
        self.assertTrue(escuela.activa)

    def test_mi_escuela_con_escuela_eliminada_da_404(self):
        escuela = Escuela.objects.create(nombre='Test')
        usuario = Usuario.objects.create_superuser(
            email='esc404@test.com', password='test1234', escuela=escuela,
        )
        escuela.delete()  # soft-delete: la FK queda colgada
        self.client.force_authenticate(
            user=Usuario.objects.get(pk=usuario.pk),
        )
        res = self.client.get(reverse('mi-escuela'))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_me_con_escuela_eliminada_no_explota(self):
        escuela = Escuela.objects.create(nombre='Test')
        usuario = Usuario.objects.create_superuser(
            email='escme@test.com', password='test1234', escuela=escuela,
        )
        escuela.delete()  # soft-delete: la FK queda colgada
        self.client.force_authenticate(
            user=Usuario.objects.get(pk=usuario.pk),
        )
        res = self.client.get(reverse('auth-me'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data['user']['escuela_id'])
        self.assertIsNone(res.data['user']['escuela_nombre'])

    def test_404_escuela_inexistente(self):
        url = reverse('escuela-detail', args=['00000000-0000-0000-0000-000000000000'])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_crear_curso(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        data = {'sala_grado_anio': '1°', 'division': 'A', 'ciclo_lectivo': 2026}
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(escuela.cursos.count(), 1)

    def test_listar_cursos(self):
        escuela = Escuela.objects.create(nombre='Test')
        Curso.objects.create(escuela=escuela, sala_grado_anio='1°')
        Curso.objects.create(escuela=escuela, sala_grado_anio='2°')
        url = reverse('curso-list-create', args=[escuela.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_crear_curso_sin_escuela_da_404(self):
        url = reverse('curso-list-create', args=['00000000-0000-0000-0000-000000000000'])
        data = {'sala_grado_anio': '1°'}
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_ver_detalle_curso(self):
        escuela = Escuela.objects.create(nombre='Test')
        curso = Curso.objects.create(escuela=escuela, sala_grado_anio='1°')
        url = reverse('curso-detail', args=[escuela.id, curso.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['sala_grado_anio'], '1°')

    def test_actualizar_curso_put(self):
        escuela = Escuela.objects.create(nombre='Test')
        curso = Curso.objects.create(escuela=escuela, sala_grado_anio='1°')
        url = reverse('curso-detail', args=[escuela.id, curso.id])
        res = self.client.put(url, {'sala_grado_anio': '2°', 'escuela': escuela.id}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        curso.refresh_from_db()
        self.assertEqual(curso.sala_grado_anio, '2°')

    def test_eliminar_curso(self):
        escuela = Escuela.objects.create(nombre='Test')
        curso = Curso.objects.create(escuela=escuela, sala_grado_anio='1°')
        url = reverse('curso-detail', args=[escuela.id, curso.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Curso.objects.count(), 0)

    def test_401_sin_autenticar(self):
        self.client.force_authenticate(user=None)
        url = reverse('escuela-list-create')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_403_sin_permiso_crear(self):
        user_sin_permiso = Usuario.objects.create_user(
            email='sinpermiso@test.com', password='test1234',
        )
        self.client.force_authenticate(user=user_sin_permiso)
        url = reverse('escuela-list-create')
        res = self.client.post(url, {'nombre': 'Test'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ── Filtros ──────────────────────────────────────────

    def test_listar_escuelas_filtro_activa_false(self):
        Escuela.objects.create(nombre='Activa', activa=True)
        Escuela.objects.create(nombre='Inactiva', activa=False)
        url = reverse('escuela-list-create')
        res = self.client.get(f'{url}?activa=false')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['nombre'], 'Inactiva')

    def test_listar_escuelas_filtro_activa_mayuscula(self):
        Escuela.objects.create(nombre='Activa', activa=True)
        url = reverse('escuela-list-create')
        res = self.client.get(f'{url}?activa=TRUE')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_listar_escuelas_filtro_activa_invalido(self):
        Escuela.objects.create(nombre='Activa', activa=True)
        url = reverse('escuela-list-create')
        res = self.client.get(f'{url}?activa=invalido')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_listar_escuelas_filtro_q_sin_resultados(self):
        Escuela.objects.create(nombre='Escuela A')
        url = reverse('escuela-list-create')
        res = self.client.get(f'{url}?q=inexistente')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_listar_escuelas_filtro_q_vacio(self):
        Escuela.objects.create(nombre='Escuela A')
        Escuela.objects.create(nombre='Escuela B')
        url = reverse('escuela-list-create')
        res = self.client.get(f'{url}?q=')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_listar_escuelas_orden_alfabetico(self):
        Escuela.objects.create(nombre='Z')
        Escuela.objects.create(nombre='M')
        Escuela.objects.create(nombre='A')
        url = reverse('escuela-list-create')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        nombres = [e['nombre'] for e in res.data]
        self.assertEqual(nombres, sorted(nombres))

    # ── 404 en mutaciones ────────────────────────────────

    def test_404_escuela_put_inexistente(self):
        url = reverse('escuela-detail', args=['00000000-0000-0000-0000-000000000000'])
        res = self.client.put(url, {'nombre': 'Nuevo'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_404_escuela_patch_inexistente(self):
        url = reverse('escuela-detail', args=['00000000-0000-0000-0000-000000000000'])
        res = self.client.patch(url, {'nombre': 'Nuevo'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_404_escuela_delete_inexistente(self):
        url = reverse('escuela-detail', args=['00000000-0000-0000-0000-000000000000'])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_404_curso_inexistente(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-detail', args=[escuela.id, '00000000-0000-0000-0000-000000000000'])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_404_curso_escuela_pk_incorrecta(self):
        escuela_a = Escuela.objects.create(nombre='Escuela A')
        escuela_b = Escuela.objects.create(nombre='Escuela B')
        curso = Curso.objects.create(escuela=escuela_a, sala_grado_anio='1°')
        url = reverse('curso-detail', args=[escuela_b.id, curso.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_listar_cursos_escuela_inexistente_retorna_vacio(self):
        url = reverse('curso-list-create', args=['00000000-0000-0000-0000-000000000000'])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    # ── CUE duplicado via API ────────────────────────────

    def test_crear_escuela_cue_duplicado_da_400(self):
        Escuela.objects.create(nombre='Existente', cue='CUE-UNICO')
        url = reverse('escuela-list-create')
        res = self.client.post(url, {'nombre': 'Nueva', 'cue': 'CUE-UNICO'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ── PUT con domicilio ────────────────────────────────

    def test_actualizar_escuela_put_crea_domicilio(self):
        escuela = Escuela.objects.create(nombre='Original')
        url = reverse('escuela-detail', args=[escuela.id])
        data = {
            'nombre': 'Actualizado',
            'domicilio': {'calle': 'Nueva Calle', 'localidad': 'Salta'},
        }
        res = self.client.put(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        escuela.refresh_from_db()
        self.assertIsNotNone(escuela.domicilio)
        self.assertEqual(escuela.domicilio.calle, 'Nueva Calle')

    def test_actualizar_escuela_put_actualiza_domicilio_existente(self):
        domicilio = Domicilio.objects.create(calle='Original', localidad='Salta')
        escuela = Escuela.objects.create(nombre='Original', domicilio=domicilio)
        url = reverse('escuela-detail', args=[escuela.id])
        data = {
            'nombre': 'Actualizado',
            'domicilio': {'calle': 'Modificada', 'localidad': 'Cafayate'},
        }
        res = self.client.put(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        domicilio.refresh_from_db()
        self.assertEqual(domicilio.calle, 'Modificada')
        self.assertEqual(domicilio.localidad, 'Cafayate')

    # ── Curso extra ──────────────────────────────────────

    def test_actualizar_curso_patch(self):
        escuela = Escuela.objects.create(nombre='Test')
        curso = Curso.objects.create(escuela=escuela, sala_grado_anio='1°', division='A')
        url = reverse('curso-detail', args=[escuela.id, curso.id])
        res = self.client.patch(url, {'division': 'B'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        curso.refresh_from_db()
        self.assertEqual(curso.division, 'B')
        self.assertEqual(curso.sala_grado_anio, '1°')

    def test_crear_curso_datos_invalidos_da_400(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        data = {'ciclo_lectivo': 'no-un-numero'}
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_eliminar_curso_soft_delete(self):
        escuela = Escuela.objects.create(nombre='Test')
        curso = Curso.objects.create(escuela=escuela, sala_grado_anio='1°')
        url = reverse('curso-detail', args=[escuela.id, curso.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Curso.objects.count(), 0)
        self.assertEqual(Curso.all_objects.count(), 1)
        self.assertIsNotNone(Curso.all_objects.get(pk=curso.pk).deleted_at)

    def test_crear_curso_duplicado_da_400(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        data = {'sala_grado_anio': '1°', 'division': 'A', 'ciclo_lectivo': 2026}
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_crear_curso_con_anio_duplica_contra_sin_anio(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        res = self.client.post(
            url, {'sala_grado_anio': '1°', 'division': 'A', 'ciclo_lectivo': 2026}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.client.post(
            url, {'sala_grado_anio': '1°', 'division': 'A'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_crear_curso_sin_anio_duplica_contra_con_anio(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        res = self.client.post(
            url, {'sala_grado_anio': '1°', 'division': 'A'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.client.post(
            url, {'sala_grado_anio': '1', 'division': 'a', 'ciclo_lectivo': 2026}, format= 'json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_crear_curso_duplicado_variante_minuscula_da_400(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        res = self.client.post(
            url, {'sala_grado_anio': '1°', 'division': 'A', 'ciclo_lectivo': 2026}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res = self.client.post(
            url, {'sala_grado_anio': '1º', 'division': 'a', 'ciclo_lectivo': 2026}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_actualizar_curso_a_duplicado_da_400(self):
        escuela = Escuela.objects.create(nombre='Test')
        Curso.objects.create(escuela=escuela, sala_grado_anio='1°', division='A', ciclo_lectivo=2026)
        curso2 = Curso.objects.create(escuela=escuela, sala_grado_anio='2°', division='A', ciclo_lectivo=2026)
        url = reverse('curso-detail', args=[escuela.id, curso2.id])
        res = self.client.patch(url, {'sala_grado_anio': '1°'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_crear_curso_tras_eliminar_permite_reutilizar(self):
        escuela = Escuela.objects.create(nombre='Test')
        curso = Curso.objects.create(escuela=escuela, sala_grado_anio='1°', division='A', ciclo_lectivo=2026)
        url_detalle = reverse('curso-detail', args=[escuela.id, curso.id])
        res = self.client.delete(url_detalle)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        url = reverse('curso-list-create', args=[escuela.id])
        res = self.client.post(
            url, {'sala_grado_anio': '1°', 'division': 'A', 'ciclo_lectivo': 2026}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)


class EscuelaAPIPermissionTest(APITestCase):
    fixtures = ["roles", "users"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.core.management import call_command
        call_command("seed_permissions", verbosity=0)

    def _auth(self, email):
        user = Usuario.objects.get(email=email)
        self.client.force_authenticate(user=user)
        return user

    # ── Ayudante (verEscuelas, crearEscuela, editarEscuela, eliminarEscuela) ──

    def test_ayudante_ver_escuelas(self):
        self._auth('ayudante@prosane.test')
        Escuela.objects.create(nombre='Test')
        url = reverse('escuela-list-create')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_ayudante_crear_escuela(self):
        self._auth('ayudante@prosane.test')
        url = reverse('escuela-list-create')
        res = self.client.post(url, {'nombre': 'Nueva'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_ayudante_editar_escuela(self):
        self._auth('ayudante@prosane.test')
        escuela = Escuela.objects.create(nombre='Original')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.put(url, {'nombre': 'Editado'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_ayudante_eliminar_escuela(self):
        self._auth('ayudante@prosane.test')
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_ayudante_crear_curso(self):
        self._auth('ayudante@prosane.test')
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        res = self.client.post(url, {'sala_grado_anio': '1°'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    # ── Tutor (solo verEscuelas) ──

    def test_tutor_ver_escuelas(self):
        self._auth('tutor@prosane.test')
        Escuela.objects.create(nombre='Test')
        url = reverse('escuela-list-create')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_tutor_ver_detalle_escuela(self):
        self._auth('tutor@prosane.test')
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_tutor_ver_cursos(self):
        self._auth('tutor@prosane.test')
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_tutor_no_crear_escuela(self):
        self._auth('tutor@prosane.test')
        url = reverse('escuela-list-create')
        res = self.client.post(url, {'nombre': 'Nueva'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_tutor_no_editar_escuela(self):
        self._auth('tutor@prosane.test')
        escuela = Escuela.objects.create(nombre='Original')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.put(url, {'nombre': 'Editado'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_tutor_no_eliminar_escuela(self):
        self._auth('tutor@prosane.test')
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_tutor_no_crear_curso(self):
        self._auth('tutor@prosane.test')
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        res = self.client.post(url, {'sala_grado_anio': '1°'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ── Médico (solo verOperativo, ningún permiso de escuela) ──

    def test_medico_no_ver_escuelas(self):
        self._auth('medico@prosane.test')
        url = reverse('escuela-list-create')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_medico_no_ver_detalle_escuela(self):
        self._auth('medico@prosane.test')
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class EscuelaPerfilCompletitudTest(APITestCase):
    """Alta mínima del admin + completado obligatorio por el usuario escuela."""

    fixtures = ["roles", "users"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.core.management import call_command
        call_command("seed_permissions", verbosity=0)

    def _auth(self, email):
        user = Usuario.objects.get(email=email)
        self.client.force_authenticate(user=user)
        return user

    def _asignar_escuela(self, email, escuela):
        user = Usuario.objects.get(email=email)
        user.escuela = escuela
        user.save(update_fields=["escuela"])

    def test_alta_minima_solo_nombre_y_perfil_incompleto(self):
        self._auth('ayudante@prosane.test')
        url = reverse('escuela-list-create')
        res = self.client.post(url, {'nombre': 'Nueva Mínima'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res.data['perfil_completo'])
        self.assertEqual(
            set(res.data['campos_faltantes']),
            {'CUE', 'Sector de gestión', 'Modalidad educativa', 'Teléfono', 'Localidad'},
        )

    def test_perfil_completo_con_todos_los_datos(self):
        self._auth('ayudante@prosane.test')
        url = reverse('escuela-list-create')
        res = self.client.post(url, {
            'nombre': 'Completa', 'cue': 'CUE1', 'sector_gestion': 'estatal',
            'modalidad_educativa': 'comun', 'telefono': '123',
            'domicilio': {'localidad': 'Salta'},
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['perfil_completo'])
        self.assertEqual(res.data['campos_faltantes'], [])

    def test_escuela_completa_sus_datos_via_mi_escuela(self):
        escuela = Escuela.objects.create(nombre='Incompleta')
        self._asignar_escuela('escuela@prosane.test', escuela)
        self._auth('escuela@prosane.test')
        url = reverse('mi-escuela')
        res = self.client.patch(url, {
            'cue': 'CUE9', 'sector_gestion': 'estatal',
            'modalidad_educativa': 'comun', 'telefono': '456',
            'domicilio': {'localidad': 'Orán'},
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['perfil_completo'])
        self.assertEqual(res.data['campos_faltantes'], [])

    def test_escuela_ve_su_perfil_incompleto_en_mi_escuela(self):
        escuela = Escuela.objects.create(nombre='Incompleta')
        self._asignar_escuela('escuela@prosane.test', escuela)
        self._auth('escuela@prosane.test')
        res = self.client.get(reverse('mi-escuela'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['perfil_completo'])
        self.assertIn('CUE', res.data['campos_faltantes'])

    def test_medico_no_puede_completar_mi_escuela(self):
        self._auth('medico@prosane.test')
        res = self.client.patch(reverse('mi-escuela'), {'telefono': '1'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_escuela_no_puede_editar_otra_escuela_por_detalle(self):
        otra = Escuela.objects.create(nombre='Ajena')
        self._auth('escuela@prosane.test')
        url = reverse('escuela-detail', args=[otra.id])
        res = self.client.patch(url, {'telefono': '1'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

from django.test import TestCase
from django.db import IntegrityError
from apps.escuelas.models import Escuela, Curso
from apps.personas.models import Domicilio
from apps.escuelas.serializers import (
    EscuelaSerializer, EscuelaListSerializer, CursoSerializer,
)


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
        expected = {'id', 'nombre', 'cue', 'ambito', 'activa', 'localidad'}
        self.assertEqual(set(s.data.keys()), expected)


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

    def test_escuela_requerida(self):
        s = CursoSerializer(data={'sala_grado_anio': '1°'})
        self.assertFalse(s.is_valid())
        self.assertIn('escuela', s.errors)

    def test_update_curso(self):
        c = Curso.objects.create(
            escuela=self.escuela, sala_grado_anio='1°'
        )
        s = CursoSerializer(c, data={'sala_grado_anio': '2°'}, partial=True)
        self.assertTrue(s.is_valid(), msg=s.errors)
        s.save()
        c.refresh_from_db()
        self.assertEqual(c.sala_grado_anio, '2°')

import io
import csv
from datetime import date

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from rest_framework.test import APITestCase

from apps.escuelas.models import Escuela, Curso
from apps.usuarios.models import Usuario
from apps.operativos.models import Operativo, OperativoProfesional, OperativoAlumno
from apps.operativos import services


# ──────────────────────────────────────────────
#  Helpers de test
# ──────────────────────────────────────────────
_user_counter = 0


def _create_ayudante(**kwargs):
    global _user_counter
    _user_counter += 1
    return Usuario.objects.create_user(
        email=kwargs.get('email', f'ayudante{_user_counter}@test.com'),
        password='pass1234',
    )


def _create_medico(**kwargs):
    global _user_counter
    _user_counter += 1
    return Usuario.objects.create_user(
        email=kwargs.get('email', f'medico{_user_counter}@test.com'),
        password='pass1234',
    )


def _create_odontologo(**kwargs):
    global _user_counter
    _user_counter += 1
    return Usuario.objects.create_user(
        email=kwargs.get('email', f'odontologo{_user_counter}@test.com'),
        password='pass1234',
    )


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
        user = _create_ayudante()
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
#  Tests de servicios
# ──────────────────────────────────────────────
class ServiciosTest(TestCase):
    def setUp(self):
        self.escuela = _create_escuela()
        self.ayudante = _create_ayudante()
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
        with self.assertRaises(ValueError):
            services.finalizar_operativo(op.id)

    def test_finalizar_ok(self):
        op = _create_operativo(self.escuela)
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        alumno = OperativoAlumno.objects.create(
            operativo=op, apellido='García', nombre='Juan', dni='12345678',
        )
        services.confirmar_operativo(op.id)
        alumno.estado = OperativoAlumno.EVALUADO
        alumno.save()
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
        alumno.estado = OperativoAlumno.EVALUADO
        alumno.save()
        services.finalizar_operativo(op.id)
        with self.assertRaises(ValueError):
            services.cancelar_operativo(op.id)

    def test_transicion_invalida(self):
        op = _create_operativo(self.escuela)
        with self.assertRaises(ValueError):
            services.transicionar_estado(op.id, Operativo.FINALIZADO)


# ──────────────────────────────────────────────
#  Tests de importar CSV
# ──────────────────────────────────────────────
class ImportarCSVTest(TestCase):
    def setUp(self):
        self.escuela = _create_escuela()
        self.operativo = _create_operativo(self.escuela)

    def _make_csv(self, rows):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'apellido', 'nombre', 'tipo_dni', 'dni', 'fecha_nacimiento', 'sexo',
        ])
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
        alumno.estado = OperativoAlumno.EVALUADO
        alumno.save()
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
        self.ayudante = _create_ayudante()
        self.medico = _create_medico()
        self.odontologo = _create_odontologo()
        self.otro_ayudante = _create_ayudante()

        # Assign roles
        from apps.usuarios.models import Rol
        self.rol_ayudante = Rol.objects.get(rol='ayudante')
        self.rol_medico = Rol.objects.get(rol='medico')
        self.rol_odontologo = Rol.objects.get(rol='odontologo')
        self.ayudante.roles.add(self.rol_ayudante)
        self.medico.roles.add(self.rol_medico)
        self.odontologo.roles.add(self.rol_odontologo)
        self.otro_ayudante.roles.add(self.rol_ayudante)

        self.client.force_authenticate(user=self.ayudante)

    def _create_operativo(self, **kwargs):
        defaults = {
            'escuela': self.escuela,
            'fecha': date(2026, 6, 20),
            'created_by': self.ayudante,
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

    def test_list_operativos_ayudante_solo_propios(self):
        self._create_operativo(created_by=self.ayudante)
        self._create_operativo(created_by=self.otro_ayudante)
        response = self.client.get('/api/v1/operativos/')
        self.assertEqual(len(response.data), 1)

    def test_list_operativos_medico_solo_asignados(self):
        op = self._create_operativo(created_by=self.otro_ayudante)
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
        alumno.estado = OperativoAlumno.EVALUADO
        alumno.save()
        response = self.client.post(f'/api/v1/operativos/{op.id}/finalizar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['estado'], Operativo.FINALIZADO)

    def test_finalizar_con_pendientes(self):
        op = self._create_operativo()
        services.asignar_profesional(op.id, self.medico.id, 'medico')
        self._create_alumno(op)
        services.confirmar_operativo(op.id)
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
        op = self._create_operativo()
        data = {'apellido': 'López', 'nombre': 'Carlos', 'dni': '34567890'}
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/alumnos/',
            data, format='json',
        )
        self.assertEqual(response.status_code, 201)

    def test_patch_alumno_estado(self):
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

    # ─── Importar CSV ───
    def test_importar_csv_api(self):
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
        op = self._create_operativo()
        response = self.client.post(
            f'/api/v1/operativos/{op.id}/alumnos/importar-csv/',
            {}, format='multipart',
        )
        self.assertEqual(response.status_code, 400)

    # ─── Permisos por rol ───
    def test_medico_ve_asignados(self):
        op = self._create_operativo(created_by=self.otro_ayudante)
        OperativoProfesional.objects.create(
            operativo=op, profesional=self.medico, rol_en_operativo='medico',
        )
        self.client.force_authenticate(user=self.medico)
        response = self.client.get(f'/api/v1/operativos/{op.id}/')
        self.assertEqual(response.status_code, 200)

    def test_medico_no_ve_no_asignados(self):
        self._create_operativo(created_by=self.otro_ayudante)
        self.client.force_authenticate(user=self.medico)
        response = self.client.get('/api/v1/operativos/')
        self.assertEqual(len(response.data), 0)

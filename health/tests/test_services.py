from datetime import datetime, timezone

from django.core.management import call_command
from django.test import TransactionTestCase, override_settings

from authentication.models import Usuarios
from core.models import Domicilio, Personas
from patients.models import Pacientes
from health.models import Apto
from health import services

NOW = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)


@override_settings(SEEDS_ENABLED=True)
class AptoServicesTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.medico = Usuarios.objects.get(email="medico@prosane.test")
        nna = Personas.objects.create(
            nombre="Niño", apellido="Prueba", dni="55000001",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="2014-01-01",
        )
        dom = Domicilio.objects.create(calle="Falsa", nro_calle="123", localidad="Salta")
        self.paciente = Pacientes.objects.create(persona=nna, domicilio=dom, edad=11)
        self._nna = nna
        self._dom = dom

    def tearDown(self):
        # Personas/Domicilio/Pacientes son managed=False: TransactionTestCase no
        # los trunca entre tests. Limpiamos a mano para evitar colisiones de UNIQUE.
        # Apto extiende BaseModel (soft-delete), hay que usar hard_delete para
        # que la fila desaparezca realmente antes de borrar el Paciente (PROTECT).
        Apto.all_objects.filter(paciente=self.paciente).hard_delete()
        Pacientes.objects.filter(id=self.paciente.id).delete()
        Personas.objects.filter(id=self._nna.id).delete()
        Domicilio.objects.filter(id=self._dom.id).delete()
        super().tearDown()

    def test_crear_apto_arranca_en_borrador(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        self.assertEqual(apto.estado, Apto.BORRADOR)
        self.assertIsNone(apto.firma_hash)

    def test_editar_borrador_actualiza_campos(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        services.editar_apto(apto, peso_kg="40.5", altura_cm="145.0", observaciones="ok")
        apto.refresh_from_db()
        self.assertEqual(str(apto.peso_kg), "40.50")
        self.assertEqual(apto.observaciones, "ok")

    def test_firmar_congela_snapshots_y_hash(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        services.editar_apto(apto, peso_kg="40.5", altura_cm="145.0", observaciones="ok")
        services.firmar_apto(apto, now=NOW)
        apto.refresh_from_db()
        self.assertEqual(apto.estado, Apto.FIRMADO)
        self.assertEqual(apto.nna_dni, "55000001")
        self.assertEqual(apto.nna_nombre_completo, "Niño Prueba")
        self.assertEqual(apto.nna_edad, 11)
        self.assertEqual(apto.profesional_nombre, "Mariana Médica")
        self.assertIsNotNone(apto.firma_hash)
        self.assertEqual(apto.fecha_emision.isoformat(), "2026-06-11")
        self.assertEqual(apto.validez_hasta.isoformat(), "2027-06-11")

    def test_editar_apto_firmado_falla(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        services.firmar_apto(apto, now=NOW)
        with self.assertRaises(services.AptoInmutableError):
            services.editar_apto(apto, observaciones="no se puede")

    def test_firmar_dos_veces_falla(self):
        apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
        services.firmar_apto(apto, now=NOW)
        with self.assertRaises(services.AptoInmutableError):
            services.firmar_apto(apto, now=NOW)

    def test_firmar_toma_la_matricula_del_profesional(self):
        from professionals.models import Profesionales
        Profesionales.objects.create(id_usuario=self.medico, matricula="MP-12345")
        try:
            apto = services.crear_apto(paciente=self.paciente, profesional=self.medico)
            services.firmar_apto(apto, now=NOW)
            apto.refresh_from_db()
            self.assertEqual(apto.matricula_firmante, "MP-12345")
        finally:
            Profesionales.objects.filter(id_usuario=self.medico).delete()

from datetime import datetime, timezone

from django.core.management import call_command
from django.test import TransactionTestCase, override_settings

from authentication.models import Usuarios
from core.models import Domicilio, Personas
from patients.models import Consentimiento, Pacientes
from patients import services

NOW = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)


@override_settings(SEEDS_ENABLED=True)
class CrearConsentimientoTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self._nna = Personas.objects.create(nombre="Niño", apellido="Prueba", dni="66000001",
                                            tipo_dni="DNI", sexo="M", fecha_nacimiento="2014-01-01")
        self._dom = Domicilio.objects.create(calle="Falsa", localidad="Salta")
        self.paciente = Pacientes.objects.create(persona=self._nna, domicilio=self._dom, edad=11)

    def tearDown(self):
        Consentimiento.all_objects.filter(paciente=self.paciente).hard_delete()
        Pacientes.objects.filter(id=self.paciente.id).delete()
        Personas.objects.filter(id=self._nna.id).delete()
        Domicilio.objects.filter(id=self._dom.id).delete()
        super().tearDown()

    def _crear(self):
        return services.crear_consentimiento(
            paciente=self.paciente, firma_tipo=Consentimiento.ADULTO_RESPONSABLE,
            adulto_nombre="Marta", adulto_apellido="Tutora",
            adulto_tipo_documento="DNI", adulto_dni="22333444", now=NOW,
        )

    def test_crea_firmado_con_hash_y_fecha(self):
        c = self._crear()
        self.assertEqual(c.firma_tipo, Consentimiento.ADULTO_RESPONSABLE)
        self.assertEqual(c.adulto_nombre, "Marta")
        self.assertTrue(c.firma_hash)
        self.assertEqual(c.fecha_firma, NOW)

    def test_hash_cambia_si_cambia_el_payload(self):
        c1 = self._crear()
        c2 = services.crear_consentimiento(
            paciente=self.paciente, firma_tipo=Consentimiento.NNA_MAYOR_13,
            adulto_nombre="Otro", adulto_apellido="Distinto",
            adulto_tipo_documento="DNI", adulto_dni="99888777", now=NOW,
        )
        self.assertNotEqual(c1.firma_hash, c2.firma_hash)

from django.test import TestCase
from django.utils import timezone

from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
from apps.tutores.models import Tutor
from apps.usuarios.models import Usuario


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
            adulto_nombre="Marta", adulto_apellido="Tutora",
            adulto_tipo_documento="DNI", adulto_dni="30000000",
        )
        p.refresh_from_db()
        self.assertTrue(p.consentimiento_aceptado)
        self.assertIsNotNone(p.fecha_consentimiento)
        self.assertEqual(p.adulto_dni, "30000000")

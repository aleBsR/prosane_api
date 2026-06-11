"""Tests de exposición de los serializers sensibles (Ley 25.326, datos de menores).

PersonasSerializer y DomicilioSerializer NO deben filtrar campos de más:
- el DNI nunca se devuelve en respuestas (write_only),
- el domicilio no expone metadata de auditoría.
El input de registro (con DNI) sigue funcionando.

Puros (sin DB): serializan instancias en memoria / validan data.
"""
from datetime import date

from django.test import SimpleTestCase

from core.models import Domicilio, Personas
from core.serializers import DomicilioSerializer, PersonasSerializer


def _persona():
    return Personas(
        id=1, nombre="Ana", apellido="García", dni="44555666",
        tipo_dni="DNI", sexo="F", fecha_nacimiento=date(2012, 5, 1),
    )


class PersonasSerializerTests(SimpleTestCase):
    def test_output_no_filtra_dni(self):
        data = PersonasSerializer(_persona()).data
        self.assertNotIn("dni", data)

    def test_output_expone_los_no_sensibles(self):
        data = PersonasSerializer(_persona()).data
        self.assertEqual(
            set(data.keys()),
            {"id", "nombre", "apellido", "tipo_dni", "sexo", "fecha_nacimiento"},
        )

    def test_dni_es_write_only(self):
        # write_only → se acepta al CREAR (input) pero no aparece en el output.
        dni = PersonasSerializer().fields["dni"]
        self.assertTrue(dni.write_only)
        self.assertFalse(dni.read_only)


class DomicilioSerializerTests(SimpleTestCase):
    def test_output_no_expone_auditoria_ni_campos_de_mas(self):
        d = Domicilio(calle="Falsa", nro_calle="123", localidad="Salta", provincia="Salta")
        data = DomicilioSerializer(d).data
        for f in ["created_at", "created_by", "updated_by", "deleted_at", "created_year"]:
            self.assertNotIn(f, data)
        self.assertIn("calle", data)
        self.assertIn("localidad", data)

from django.core.management import call_command
from django.test import TransactionTestCase

from authentication.models import Usuarios
from core.models import Personas


class CreateAdminCommandTests(TransactionTestCase):
    def tearDown(self):
        Usuarios.objects.filter(email="jefe@prosane.test").delete()
        Personas.objects.filter(dni="30111222").delete()

    def test_crea_superuser_con_persona(self):
        call_command(
            "create_admin",
            email="jefe@prosane.test", password="secreta-123",
            nombre="Jefa", apellido="Admin", dni="30111222",
            tipo_dni="DNI", sexo="F", fecha_nacimiento="1985-03-10",
            verbosity=0,
        )
        u = Usuarios.objects.get(email="jefe@prosane.test")
        self.assertTrue(u.is_superuser)
        self.assertTrue(u.check_password("secreta-123"))
        self.assertIsNotNone(u.persona)
        self.assertEqual(u.persona.nombre, "Jefa")
        self.assertEqual(u.persona.dni, "30111222")

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
from apps.tutores.models import Tutor
from apps.usuarios.models import Usuario


class RegisterTutorAPITest(APITestCase):
    def _payload(self, email="tutor@example.com", dni="11111111"):
        return {
            "email": email,
            "password": "test1234",
            "parentesco": "padre",
            "persona": {
                "nombre": "Juan",
                "apellido": "Pérez",
                "dni": dni,
                "tipo_dni": "DNI",
                "sexo": "M",
                "fecha_nacimiento": "1985-03-15",
            },
        }

    def test_registro_tutor_exitoso(self):
        url = reverse("register-tutor")
        res = self.client.post(url, self._payload(), format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["user"]["email"], "tutor@example.com")

        self.assertTrue(Usuario.objects.filter(email="tutor@example.com").exists())
        self.assertTrue(Tutor.objects.filter(usuario__email="tutor@example.com").exists())

        # Verifica que se le asignó el rol tutor
        user = Usuario.objects.get(email="tutor@example.com")
        self.assertTrue(user.roles.filter(rol="tutor").exists())

    def test_registro_tutor_email_duplicado(self):
        Usuario.objects.create_user(email="tutor@example.com", password="test1234")

        url = reverse("register-tutor")
        res = self.client.post(url, self._payload(), format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", res.data)

    def test_registro_tutor_dni_duplicado(self):
        Persona.objects.create(
            nombre="Otro",
            apellido="Otro",
            dni="11111111",
            tipo_dni="DNI",
            sexo="M",
            fecha_nacimiento="1980-01-01",
        )

        url = reverse("register-tutor")
        res = self.client.post(url, self._payload(), format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class TutorHijosAPITest(APITestCase):
    def setUp(self):
        self.persona_tutor = Persona.objects.create(
            nombre="Juan",
            apellido="Pérez",
            dni="22222222",
            tipo_dni="DNI",
            sexo="M",
            fecha_nacimiento="1985-03-15",
        )
        self.usuario_tutor = Usuario.objects.create_user(
            email="tutor@example.com",
            password="test1234",
            persona=self.persona_tutor,
        )
        self.tutor = Tutor.objects.create(
            persona=self.persona_tutor,
            usuario=self.usuario_tutor,
            parentesco="padre",
        )

    def _hijo_payload(self, dni="33333333"):
        return {
            "persona": {
                "nombre": "María",
                "apellido": "Pérez",
                "dni": dni,
                "tipo_dni": "DNI",
                "sexo": "F",
                "fecha_nacimiento": "2015-07-20",
            },
            "domicilio": {
                "calle": "Av. Siempre Viva",
                "localidad": "Springfield",
            },
            "edad": 10,
            "tiene_cud": "NO",
        }

    def test_crear_hijo_exitoso(self):
        self.client.force_authenticate(user=self.usuario_tutor)
        url = reverse("tutor-hijos", kwargs={"pk": str(self.tutor.id)})
        res = self.client.post(url, self._hijo_payload(), format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["persona"]["nombre"], "María")
        self.assertEqual(str(res.data["tutor"]), str(self.tutor.id))
        self.assertTrue(Paciente.objects.filter(tutor=self.tutor).exists())

    def test_crear_hijo_sin_autenticacion(self):
        url = reverse("tutor-hijos", kwargs={"pk": str(self.tutor.id)})
        res = self.client.post(url, self._hijo_payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_crear_hijo_otro_tutor_403(self):
        otra_persona = Persona.objects.create(
            nombre="Otro", apellido="Tutor", dni="44444444",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="1980-01-01",
        )
        otro_usuario = Usuario.objects.create_user(
            email="otro@example.com", password="test1234", persona=otra_persona
        )
        self.client.force_authenticate(user=otro_usuario)

        url = reverse("tutor-hijos", kwargs={"pk": str(self.tutor.id)})
        res = self.client.post(url, self._hijo_payload(), format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_listar_hijos(self):
        Paciente.objects.create(
            persona=Persona.objects.create(
                nombre="María", apellido="Pérez", dni="33333333",
                tipo_dni="DNI", sexo="F", fecha_nacimiento="2015-07-20",
            ),
            domicilio=Domicilio.objects.create(),
            tutor=self.tutor,
            edad=10,
        )

        self.client.force_authenticate(user=self.usuario_tutor)
        url = reverse("tutor-hijos", kwargs={"pk": str(self.tutor.id)})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_listar_hijos_otro_tutor_vacia(self):
        otra_persona = Persona.objects.create(
            nombre="Otro", apellido="Tutor", dni="55555555",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="1980-01-01",
        )
        otro_usuario = Usuario.objects.create_user(
            email="otro2@example.com", password="test1234", persona=otra_persona
        )
        self.client.force_authenticate(user=otro_usuario)

        url = reverse("tutor-hijos", kwargs={"pk": str(self.tutor.id)})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

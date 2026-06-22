from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.antecedentes.models import AntecedenteFamiliar, AntecedenteFamiliarTutor, AntecedentePersonal
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
            consentimiento_aceptado=True,
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

    def test_crear_hijo_con_telefonos(self):
        self.client.force_authenticate(user=self.usuario_tutor)
        payload = self._hijo_payload()
        payload["persona"]["telefono_fijo"] = "0387-4211111"
        payload["persona"]["celular"] = "+54 9 387 555 5555"

        url = reverse("tutor-hijos", kwargs={"pk": str(self.tutor.id)})
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["telefono_fijo"], "0387-4211111")
        self.assertEqual(res.data["celular"], "+54 9 387 555 5555")

        paciente = Paciente.objects.get(tutor=self.tutor)
        self.assertEqual(paciente.telefono_fijo, "0387-4211111")
        self.assertEqual(paciente.celular, "+54 9 387 555 5555")

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


class CrearHijoAgregadoTest(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(email="papa@example.com", password="test1234")
        persona = Persona.objects.create(
            nombre="Pedro", apellido="Papá", dni="40000000",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="1982-02-02",
        )
        self.tutor = Tutor.objects.create(
            persona=persona, usuario=self.usuario, parentesco="",
            consentimiento_aceptado=True,
        )
        self.client.force_authenticate(self.usuario)

    def _body(self, dni="60000000"):
        return {
            "persona": {
                "nombre": "Hija", "apellido": "Papá", "dni": dni,
                "tipo_dni": "DNI", "sexo": "F", "fecha_nacimiento": "2015-06-01",
            },
            "domicilio": {"calle": "Siempreviva", "nro_calle": "742", "provincia": "Salta"},
            "edad": 10, "tiene_cud": "NO",
            "tipo_cobertura": "obra_social", "nombre_cobertura": "OSDE",
            "parentesco": "padre",
            "antecedentes_personales": {"asma_espasmos": "SI", "diabetes": "NO"},
            "antecedentes_familiares": {
                "problemas_salud": "SI",
                "detalle_problema_salud": "Hipertensión materna",
                "familiar_con_muerte_subita": "NO",
            },
        }

    def test_crea_hijo_con_antecedentes_personales(self):
        url = reverse("tutor-hijos", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, self._body(), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        paciente_id = res.data["id"]
        self.assertEqual(AntecedentePersonal.objects.filter(paciente_id=paciente_id).count(), 1)
        self.assertEqual(AntecedenteFamiliar.objects.filter(paciente_id=paciente_id).count(), 0)
        self.assertEqual(res.data["adulto"]["dni"], "40000000")
        self.tutor.refresh_from_db()
        self.assertEqual(self.tutor.parentesco, "padre")

    def test_otro_tutor_no_puede_cargar_403(self):
        otro = Usuario.objects.create_user(email="otro@example.com", password="test1234")
        self.client.force_authenticate(otro)
        url = reverse("tutor-hijos", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, self._body(dni="61000000"), format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_dni_duplicado_no_crea_nada(self):
        Persona.objects.create(
            nombre="X", apellido="X", dni="62000000",
            tipo_dni="DNI", sexo="F", fecha_nacimiento="2010-01-01",
        )
        url = reverse("tutor-hijos", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, self._body(dni="62000000"), format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AntecedentePersonal.objects.count(), 0)
        self.assertEqual(Paciente.objects.count(), 0)


class TutorConsentimientoAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)

    def setUp(self):
        from apps.usuarios.models import Rol

        self.persona = Persona.objects.create(
            nombre="Juan", apellido="Pérez", dni="70000000",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="1985-03-15",
        )
        self.usuario = Usuario.objects.create_user(
            email="tutor@example.com", password="test1234", persona=self.persona
        )
        self.rol_tutor = Rol.objects.get(rol="tutor")
        self.usuario.roles.add(self.rol_tutor)
        self.tutor = Tutor.objects.create(
            persona=self.persona, usuario=self.usuario, parentesco="padre"
        )
        self.client.force_authenticate(user=self.usuario)

    def test_aceptar_consentimiento(self):
        url = reverse("tutor-consentimiento", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["consentimiento_aceptado"])
        self.assertIsNotNone(res.data["fecha_consentimiento"])
        self.tutor.refresh_from_db()
        self.assertTrue(self.tutor.consentimiento_aceptado)

    def test_aceptar_consentimiento_es_idempotente(self):
        url = reverse("tutor-consentimiento", kwargs={"pk": self.tutor.id})
        self.client.post(url, {}, format="json")
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["consentimiento_aceptado"])

    def test_otro_usuario_no_puede_aceptar_consentimiento(self):
        otro = Usuario.objects.create_user(email="otro@example.com", password="test1234")
        self.client.force_authenticate(user=otro)
        url = reverse("tutor-consentimiento", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class TutorAntecedentesFamiliaresAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)

    def setUp(self):
        from apps.usuarios.models import Rol

        self.persona = Persona.objects.create(
            nombre="Juan", apellido="Pérez", dni="71000000",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="1985-03-15",
        )
        self.usuario = Usuario.objects.create_user(
            email="tutor@example.com", password="test1234", persona=self.persona
        )
        self.rol_tutor = Rol.objects.get(rol="tutor")
        self.usuario.roles.add(self.rol_tutor)
        self.tutor = Tutor.objects.create(
            persona=self.persona, usuario=self.usuario, parentesco="padre"
        )
        self.client.force_authenticate(user=self.usuario)

    def test_crear_y_obtener_antecedentes(self):
        url = reverse("tutor-antecedentes-familiares", kwargs={"pk": self.tutor.id})
        payload = {
            "problema_salud_importante": "si",
            "problema_salud_cual": "Hipertensión",
            "muerte_subita_familiar": "no",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["problema_salud_importante"], "si")
        self.assertEqual(res.data["problema_salud_cual"], "Hipertensión")

        res_get = self.client.get(url)
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(res_get.data["muerte_subita_familiar"], "no")
        self.assertEqual(AntecedenteFamiliarTutor.objects.count(), 1)

    def test_otro_usuario_no_puede_ver_antecedentes(self):
        otro = Usuario.objects.create_user(email="otro@example.com", password="test1234")
        self.client.force_authenticate(user=otro)
        url = reverse("tutor-antecedentes-familiares", kwargs={"pk": self.tutor.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class HijoRequiereConsentimientoAPITest(APITestCase):
    def setUp(self):
        self.persona = Persona.objects.create(
            nombre="Juan", apellido="Pérez", dni="72000000",
            tipo_dni="DNI", sexo="M", fecha_nacimiento="1985-03-15",
        )
        self.usuario = Usuario.objects.create_user(
            email="tutor@example.com", password="test1234", persona=self.persona
        )
        self.tutor = Tutor.objects.create(
            persona=self.persona, usuario=self.usuario, parentesco="padre"
        )
        self.client.force_authenticate(user=self.usuario)

    def _body(self, dni="73000000"):
        return {
            "persona": {
                "nombre": "Hija", "apellido": "Pérez", "dni": dni,
                "tipo_dni": "DNI", "sexo": "F", "fecha_nacimiento": "2015-06-01",
            },
            "domicilio": {"calle": "Siempreviva"},
            "edad": 10,
        }

    def test_no_puede_crear_hijo_sin_consentimiento(self):
        url = reverse("tutor-hijos", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, self._body(), format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("consentimiento", res.data)
        self.assertEqual(Paciente.objects.count(), 0)

    def test_puede_crear_hijo_con_consentimiento(self):
        self.tutor.consentimiento_aceptado = True
        self.tutor.save()
        url = reverse("tutor-hijos", kwargs={"pk": self.tutor.id})
        res = self.client.post(url, self._body(), format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

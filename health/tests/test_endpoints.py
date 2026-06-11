from django.core.management import call_command
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from authentication.models import Usuarios
from core.models import Domicilio, Personas
from patients.models import Pacientes
from health.views import AptoListCreateView, AptoDetailView, AptoFirmarView


@override_settings(SEEDS_ENABLED=True)
class AptoEndpointsTests(TransactionTestCase):
    def setUp(self):
        call_command("reset_permissions_data", "--with-users", verbosity=0)
        self.factory = APIRequestFactory()
        self.medico = Usuarios.objects.get(email="medico@prosane.test")
        self.tutor = Usuarios.objects.get(email="tutor@prosane.test")
        self._nna = Personas.objects.create(nombre="Niño", apellido="Prueba", dni="55000002",
                                            tipo_dni="DNI", sexo="M", fecha_nacimiento="2014-01-01")
        self._dom = Domicilio.objects.create(calle="Falsa", localidad="Salta")
        self.paciente = Pacientes.objects.create(persona=self._nna, domicilio=self._dom, edad=11)

    def tearDown(self):
        from health.models import Apto
        Apto.all_objects.filter(paciente=self.paciente).hard_delete()
        Pacientes.objects.filter(id=self.paciente.id).delete()
        Personas.objects.filter(id=self._nna.id).delete()
        Domicilio.objects.filter(id=self._dom.id).delete()
        super().tearDown()

    def _crear(self, user):
        req = self.factory.post("/api/v1/aptos/", {"paciente": self.paciente.id}, format="json")
        force_authenticate(req, user=user)
        return AptoListCreateView.as_view()(req)

    def test_crear_apto_medico_201(self):
        resp = self._crear(self.medico)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["estado"], "borrador")
        self.assertNotIn("nna_dni", resp.data or {})

    def test_crear_apto_tutor_403(self):
        self.assertEqual(self._crear(self.tutor).status_code, 403)

    def test_firmar_y_luego_no_se_puede_editar(self):
        apto_id = self._crear(self.medico).data["id"]
        req = self.factory.post(f"/api/v1/aptos/{apto_id}/firmar/")
        force_authenticate(req, user=self.medico)
        self.assertEqual(AptoFirmarView.as_view()(req, pk=apto_id).status_code, 200)
        req2 = self.factory.patch(f"/api/v1/aptos/{apto_id}/", {"observaciones": "x"}, format="json")
        force_authenticate(req2, user=self.medico)
        self.assertEqual(AptoDetailView.as_view()(req2, pk=apto_id).status_code, 409)

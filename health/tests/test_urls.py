"""Las rutas de aptos resuelven con el pk UUID (Apto hereda BaseModel → id UUID).

Regresión: los tests de endpoints llaman las vistas directamente (pasan pk a mano),
así que NO ejercitan el converter de la URL. El smoke en vivo detectó que `<int:pk>`
daba 404 con un id UUID. Este test cubre el routing real.
"""
import uuid

from django.test import SimpleTestCase
from django.urls import resolve

from health.views import AptoDetailView, AptoFirmarView


class AptoUrlsTests(SimpleTestCase):
    def test_detail_resuelve_con_uuid(self):
        u = str(uuid.uuid4())
        self.assertEqual(resolve(f"/api/v1/aptos/{u}/").func.view_class, AptoDetailView)

    def test_firmar_resuelve_con_uuid(self):
        u = str(uuid.uuid4())
        self.assertEqual(resolve(f"/api/v1/aptos/{u}/firmar/").func.view_class, AptoFirmarView)

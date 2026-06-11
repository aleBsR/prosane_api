import uuid

from django.test import SimpleTestCase
from django.urls import resolve

from patients.views import ConsentimientoDetailView


class ConsentimientoUrlsTests(SimpleTestCase):
    def test_detail_resuelve_con_uuid(self):
        u = str(uuid.uuid4())
        self.assertEqual(
            resolve(f"/api/v1/consentimientos/{u}/").func.view_class, ConsentimientoDetailView
        )

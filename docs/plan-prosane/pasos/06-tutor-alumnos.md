# Paso 06: Alumnos del tutor

## Objetivo

El tutor puede agregar alumnos (Paciente) y listar sus alumnos registrados.

## 1. Views

**Agregar en `apps/tutores/views.py`:**
```python
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.personas.models import Persona
from apps.pacientes.models import Paciente
from .models import Tutor


class TutorAlumnosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tutor_pk):
        tutor = get_object_or_404(Tutor, pk=tutor_pk, usuario=request.user)
        alumnos = tutor.paciente_set.all()
        data = [{
            'id': str(a.id),
            'nombre': a.persona.nombre,
            'apellido': a.persona.apellido,
            'dni': a.persona.dni,
            'fecha_nacimiento': a.persona.fecha_nacimiento,
            'sexo': a.persona.sexo,
        } for a in alumnos]
        return Response(data)

    def post(self, request, tutor_pk):
        tutor = get_object_or_404(Tutor, pk=tutor_pk, usuario=request.user)
        data = request.data

        persona = Persona.objects.create(
            nombre=data.get('nombre'),
            apellido=data.get('apellido'),
            dni=data.get('dni'),
            tipo_dni=data.get('tipo_dni', 'DNI'),
            sexo=data.get('sexo', ''),
            fecha_nacimiento=data.get('fecha_nacimiento'),
        )

        paciente = Paciente.objects.create(
            persona=persona,
            tutor=tutor,
            edad=data.get('edad', 0),
            tipo_cobertura=data.get('tipo_cobertura', ''),
            nombre_cobertura=data.get('nombre_cobertura', ''),
        )

        return Response({
            'id': str(paciente.id),
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'dni': persona.dni,
        }, status=status.HTTP_201_CREATED)
```

## 2. URLs

**Archivo:** `apps/tutores/urls.py` (agregar)
```python
urlpatterns = [
    path('auth/register/tutor/', views.RegisterTutorView.as_view(), name='register-tutor'),
    path('tutores/<uuid:tutor_pk>/alumnos/', views.TutorAlumnosView.as_view(), name='tutor-alumnos'),
]
```

## 3. Tests

**Agregar en `apps/tutores/tests.py`:**
```python
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.tutores.models import Tutor
from apps.personas.models import Persona

Usuario = get_user_model()


class TutorAlumnosTest(APITestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            email='tutor@test.com', password='test1234',
        )
        persona = Persona.objects.create(nombre='Tutor', apellido='Test')
        self.tutor = Tutor.objects.create(
            persona=persona, usuario=self.user, parentesco='padre',
        )
        self.client.force_authenticate(user=self.user)

    def test_crear_alumno(self):
        url = reverse('tutor-alumnos', args=[self.tutor.id])
        data = {'nombre': 'Hijo', 'apellido': 'Test', 'dni': '12345678'}
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_listar_alumnos(self):
        url = reverse('tutor-alumnos', args=[self.tutor.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
```

```bash
python manage.py test apps.tutores.tests
```

## Criterio de aceptación

- `POST /tutores/{id}/alumnos/` → 201, crea Persona + Paciente vinculado al tutor
- `GET /tutores/{id}/alumnos/` → 200, lista alumnos del tutor autenticado
- Solo el dueño del tutor puede ver/crear alumnos
- Tests pasan

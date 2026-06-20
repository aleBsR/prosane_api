# Paso 05: Registro de tutor

## Objetivo

Endpoint público que crea Persona + Usuario + Tutor en una sola llamada y devuelve JWT.

## 1. Views

**Archivo:** `apps/tutores/views.py`
```python
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction

from apps.personas.models import Persona
from apps.usuarios.models import Usuario
from .models import Tutor


class RegisterTutorView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        data = request.data

        # Crear Persona
        persona = Persona.objects.create(
            nombre=data.get('nombre'),
            apellido=data.get('apellido'),
            dni=data.get('dni'),
            tipo_dni=data.get('tipo_dni', 'DNI'),
            sexo=data.get('sexo', ''),
            fecha_nacimiento=data.get('fecha_nacimiento'),
        )

        # Crear Usuario
        usuario = Usuario.objects.create_user(
            email=data['email'],
            password=data['password'],
        )
        usuario.persona = persona
        usuario.save(update_fields=['persona'])

        # Crear Tutor
        tutor = Tutor.objects.create(
            persona=persona,
            usuario=usuario,
            parentesco=data.get('parentesco', ''),
        )

        # Generar JWT
        refresh = RefreshToken.for_user(usuario)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(usuario.id),
                'email': usuario.email,
                'nombre': persona.nombre,
                'apellido': persona.apellido,
            },
        }, status=status.HTTP_201_CREATED)
```

## 2. URLs

**Archivo:** `apps/tutores/urls.py`
```python
from django.urls import path
from . import views

urlpatterns = [
    path('auth/register/tutor/', views.RegisterTutorView.as_view(), name='register-tutor'),
]
```

**Archivo:** `config/urls.py` (agregar)
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.usuarios.urls')),
    path('api/v1/', include('apps.tutores.urls')),
]
```

## 3. Tests

**Archivo:** `apps/tutores/tests.py`
```python
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse


class RegisterTutorTest(APITestCase):
    def test_register_tutor_success(self):
        url = reverse('register-tutor')
        data = {
            'nombre': 'Juan', 'apellido': 'Pérez',
            'dni': '12345678', 'email': 'juan@test.com',
            'password': 'test1234', 'parentesco': 'padre',
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)
        self.assertEqual(res.data['user']['email'], 'juan@test.com')
```

```bash
python manage.py test apps.tutores.tests
```

## Criterio de aceptación

- `POST /api/v1/auth/register/tutor/` → 201 con JWT + datos del usuario
- Crea 1 Persona + 1 Usuario + 1 Tutor en una transacción
- El usuario puede hacer login inmediatamente con el email registrado
- Tests pasan

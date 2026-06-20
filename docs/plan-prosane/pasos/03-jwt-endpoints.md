# Paso 03: Endpoints JWT (login, refresh, logout, me)

## Objetivo

Exponer endpoints de autenticación usando simplejwt + APIView. El endpoint `/me` incluye `effective_actions` para que el frontend conozca los permisos del usuario.

## 1. Views

**Archivo:** `apps/usuarios/views.py`
```python
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import UserSerializer
from .action_resolution import effective_actions


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        data = serializer.data
        data['roles'] = list(user.roles.values('rol', 'id'))
        data['actions'] = effective_actions(user)
        return Response(data)
```

## 2. URLs

**Archivo:** `apps/usuarios/urls.py`
```python
from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', views.RefreshView.as_view(), name='auth-refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', views.MeView.as_view(), name='auth-me'),
]
```

**Archivo:** `config/urls.py`
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.usuarios.urls')),
]
```

## 3. Tests

**Agregar en `apps/usuarios/tests.py`:**
```python
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.usuarios.models.action import Action, RoleAction
from apps.usuarios.models import Rol

Usuario = get_user_model()


class AuthAPITest(APITestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            email='test@test.com', password='test1234',
        )

    def test_login_success(self):
        url = reverse('auth-login')
        res = self.client.post(url, {
            'email': 'test@test.com', 'password': 'test1234',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_login_invalid(self):
        url = reverse('auth-login')
        res = self.client.post(url, {
            'email': 'test@test.com', 'password': 'wrong',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('auth-me')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], 'test@test.com')

    def test_me_includes_actions(self):
        action = Action.objects.create(name='test', label='Test')
        rol = Rol.objects.create(rol='test')
        RoleAction.objects.create(role=rol, action=action)
        self.user.roles.add(rol)
        self.client.force_authenticate(user=self.user)
        url = reverse('auth-me')
        res = self.client.get(url)
        self.assertIn('actions', res.data)
        self.assertEqual(len(res.data['actions']), 1)

    def test_me_unauthenticated(self):
        url = reverse('auth-me')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('auth-logout')
        res = self.client.post(url, {'refresh': 'dummy'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
```

```bash
python manage.py test apps.usuarios.tests.AuthAPITest
```

## Criterio de aceptación

- `POST /api/v1/auth/login/` → 200 con access+refresh, o 401
- `POST /api/v1/auth/refresh/` → 200 con nuevo access
- `POST /api/v1/auth/logout/` → 204
- `GET /api/v1/auth/me/` → 200 con datos + roles + actions, o 401
- `/me` incluye `effective_actions` para cache del frontend
- Tests pasan

# Paso 09: Endpoints CRUD de Escuela y Curso

## Objetivo

Exponer Escuela y Curso vía API REST con permisos.

## 1. Views

**Archivo:** `apps/escuelas/views.py`
```python
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import models

from apps.usuarios.permissions import require_action
from apps.personas.models import Domicilio
from .models import Escuela, Curso
from .serializers import EscuelaSerializer, EscuelaListSerializer, CursoSerializer


class EscuelaListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verEscuelas')()]
        return [require_action('crearEscuela')()]

    def get(self, request):
        qs = Escuela.objects.all()
        activa = request.query_params.get('activa')
        q = request.query_params.get('q')
        if activa is not None:
            qs = qs.filter(activa=(activa.lower() == 'true'))
        if q:
            qs = qs.filter(
                models.Q(nombre__icontains=q) | models.Q(cue__icontains=q),
            )
        qs = qs.order_by('nombre')
        serializer = EscuelaListSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = EscuelaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EscuelaDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verEscuelas')()]
        if self.request.method in ('PUT', 'PATCH'):
            return [require_action('editarEscuela')()]
        if self.request.method == 'DELETE':
            return [require_action('eliminarEscuela')()]
        return []

    def get_object(self, pk):
        return get_object_or_404(Escuela, pk=pk)

    def get(self, request, pk):
        escuela = self.get_object(pk)
        serializer = EscuelaSerializer(escuela)
        return Response(serializer.data)

    def put(self, request, pk):
        escuela = self.get_object(pk)
        serializer = EscuelaSerializer(escuela, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        escuela = self.get_object(pk)
        serializer = EscuelaSerializer(escuela, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        escuela = self.get_object(pk)
        escuela.activa = False
        escuela.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CursoListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verEscuelas')()]
        return [require_action('editarEscuela')()]

    def get(self, request, escuela_pk):
        cursos = Curso.objects.filter(escuela_id=escuela_pk)
        serializer = CursoSerializer(cursos, many=True)
        return Response(serializer.data)

    def post(self, request, escuela_pk):
        get_object_or_404(Escuela, pk=escuela_pk)
        serializer = CursoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(escuela_id=escuela_pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CursoDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verEscuelas')()]
        return [require_action('editarEscuela')()]

    def get(self, request, escuela_pk, pk):
        curso = get_object_or_404(Curso, escuela_id=escuela_pk, pk=pk)
        serializer = CursoSerializer(curso)
        return Response(serializer.data)

    def put(self, request, escuela_pk, pk):
        curso = get_object_or_404(Curso, escuela_id=escuela_pk, pk=pk)
        serializer = CursoSerializer(curso, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, escuela_pk, pk):
        curso = get_object_or_404(Curso, escuela_id=escuela_pk, pk=pk)
        serializer = CursoSerializer(curso, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, escuela_pk, pk):
        curso = get_object_or_404(Curso, escuela_id=escuela_pk, pk=pk)
        curso.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

## 2. URLs

**Archivo:** `apps/escuelas/urls.py`
```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.EscuelaListCreateView.as_view(), name='escuela-list-create'),
    path('<uuid:pk>/', views.EscuelaDetailView.as_view(), name='escuela-detail'),
    path('<uuid:escuela_pk>/cursos/', views.CursoListCreateView.as_view(), name='curso-list-create'),
    path('<uuid:escuela_pk>/cursos/<uuid:pk>/', views.CursoDetailView.as_view(), name='curso-detail'),
]
```

**Archivo:** `config/urls.py`
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.usuarios.urls')),      # auth
    path('api/v1/escuelas/', include('apps.escuelas.urls')),
]
```

## 3. Tests

**Archivo:** `apps/escuelas/tests.py`
```python
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.usuarios.models import Rol
from apps.escuelas.models import Escuela

Usuario = get_user_model()


class EscuelaAPITest(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email='admin@test.com', password='test1234',
        )
        self.client.force_authenticate(user=self.admin)

    def test_listar_escuelas(self):
        Escuela.objects.create(nombre='Test Escuela')
        url = reverse('escuela-list-create')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_crear_escuela(self):
        url = reverse('escuela-list-create')
        data = {'nombre': 'Escuela Nueva', 'cue': 'CUE001'}
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Escuela.objects.count(), 1)

    def test_crear_curso(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        data = {'sala_grado_anio': '1°', 'ciclo_lectivo': 2026}
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(escuela.cursos.count(), 1)

    def test_listar_cursos(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('curso-list-create', args=[escuela.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_soft_delete_escuela(self):
        escuela = Escuela.objects.create(nombre='Test')
        url = reverse('escuela-detail', args=[escuela.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        escuela.refresh_from_db()
        self.assertFalse(escuela.activa)
```

```bash
python manage.py test apps.escuelas.tests
```

## Criterio de aceptación

- `GET /api/v1/escuelas/` → lista (200) con filtros `?activa=` y `?q=`
- `POST /api/v1/escuelas/` → crea (201)
- `GET /api/v1/escuelas/{id}/` → detalle (200)
- `PUT/PATCH /api/v1/escuelas/{id}/` → actualiza (200)
- `DELETE /api/v1/escuelas/{id}/` → soft delete (204, activa=false)
- `GET /api/v1/escuelas/{id}/cursos/` → lista cursos (200)
- `POST /api/v1/escuelas/{id}/cursos/` → crea curso (201)
- Todos los tests pasan

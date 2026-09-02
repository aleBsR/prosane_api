from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import models

from apps.usuarios.permissions import require_action, require_any_action
from .models import Escuela, Curso
from .serializers import EscuelaSerializer, EscuelaListSerializer, CursoSerializer


class EscuelaListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verEscuelas')()]
        return [require_action('crearEscuela')()]

    def get(self, request):
        qs = Escuela.objects.prefetch_related('usuarios_escuela__persona', 'usuarios_escuela__roles').all()
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
        return get_object_or_404(
            Escuela.objects.prefetch_related('usuarios_escuela__persona', 'usuarios_escuela__roles'),
            pk=pk,
        )

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


class MiEscuelaView(APIView):
    permission_classes = [require_action('verMiEscuela')]

    def get(self, request):
        escuela = getattr(request.user, 'escuela', None)
        if escuela is None:
            return Response(
                {'detail': 'El usuario no tiene una escuela asignada.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = EscuelaSerializer(escuela).data
        cursos = Curso.objects.filter(escuela=escuela).order_by(
            'sala_grado_anio', 'division', 'ciclo_lectivo',
        )
        data['cursos'] = CursoSerializer(cursos, many=True).data
        return Response(data)


class CursoListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_any_action('verEscuelas', 'verMiEscuela')()]
        return [require_any_action('editarEscuela', 'gestionarCursos')()]

    def _escuela(self, request, escuela_pk):
        if 'escuela' in request.user.roles.values_list('rol', flat=True):
            if request.user.escuela_id != escuela_pk:
                return None
        return get_object_or_404(Escuela, pk=escuela_pk)

    def get(self, request, escuela_pk):
        es_escuela = request.user.roles.filter(rol='escuela').exists()
        if es_escuela and request.user.escuela_id != escuela_pk:
            return Response({'detail': 'No tenés acceso a esta escuela.'}, status=status.HTTP_404_NOT_FOUND)
        cursos = Curso.objects.filter(escuela_id=escuela_pk)
        serializer = CursoSerializer(cursos, many=True)
        return Response(serializer.data)

    def post(self, request, escuela_pk):
        escuela = self._escuela(request, escuela_pk)
        if escuela is None:
            return Response({'detail': 'No tenés acceso a esta escuela.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CursoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(escuela=escuela)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CursoDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_any_action('verEscuelas', 'verMiEscuela')()]
        return [require_any_action('editarEscuela', 'gestionarCursos')()]

    def _curso(self, request, escuela_pk, pk):
        if 'escuela' in request.user.roles.values_list('rol', flat=True):
            if request.user.escuela_id != escuela_pk:
                return None
        return get_object_or_404(Curso, escuela_id=escuela_pk, pk=pk)

    def get(self, request, escuela_pk, pk):
        curso = self._curso(request, escuela_pk, pk)
        if curso is None:
            return Response({'detail': 'No tenés acceso a esta escuela.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CursoSerializer(curso)
        return Response(serializer.data)

    def put(self, request, escuela_pk, pk):
        curso = self._curso(request, escuela_pk, pk)
        if curso is None:
            return Response({'detail': 'No tenés acceso a esta escuela.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CursoSerializer(curso, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, escuela_pk, pk):
        curso = self._curso(request, escuela_pk, pk)
        if curso is None:
            return Response({'detail': 'No tenés acceso a esta escuela.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CursoSerializer(curso, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, escuela_pk, pk):
        curso = self._curso(request, escuela_pk, pk)
        if curso is None:
            return Response({'detail': 'No tenés acceso a esta escuela.'}, status=status.HTTP_404_NOT_FOUND)
        curso.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

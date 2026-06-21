from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import models

from apps.usuarios.permissions import require_action
from .models import Operativo, OperativoProfesional, OperativoAlumno
from .serializers import (
    OperativoListSerializer,
    OperativoDetailSerializer,
    OperativoProfesionalSerializer,
    OperativoAlumnoSerializer,
    OperativoAlumnoEstadoSerializer,
)
from . import services


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────
def _filter_operativos_qs(request):
    """Filtra operativos según el rol del usuario.

    - ayudante: solo sus propios operativos (created_by)
    - medico/odontologo: solo operativos donde está asignado
    - superuser: todos
    """
    user = request.user
    if user.is_superuser:
        return Operativo.objects.all()

    roles = list(user.roles.values_list('rol', flat=True))
    if 'ayudante' in roles:
        return Operativo.objects.filter(created_by=user)
    if any(r in ('medico', 'odontologo') for r in roles):
        return Operativo.objects.filter(
            profesionales_asignados__profesional=user,
        )
    return Operativo.objects.none()


# ──────────────────────────────────────────────
#  Operativos CRUD
# ──────────────────────────────────────────────
class OperativoListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verOperativo')()]
        return [require_action('crearOperativo')()]

    def get(self, request):
        qs = _filter_operativos_qs(request)
        escuela_id = request.query_params.get('escuela_id')
        fecha = request.query_params.get('fecha')
        estado = request.query_params.get('estado')
        if escuela_id:
            qs = qs.filter(escuela_id=escuela_id)
        if fecha:
            qs = qs.filter(fecha=fecha)
        if estado:
            qs = qs.filter(estado=estado)
        qs = qs.order_by('-fecha', '-created_at')
        serializer = OperativoListSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OperativoDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OperativoDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verOperativo')()]
        if self.request.method in ('PUT', 'PATCH'):
            return [require_action('editarOperativo')()]
        if self.request.method == 'DELETE':
            return [require_action('cancelarOperativo')()]
        return []

    def get_object(self, pk):
        return get_object_or_404(Operativo, pk=pk)

    def get(self, request, pk):
        operativo = self.get_object(pk)
        serializer = OperativoDetailSerializer(operativo)
        return Response(serializer.data)

    def put(self, request, pk):
        operativo = self.get_object(pk)
        serializer = OperativoDetailSerializer(operativo, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        operativo = self.get_object(pk)
        serializer = OperativoDetailSerializer(operativo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        operativo = self.get_object(pk)
        services.cancelar_operativo(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────
#  Acciones de estado
# ──────────────────────────────────────────────
class OperativoConfirmarView(APIView):
    permission_classes = [require_action('confirmarOperativo')]

    def post(self, request, pk):
        try:
            op = services.confirmar_operativo(pk)
            serializer = OperativoDetailSerializer(op)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


class OperativoFinalizarView(APIView):
    permission_classes = [require_action('finalizarOperativo')]

    def post(self, request, pk):
        try:
            op = services.finalizar_operativo(pk)
            serializer = OperativoDetailSerializer(op)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


class OperativoCancelarView(APIView):
    permission_classes = [require_action('cancelarOperativo')]

    def post(self, request, pk):
        try:
            op = services.cancelar_operativo(pk)
            serializer = OperativoDetailSerializer(op)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


# ──────────────────────────────────────────────
#  Profesionales
# ──────────────────────────────────────────────
class OperativoProfesionalListView(APIView):
    permission_classes = [require_action('verOperativo')]

    def get(self, request, pk):
        qs = OperativoProfesional.objects.filter(operativo_id=pk)
        serializer = OperativoProfesionalSerializer(qs, many=True)
        return Response(serializer.data)


class OperativoProfesionalAssignView(APIView):
    permission_classes = [require_action('gestionarProfesionalesEnOperativo')]

    def post(self, request, pk):
        profesional_id = request.data.get('profesional')
        rol = request.data.get('rol_en_operativo')
        if not profesional_id or not rol:
            return Response(
                {'error': 'Se requieren profesional y rol_en_operativo'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            op = services.asignar_profesional(pk, profesional_id, rol)
            serializer = OperativoProfesionalSerializer(op)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


class OperativoProfesionalRemoveView(APIView):
    permission_classes = [require_action('gestionarProfesionalesEnOperativo')]

    def delete(self, request, pk, prof_pk):
        rel = get_object_or_404(
            OperativoProfesional, operativo_id=pk, pk=prof_pk,
        )
        rel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────
#  Alumnos
# ──────────────────────────────────────────────
class OperativoAlumnoListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verOperativo')()]
        return [require_action('importarNominaOperativo')()]

    def get(self, request, pk):
        qs = OperativoAlumno.objects.filter(operativo_id=pk)
        estado = request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        serializer = OperativoAlumnoSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        get_object_or_404(Operativo, pk=pk)
        serializer = OperativoAlumnoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(operativo_id=pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OperativoAlumnoDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verOperativo')()]
        if self.request.method == 'PATCH':
            return [require_action('gestionarEstadoAlumnoEnOperativo')()]
        if self.request.method == 'DELETE':
            return [require_action('editarOperativo')()]
        return []

    def get_object(self, operativo_pk, alumno_pk):
        return get_object_or_404(
            OperativoAlumno, operativo_id=operativo_pk, pk=alumno_pk,
        )

    def get(self, request, pk, alumno_pk):
        alumno = self.get_object(pk, alumno_pk)
        serializer = OperativoAlumnoSerializer(alumno)
        return Response(serializer.data)

    def patch(self, request, pk, alumno_pk):
        alumno = self.get_object(pk, alumno_pk)
        serializer = OperativoAlumnoEstadoSerializer(alumno, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk, alumno_pk):
        alumno = self.get_object(pk, alumno_pk)
        alumno.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OperativoAlumnoImportCSVView(APIView):
    permission_classes = [require_action('importarNominaOperativo')]

    def post(self, request, pk):
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response(
                {'error': 'Se requiere un archivo CSV'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            resultado = services.importar_csv(pk, archivo)
            return Response(resultado)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)

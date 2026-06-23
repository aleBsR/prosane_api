from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.usuarios.permissions import require_action
from .models import (
    Operativo, OperativoProfesional, OperativoAlumno,
    EvaluacionMedica, EvaluacionOdontologica,
)
from .serializers import (
    OperativoListSerializer,
    OperativoDetailSerializer,
    OperativoProfesionalSerializer,
    OperativoAlumnoSerializer,
    OperativoAlumnoEstadoSerializer,
    EvaluacionMedicaSerializer,
    EvaluacionOdontologicaSerializer,
    SeccionEscuelaSerializer,
)
from . import queries, services


# ──────────────────────────────────────────────
#  Operativos CRUD
# ──────────────────────────────────────────────
class OperativoListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verOperativo')()]
        return [require_action('crearOperativo')()]

    def get(self, request):
        qs = queries.operativos_visibles_para_usuario(request.user)
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

    def get(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        serializer = OperativoDetailSerializer(operativo)
        return Response(serializer.data)

    def put(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        serializer = OperativoDetailSerializer(operativo, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        serializer = OperativoDetailSerializer(operativo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        services.cancelar_operativo(operativo.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────
#  Acciones de estado
# ──────────────────────────────────────────────
class OperativoConfirmarView(APIView):
    permission_classes = [require_action('confirmarOperativo')]

    def post(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        try:
            op = services.confirmar_operativo(operativo.id)
            serializer = OperativoDetailSerializer(op)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


class OperativoFinalizarView(APIView):
    permission_classes = [require_action('finalizarOperativo')]

    def post(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        try:
            op = services.finalizar_operativo(operativo.id)
            serializer = OperativoDetailSerializer(op)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


class OperativoCancelarView(APIView):
    permission_classes = [require_action('cancelarOperativo')]

    def post(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        try:
            op = services.cancelar_operativo(operativo.id)
            serializer = OperativoDetailSerializer(op)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


class OperativoIniciarView(APIView):
    permission_classes = [require_action('iniciarOperativo')]

    def post(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        try:
            op = services.iniciar_operativo(operativo.id)
            serializer = OperativoDetailSerializer(op)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


# ──────────────────────────────────────────────
#  Profesionales
# ──────────────────────────────────────────────
class ProfesionalesDisponiblesView(APIView):
    """Lista los usuarios con rol médico u odontólogo, para asignarlos a un operativo."""
    permission_classes = [require_action('gestionarProfesionalesEnOperativo')]

    def get(self, request):
        from apps.usuarios.models import Usuario
        usuarios = (
            Usuario.objects
            .filter(roles__rol__in=['medico', 'odontologo'], is_active=True)
            .prefetch_related('roles', 'persona')
            .distinct()
        )
        data = []
        for u in usuarios:
            roles_prof = [r.rol for r in u.roles.all() if r.rol in ('medico', 'odontologo')]
            nombre = u.persona.nombre if u.persona else ''
            apellido = u.persona.apellido if u.persona else ''
            data.append({
                'id': str(u.id),
                'email': u.email,
                'nombre': nombre,
                'apellido': apellido,
                'roles': roles_prof,
            })
        return Response(data)


class OperativoProfesionalListView(APIView):
    permission_classes = [require_action('verOperativo')]

    def get(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        qs = OperativoProfesional.objects.filter(operativo=operativo)
        serializer = OperativoProfesionalSerializer(qs, many=True)
        return Response(serializer.data)


class OperativoProfesionalAssignView(APIView):
    permission_classes = [require_action('gestionarProfesionalesEnOperativo')]

    def post(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        profesional_id = request.data.get('profesional')
        rol = request.data.get('rol_en_operativo')
        if not profesional_id or not rol:
            return Response(
                {'error': 'Se requieren profesional y rol_en_operativo'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            op = services.asignar_profesional(operativo.id, profesional_id, rol)
            serializer = OperativoProfesionalSerializer(op)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


class OperativoProfesionalRemoveView(APIView):
    permission_classes = [require_action('gestionarProfesionalesEnOperativo')]

    def delete(self, request, pk, prof_pk):
        try:
            services.remover_profesional(pk, prof_pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


# ──────────────────────────────────────────────
#  Alumnos
# ──────────────────────────────────────────────
class OperativoAlumnoListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verOperativo')()]
        return [require_action('importarNominaOperativo')()]

    def get(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        qs = OperativoAlumno.objects.filter(operativo=operativo)
        estado = request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        serializer = OperativoAlumnoSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        serializer = OperativoAlumnoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(operativo=operativo)
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
        operativo = queries.obtener_operativo_visible(self.request.user, operativo_pk)
        return OperativoAlumno.objects.get(operativo=operativo, pk=alumno_pk)

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
        operativo = queries.obtener_operativo_visible(request.user, pk)
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response(
                {'error': 'Se requiere un archivo CSV'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            resultado = services.importar_csv(operativo.id, archivo)
            return Response(resultado)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)


# ──────────────────────────────────────────────
#  Evaluación clínica por alumno
# ──────────────────────────────────────────────
class EvaluacionMedicaView(APIView):
    permission_classes = [require_action('cargarEvaluacionMedica')]
    rol_requerido = 'medico'

    def _get_alumno(self, request, pk, alumno_pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        alumno = OperativoAlumno.objects.get(operativo=operativo, pk=alumno_pk)
        return operativo, alumno

    def _profesional_asignado(self, operativo, user):
        return OperativoProfesional.objects.filter(
            operativo=operativo, profesional=user, rol_en_operativo=self.rol_requerido,
        ).exists()

    def get(self, request, pk, alumno_pk):
        operativo, alumno = self._get_alumno(request, pk, alumno_pk)
        if not self._profesional_asignado(operativo, request.user):
            return Response(
                {'error': f'No estás asignado a este operativo como {self.rol_requerido}'},
                status=status.HTTP_403_FORBIDDEN,
            )
        evaluacion, _ = EvaluacionMedica.objects.get_or_create(operativo_alumno=alumno)
        return Response(EvaluacionMedicaSerializer(evaluacion).data)

    def put(self, request, pk, alumno_pk):
        operativo, alumno = self._get_alumno(request, pk, alumno_pk)
        if not self._profesional_asignado(operativo, request.user):
            return Response(
                {'error': f'No estás asignado a este operativo como {self.rol_requerido}'},
                status=status.HTTP_403_FORBIDDEN,
            )
        evaluacion, _ = EvaluacionMedica.objects.get_or_create(operativo_alumno=alumno)
        serializer = EvaluacionMedicaSerializer(evaluacion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            profesional=request.user,
            fecha_evaluacion=timezone.now(),
            completada=True,
        )
        return Response(serializer.data)


class EvaluacionOdontologicaView(APIView):
    permission_classes = [require_action('cargarEvaluacionOdontologica')]
    rol_requerido = 'odontologo'

    def _get_alumno(self, request, pk, alumno_pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        alumno = OperativoAlumno.objects.get(operativo=operativo, pk=alumno_pk)
        return operativo, alumno

    def _profesional_asignado(self, operativo, user):
        return OperativoProfesional.objects.filter(
            operativo=operativo, profesional=user, rol_en_operativo=self.rol_requerido,
        ).exists()

    def get(self, request, pk, alumno_pk):
        operativo, alumno = self._get_alumno(request, pk, alumno_pk)
        if not self._profesional_asignado(operativo, request.user):
            return Response(
                {'error': f'No estás asignado a este operativo como {self.rol_requerido}'},
                status=status.HTTP_403_FORBIDDEN,
            )
        evaluacion, _ = EvaluacionOdontologica.objects.get_or_create(operativo_alumno=alumno)
        return Response(EvaluacionOdontologicaSerializer(evaluacion).data)

    def put(self, request, pk, alumno_pk):
        operativo, alumno = self._get_alumno(request, pk, alumno_pk)
        if not self._profesional_asignado(operativo, request.user):
            return Response(
                {'error': f'No estás asignado a este operativo como {self.rol_requerido}'},
                status=status.HTTP_403_FORBIDDEN,
            )
        evaluacion, _ = EvaluacionOdontologica.objects.get_or_create(operativo_alumno=alumno)
        serializer = EvaluacionOdontologicaSerializer(evaluacion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            profesional=request.user,
            fecha_evaluacion=timezone.now(),
            completada=True,
        )
        return Response(serializer.data)


class OperativoCompletitudView(APIView):
    """Resumen de completitud de alumnos de un operativo."""
    permission_classes = [require_action('verOperativo')]

    def get(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        alumnos = list(operativo.alumnos.all())
        total = len(alumnos)
        completos = sum(1 for a in alumnos if a.completo)
        return Response({
            'total_alumnos': total,
            'completos': completos,
            'pendientes': total - completos,
            'puede_finalizar': operativo.puede_finalizar,
        })


class SeccionEscuelaView(APIView):
    permission_classes = [require_action('cargarSeccionEscuela')]

    def patch(self, request, pk, alumno_pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        alumno = OperativoAlumno.objects.get(operativo=operativo, pk=alumno_pk)
        serializer = SeccionEscuelaSerializer(alumno, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(escuela_completado=True)
        return Response(serializer.data)

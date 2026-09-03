from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.usuarios.permissions import require_action, require_any_action
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


def _auto_evaluar_si_completo(alumno: OperativoAlumno):
    """Si el alumno quedó completo (E+A+M+O) y está en presente, pasarlo a evaluado automáticamente."""
    try:
        if alumno.estado == OperativoAlumno.PRESENTE and alumno.completo:
            alumno.estado = OperativoAlumno.EVALUADO
            alumno.save(update_fields=['estado', 'updated_at'])
    except Exception:
        pass


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
        try:
            services.exigir_operativo_mutable(operativo)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        serializer = OperativoDetailSerializer(operativo, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        try:
            services.exigir_operativo_mutable(operativo)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
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
        qs = OperativoAlumno.objects.filter(operativo=operativo).order_by('apellido', 'nombre', 'dni')
        estado = request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        serializer = OperativoAlumnoSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        try:
            services.exigir_operativo_mutable(operativo)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
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
        try:
            services.exigir_operativo_mutable(alumno.operativo)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        # Evaluado es automático: no permitir marcar manualmente si no está completo
        nuevo_estado = (request.data or {}).get('estado')
        if nuevo_estado == OperativoAlumno.EVALUADO and not alumno.completo:
            # Refrescar flags por si el cliente tiene cache vieja
            alumno.refresh_from_db()
            if not alumno.completo:
                return Response(
                    {'error': 'No se puede marcar como evaluado hasta completar E, A, M y O. El estado evaluado es automático.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        serializer = OperativoAlumnoEstadoSerializer(alumno, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk, alumno_pk):
        alumno = self.get_object(pk, alumno_pk)
        try:
            services.exigir_operativo_mutable(alumno.operativo)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
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
        if operativo.estado in services.ESTADOS_NO_EDITABLES:
            try:
                evaluacion = EvaluacionMedica.objects.get(operativo_alumno=alumno)
            except EvaluacionMedica.DoesNotExist:
                return Response(
                    {'error': 'El operativo está finalizado o cancelado y no existe evaluación médica'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(EvaluacionMedicaSerializer(evaluacion).data)
        if operativo.estado != Operativo.EN_CURSO:
            # Fuera de EN_CURSO no se crea evaluación nueva; solo lectura si ya existe
            try:
                evaluacion = EvaluacionMedica.objects.get(operativo_alumno=alumno)
            except EvaluacionMedica.DoesNotExist:
                return Response(
                    {'error': 'Solo se puede cargar la evaluación médica cuando el operativo está en curso'},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(EvaluacionMedicaSerializer(evaluacion).data)
        evaluacion, _ = EvaluacionMedica.objects.get_or_create(operativo_alumno=alumno)
        return Response(EvaluacionMedicaSerializer(evaluacion).data)

    def put(self, request, pk, alumno_pk):
        operativo, alumno = self._get_alumno(request, pk, alumno_pk)
        if not self._profesional_asignado(operativo, request.user):
            return Response(
                {'error': f'No estás asignado a este operativo como {self.rol_requerido}'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            services.exigir_operativo_en_curso(operativo)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        evaluacion, _ = EvaluacionMedica.objects.get_or_create(operativo_alumno=alumno)
        serializer = EvaluacionMedicaSerializer(evaluacion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            profesional=request.user,
            fecha_evaluacion=timezone.now(),
            completada=True,
        )
        # Auto-evaluado si con esta carga quedó completo (E+A+M+O)
        alumno.refresh_from_db()
        _auto_evaluar_si_completo(alumno)
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
        if operativo.estado in services.ESTADOS_NO_EDITABLES:
            try:
                evaluacion = EvaluacionOdontologica.objects.get(operativo_alumno=alumno)
            except EvaluacionOdontologica.DoesNotExist:
                return Response(
                    {'error': 'El operativo está finalizado o cancelado y no existe evaluación odontológica'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(EvaluacionOdontologicaSerializer(evaluacion).data)
        if operativo.estado != Operativo.EN_CURSO:
            try:
                evaluacion = EvaluacionOdontologica.objects.get(operativo_alumno=alumno)
            except EvaluacionOdontologica.DoesNotExist:
                return Response(
                    {'error': 'Solo se puede cargar la evaluación odontológica cuando el operativo está en curso'},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(EvaluacionOdontologicaSerializer(evaluacion).data)
        evaluacion, _ = EvaluacionOdontologica.objects.get_or_create(operativo_alumno=alumno)
        return Response(EvaluacionOdontologicaSerializer(evaluacion).data)

    def put(self, request, pk, alumno_pk):
        operativo, alumno = self._get_alumno(request, pk, alumno_pk)
        if not self._profesional_asignado(operativo, request.user):
            return Response(
                {'error': f'No estás asignado a este operativo como {self.rol_requerido}'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            services.exigir_operativo_en_curso(operativo)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        evaluacion, _ = EvaluacionOdontologica.objects.get_or_create(operativo_alumno=alumno)
        serializer = EvaluacionOdontologicaSerializer(evaluacion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            profesional=request.user,
            fecha_evaluacion=timezone.now(),
            completada=True,
        )
        alumno.refresh_from_db()
        _auto_evaluar_si_completo(alumno)
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

    def get(self, request, pk, alumno_pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        alumno = OperativoAlumno.objects.get(operativo=operativo, pk=alumno_pk)
        serializer = SeccionEscuelaSerializer(alumno)
        return Response(serializer.data)

    def patch(self, request, pk, alumno_pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        try:
            services.exigir_operativo_mutable(operativo)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        alumno = OperativoAlumno.objects.get(operativo=operativo, pk=alumno_pk)
        serializer = SeccionEscuelaSerializer(alumno, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(escuela_completado=True)
        alumno.refresh_from_db()
        _auto_evaluar_si_completo(alumno)
        return Response(serializer.data)


class OperativoAlumnoDatosView(APIView):
    """GET/PATCH datos completos del alumno para escuela (igual que tutor).

    Permite a escuela cargar/editar datos personales + antecedentes del Paciente
    vinculado al OperativoAlumno. Solo si el operativo pertenece a su escuela.
    GET en solo lectura (finalizado) también para ayudante/superadmin con verOperativo.
    """
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_any_action('cargarAntecedentesNino', 'verOperativo')()]
        return [require_action('cargarAntecedentesNino')()]

    def _get_objs(self, request, pk, alumno_pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        # Escuela solo puede editar alumnos de su escuela (o superadmin)
        if not request.user.is_superuser and request.user.escuela_id and str(operativo.escuela_id) != str(request.user.escuela_id):
            from django.http import Http404
            raise Http404
        alumno = OperativoAlumno.objects.select_related('paciente__persona', 'paciente__domicilio', 'paciente__escuela').get(operativo=operativo, pk=alumno_pk)
        # Si no tiene paciente, lo creamos al vuelo al hacer PATCH; para GET devolvemos snapshot
        return operativo, alumno

    def get(self, request, pk, alumno_pk):
        operativo, alumno = self._get_objs(request, pk, alumno_pk)
        # Si tiene paciente, devolver datos del Paciente + antecedentes, sino snapshot del OperativoAlumno
        if alumno.paciente_id:
            from apps.antecedentes.models import AntecedentePersonal
            try:
                ant = AntecedentePersonal.objects.get(paciente=alumno.paciente)
            except AntecedentePersonal.DoesNotExist:
                ant = None
            data = {
                'operativo_alumno': {
                    'id': str(alumno.id),
                    'dni': alumno.dni,
                    'apellido': alumno.apellido,
                    'nombre': alumno.nombre,
                    'tipo_dni': alumno.tipo_dni,
                    'fecha_nacimiento': alumno.fecha_nacimiento.isoformat() if alumno.fecha_nacimiento else None,
                    'sexo': alumno.sexo,
                    'curso': str(alumno.curso_id) if alumno.curso_id else None,
                    'estado': alumno.estado,
                },
                'paciente': {
                    'id': str(alumno.paciente_id),
                    'edad': alumno.paciente.edad,
                    'tiene_cud': alumno.paciente.tiene_cud,
                    'tipo_cobertura': alumno.paciente.tipo_cobertura,
                    'nombre_cobertura': alumno.paciente.nombre_cobertura,
                    'telefono_fijo': alumno.paciente.telefono_fijo,
                    'celular': alumno.paciente.celular,
                },
                'persona': {
                    'nombre': alumno.paciente.persona.nombre if alumno.paciente.persona else '',
                    'apellido': alumno.paciente.persona.apellido if alumno.paciente.persona else '',
                    'dni': alumno.paciente.persona.dni if alumno.paciente.persona else alumno.dni,
                    'tipo_dni': alumno.paciente.persona.tipo_dni if alumno.paciente.persona else alumno.tipo_dni,
                    'sexo': alumno.paciente.persona.sexo if alumno.paciente.persona else alumno.sexo,
                    'fecha_nacimiento': alumno.paciente.persona.fecha_nacimiento.isoformat() if alumno.paciente.persona and alumno.paciente.persona.fecha_nacimiento else None,
                } if alumno.paciente and alumno.paciente.persona else None,
                'domicilio': {
                    'localidad': alumno.paciente.domicilio.localidad if alumno.paciente and alumno.paciente.domicilio else '',
                    'calle': alumno.paciente.domicilio.calle if alumno.paciente and alumno.paciente.domicilio else '',
                } if alumno.paciente and alumno.paciente.domicilio else None,
                'antecedentes': {
                    'nacio_prematuro': ant.nacio_prematuro if ant else 'NO',
                    'peso_nacimiento': ant.peso_nacimiento if ant else '0',
                    'convulsiones_epilepsia': ant.convulsiones_epilepsia if ant else 'NO',
                    'mareos_desmayos': ant.mareos_desmayos if ant else 'NO',
                    'infecciones_urinarias': ant.infecciones_urinarias if ant else 'NO',
                    'asma_espasmos': ant.asma_espasmos if ant else 'NO',
                    'tuberculosis': ant.tuberculosis if ant else 'NO',
                    'diabetes': ant.diabetes if ant else 'NO',
                    'hipertension': ant.hipertension if ant else 'NO',
                    'cardiopatia_congenita': ant.cardiopatia_congenita if ant else 'NO',
                    'traumatismo_internacion': ant.traumatismo_internacion if ant else 'NO',
                    'diarrea_frecuente': ant.diarrea_frecuente if ant else 'NO',
                    'infecciones_oido': ant.infecciones_oido if ant else 'NO',
                    'internacion_previa': ant.internacion_previa if ant else 'NO',
                    'causa_hospitalizacion': ant.causa_hospitalizacion if ant else 'NO',
                    'tratamiento_actual': ant.tratamiento_actual if ant else 'NO',
                    'descripcion_tratamiento': ant.descripcion_tratamiento if ant else 'NINGUNO',
                    'ultima_consulta_medica': ant.ultima_consulta_medica if ant else 'NINGUNA',
                    'otros_problemas_salud': ant.otros_problemas_salud if ant else 'NINGUNO',
                    'primera_menstruacion': ant.primera_menstruacion if ant else 'NO',
                    'edad_primera_menstruacion': ant.edad_primera_menstruacion if ant else 0,
                } if ant else None,
                'escuela_completado': alumno.escuela_completado,
            }
            return Response(data)
        # Sin paciente: devolver snapshot para que escuela lo complete
        return Response({
            'operativo_alumno': {
                'id': str(alumno.id),
                'dni': alumno.dni,
                'apellido': alumno.apellido,
                'nombre': alumno.nombre,
                'tipo_dni': alumno.tipo_dni,
                'fecha_nacimiento': alumno.fecha_nacimiento.isoformat() if alumno.fecha_nacimiento else None,
                'sexo': alumno.sexo,
                'curso': str(alumno.curso_id) if alumno.curso_id else None,
                'estado': alumno.estado,
            },
            'paciente': None,
            'persona': None,
            'domicilio': None,
            'antecedentes': None,
            'escuela_completado': alumno.escuela_completado,
            'antecedentes_completado': alumno.antecedentes_completado,
        })

    def patch(self, request, pk, alumno_pk):
        operativo, alumno = self._get_objs(request, pk, alumno_pk)
        try:
            services.exigir_operativo_mutable(operativo)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        data = request.data or {}
        # Actualizar snapshot del OperativoAlumno si vienen esos campos
        for field in ['apellido', 'nombre', 'tipo_dni', 'dni', 'sexo']:
            if field in data:
                setattr(alumno, field, data[field])
        if 'fecha_nacimiento' in data and data['fecha_nacimiento']:
            try:
                from datetime import datetime
                alumno.fecha_nacimiento = datetime.strptime(data['fecha_nacimiento'], '%Y-%m-%d').date()
            except Exception:
                pass
        if 'curso' in data:
            try:
                from apps.escuelas.models import Curso
                if data['curso']:
                    curso = Curso.objects.get(pk=data['curso'], escuela=operativo.escuela)
                    alumno.curso = curso
                else:
                    alumno.curso = None
            except Exception:
                pass
        alumno.save()

        # Si tiene paciente, actualizar Paciente/Persona/Domicilio/Antecedentes
        if alumno.paciente_id:
            paciente = alumno.paciente
            persona = paciente.persona
            domicilio = paciente.domicilio
            # Persona
            if persona:
                for f in ['nombre', 'apellido', 'dni', 'tipo_dni', 'sexo']:
                    if f in data and data[f] not in (None, ''):
                        setattr(persona, f, data[f])
                if 'fecha_nacimiento' in data and data['fecha_nacimiento']:
                    try:
                        from datetime import datetime
                        persona.fecha_nacimiento = datetime.strptime(data['fecha_nacimiento'], '%Y-%m-%d').date()
                    except Exception:
                        pass
                persona.save()
            # Paciente
            for f in ['edad', 'tiene_cud', 'tipo_cobertura', 'nombre_cobertura', 'telefono_fijo', 'celular']:
                if f in data:
                    setattr(paciente, f, data[f])
            paciente.save()
            # Domicilio
            if domicilio and 'localidad' in data:
                domicilio.localidad = data['localidad'] or domicilio.localidad
                domicilio.save()
            # Antecedentes
            if 'antecedentes' in data and isinstance(data['antecedentes'], dict):
                from apps.antecedentes.models import AntecedentePersonal
                ant, _ = AntecedentePersonal.objects.get_or_create(paciente=paciente)
                for k, v in data['antecedentes'].items():
                    if hasattr(ant, k):
                        setattr(ant, k, v)
                ant.save()
        else:
            # Sin paciente: crear uno nuevo con los datos enviados (como en importar_csv)
            from apps.personas.models import Persona, Domicilio
            from apps.pacientes.models import Paciente
            from apps.antecedentes.models import AntecedentePersonal
            # Crear persona
            persona_data = {
                'nombre': data.get('nombre') or alumno.nombre or '',
                'apellido': data.get('apellido') or alumno.apellido or '',
                'dni': data.get('dni') or alumno.dni,
                'tipo_dni': data.get('tipo_dni') or alumno.tipo_dni or 'DNI',
                'sexo': data.get('sexo') or alumno.sexo or 'otro',
                'fecha_nacimiento': alumno.fecha_nacimiento or '2000-01-01',
            }
            if 'fecha_nacimiento' in data and data['fecha_nacimiento']:
                try:
                    from datetime import datetime
                    persona_data['fecha_nacimiento'] = datetime.strptime(data['fecha_nacimiento'], '%Y-%m-%d').date()
                except Exception:
                    pass
            persona = Persona.objects.create(**persona_data)
            domicilio = Domicilio.objects.create(localidad=data.get('localidad') or '')
            # Calcular edad
            edad = data.get('edad') or 0
            if not edad and persona.fecha_nacimiento:
                try:
                    from datetime import datetime as dt
                    hoy = dt.now().date()
                    edad = hoy.year - persona.fecha_nacimiento.year - ((hoy.month, hoy.day) < (persona.fecha_nacimiento.month, persona.fecha_nacimiento.day))
                except Exception:
                    edad = 0
            paciente = Paciente.objects.create(
                escuela=operativo.escuela,
                persona=persona,
                domicilio=domicilio,
                edad=edad,
                tiene_cud=data.get('tiene_cud'),
                tipo_cobertura=data.get('tipo_cobertura'),
                nombre_cobertura=data.get('nombre_cobertura'),
                telefono_fijo=data.get('telefono_fijo'),
                celular=data.get('celular'),
            )
            AntecedentePersonal.objects.get_or_create(paciente=paciente)
            if 'antecedentes' in data and isinstance(data['antecedentes'], dict):
                ant, _ = AntecedentePersonal.objects.get_or_create(paciente=paciente)
                for k, v in data['antecedentes'].items():
                    if hasattr(ant, k):
                        setattr(ant, k, v)
                ant.save()
            alumno.paciente = paciente
            alumno.save(update_fields=['paciente'])

        alumno.antecedentes_completado = True
        alumno.save(update_fields=['antecedentes_completado'])
        alumno.refresh_from_db()
        _auto_evaluar_si_completo(alumno)

        return self.get(request, pk, alumno_pk)


# ──────────────────────────────────────────────
#  Constancia por alumno (PDF)
# ──────────────────────────────────────────────
class ConstanciaAlumnoView(APIView):
    permission_classes = [require_action('verOperativo')]

    def get(self, request, pk, alumno_pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        if operativo.estado != Operativo.FINALIZADO:
            return Response(
                {'error': 'La constancia solo está disponible cuando el operativo está finalizado'},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            alumno = OperativoAlumno.objects.select_related('curso', 'operativo__escuela').get(operativo=operativo, pk=alumno_pk)
        except OperativoAlumno.DoesNotExist:
            return Response({'error': 'Alumno no encontrado en este operativo'}, status=status.HTTP_404_NOT_FOUND)
        # Ausente también tiene constancia; para pendiente/incompleto no se bloquea pero se informa en PDF
        from .services_constancia import generar_constancia_pdf
        pdf_bytes = generar_constancia_pdf(operativo, alumno)
        filename = f"constancia-{alumno.dni or alumno_pk}.pdf"
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{filename}"'
        return resp


# ──────────────────────────────────────────────
#  Export resumen operativo (PDF / Excel / CSV)
# ──────────────────────────────────────────────
class ExportOperativoView(APIView):
    permission_classes = [require_action('verOperativo')]

    def get(self, request, pk):
        operativo = queries.obtener_operativo_visible(request.user, pk)
        if operativo.estado != Operativo.FINALIZADO:
            return Response(
                {'error': 'La exportación solo está disponible cuando el operativo está finalizado'},
                status=status.HTTP_409_CONFLICT,
            )
        formato = (request.query_params.get('formato') or request.query_params.get('format') or 'pdf').lower()
        if formato not in ('pdf', 'excel', 'xlsx', 'csv'):
            return Response({'error': 'Formato no soportado. Use pdf, excel o csv'}, status=status.HTTP_400_BAD_REQUEST)

        if formato == 'csv':
            from .services_export import generar_export_csv
            data = generar_export_csv(operativo)
            resp = HttpResponse(data, content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="operativo-{operativo.id}.csv"'
            return resp
        if formato in ('excel', 'xlsx'):
            from .services_export import generar_export_excel
            data = generar_export_excel(operativo)
            resp = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = f'attachment; filename="operativo-{operativo.id}.xlsx"'
            return resp
        # pdf default
        from .services_export import generar_export_pdf
        data = generar_export_pdf(operativo)
        resp = HttpResponse(data, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="operativo-{operativo.id}.pdf"'
        return resp

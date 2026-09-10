import uuid

from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

from django.shortcuts import get_object_or_404

from apps.antecedentes.models import AntecedentePersonal
from apps.escuelas.models import Escuela
from apps.usuarios.permissions import require_action
from .models import Paciente
from .services.alumnos import (
    AlumnoEscuelaError,
    crear_alumno_escuela,
    listar_alumnos_escuela,
)


class PersonaAlumnoSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    apellido = serializers.CharField()
    dni = serializers.CharField()
    tipo_dni = serializers.CharField(required=False, allow_blank=True, default='DNI')
    sexo = serializers.CharField()
    fecha_nacimiento = serializers.DateField()


class DomicilioAlumnoSerializer(serializers.Serializer):
    calle = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    nro_calle = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    piso = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    dpto = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    provincia = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    departamento = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    localidad = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class AntecedentePersonalInputSerializer(serializers.Serializer):
    nacio_prematuro = serializers.CharField(required=False, allow_blank=True, default="NO")
    peso_nacimiento = serializers.CharField(required=False, allow_blank=True, default="0")
    convulsiones_epilepsia = serializers.CharField(required=False, allow_blank=True, default="NO")
    mareos_desmayos = serializers.CharField(required=False, allow_blank=True, default="NO")
    infecciones_urinarias = serializers.CharField(required=False, allow_blank=True, default="NO")
    asma_espasmos = serializers.CharField(required=False, allow_blank=True, default="NO")
    tuberculosis = serializers.CharField(required=False, allow_blank=True, default="NO")
    diabetes = serializers.CharField(required=False, allow_blank=True, default="NO")
    hipertension = serializers.CharField(required=False, allow_blank=True, default="NO")
    cardiopatia_congenita = serializers.CharField(required=False, allow_blank=True, default="NO")
    traumatismo_internacion = serializers.CharField(required=False, allow_blank=True, default="NO")
    diarrea_frecuente = serializers.CharField(required=False, allow_blank=True, default="NO")
    infecciones_oido = serializers.CharField(required=False, allow_blank=True, default="NO")
    internacion_previa = serializers.CharField(required=False, allow_blank=True, default="NO")
    causa_hospitalizacion = serializers.CharField(required=False, allow_blank=True, default="NO")
    tratamiento_actual = serializers.CharField(required=False, allow_blank=True, default="NO")
    descripcion_tratamiento = serializers.CharField(required=False, allow_blank=True, default="NINGUNO")
    ultima_consulta_medica = serializers.CharField(required=False, allow_blank=True, default="NINGUNA")
    otros_problemas_salud = serializers.CharField(required=False, allow_blank=True, default="NINGUNO")
    primera_menstruacion = serializers.CharField(required=False, allow_blank=True, default="NO")
    edad_primera_menstruacion = serializers.IntegerField(required=False, default=0)


class AlumnoEscuelaCreateSerializer(serializers.Serializer):
    persona = PersonaAlumnoSerializer()
    domicilio = DomicilioAlumnoSerializer(required=False, default=dict)
    edad = serializers.IntegerField(min_value=0)
    tiene_cud = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tipo_cobertura = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    nombre_cobertura = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    telefono_fijo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    celular = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    curso_id = serializers.UUIDField(required=False, allow_null=True)
    operativo_id = serializers.UUIDField(required=False, allow_null=True)
    antecedentes = AntecedentePersonalInputSerializer(required=False, default=dict)


class AntecedentePersonalOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedentePersonal
        fields = [
            'nacio_prematuro', 'peso_nacimiento', 'convulsiones_epilepsia',
            'mareos_desmayos', 'infecciones_urinarias', 'asma_espasmos',
            'tuberculosis', 'diabetes', 'hipertension', 'cardiopatia_congenita',
            'traumatismo_internacion', 'diarrea_frecuente', 'infecciones_oido',
            'internacion_previa', 'causa_hospitalizacion', 'tratamiento_actual', 'descripcion_tratamiento',
            'ultima_consulta_medica', 'otros_problemas_salud',
            'primera_menstruacion', 'edad_primera_menstruacion',
        ]


class AlumnoEscuelaOutputSerializer(serializers.ModelSerializer):
    persona = PersonaAlumnoSerializer(read_only=True)
    domicilio = DomicilioAlumnoSerializer(read_only=True)
    escuela_nombre = serializers.CharField(source='escuela.nombre', read_only=True)
    operativos = serializers.SerializerMethodField()
    antecedentes = serializers.SerializerMethodField()

    class Meta:
        model = Paciente
        fields = [
            'id', 'persona', 'domicilio', 'escuela', 'escuela_nombre', 'edad',
            'tiene_cud', 'tipo_cobertura', 'nombre_cobertura',
            'telefono_fijo', 'celular', 'consentimiento_aceptado',
            'operativos', 'antecedentes',
        ]

    def get_antecedentes(self, obj):
        try:
            ant = AntecedentePersonal.objects.get(paciente=obj)
            return AntecedentePersonalOutputSerializer(ant).data
        except AntecedentePersonal.DoesNotExist:
            return None

    def get_operativos(self, obj):
        return [
            {
                'id': str(item.operativo_id),
                'nombre': item.operativo.nombre or item.operativo.escuela.nombre,
                'fecha': item.operativo.fecha.isoformat(),
                'curso_id': str(item.curso_id) if item.curso_id else None,
                'curso_display': (
                    f'{item.curso.sala_grado_anio} {item.curso.division}'.strip()
                    if item.curso_id else ''
                ),
            }
            for item in obj.operativos_como_alumno.select_related(
                'operativo', 'curso', 'operativo__escuela',
            ).all()
        ]


class EscuelaAlumnosListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [require_action('verAlumnosEscuela')()]
        return [require_action('registrarAlumnoEscuela')()]

    def _escuela_id(self, request):
        if not request.user.escuela_id:
            return None
        if not request.user.roles.filter(rol='escuela').exists() and not request.user.is_superuser:
            return None
        return request.user.escuela_id

    def get(self, request):
        # ?escuela_id= permite al superadmin ver los alumnos de una escuela
        # puntual (detalle de escuela). El resto sigue con su propia escuela.
        param = request.query_params.get('escuela_id')
        if param:
            if not request.user.is_superuser:
                return Response(
                    {'detail': 'Sin permiso para ver alumnos de otra escuela.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            try:
                escuela_uuid = uuid.UUID(str(param))
            except (ValueError, AttributeError):
                return Response(
                    {'detail': 'escuela_id inválido.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not Escuela.objects.filter(pk=escuela_uuid).exists():
                return Response(
                    {'detail': 'Escuela no encontrada.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            escuela_id = escuela_uuid
        else:
            escuela_id = self._escuela_id(request)
            if not escuela_id:
                return Response({'detail': 'El usuario no tiene una escuela asignada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AlumnoEscuelaOutputSerializer(
            listar_alumnos_escuela(escuela_id), many=True,
        ).data)

    def post(self, request):
        escuela_id = self._escuela_id(request)
        if not escuela_id:
            return Response({'detail': 'El usuario no tiene una escuela asignada.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AlumnoEscuelaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            alumno = crear_alumno_escuela(escuela_id, serializer.validated_data)
        except AlumnoEscuelaError as exc:
            return Response(
                {exc.field or 'detail': [exc.message]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AlumnoEscuelaOutputSerializer(alumno).data, status=status.HTTP_201_CREATED)


class AlumnoAntecedentesView(APIView):
    """GET/PATCH /alumnos/<pk>/antecedentes/ — antecedentes personales del alumno.

    Solo para la escuela del alumno (o superadmin). Requiere cargarAntecedentesNino.
    """
    def get_permissions(self):
        return [require_action('cargarAntecedentesNino')()]

    def _get_paciente(self, request, pk):
        escuela_id = request.user.escuela_id
        if not escuela_id and not request.user.is_superuser:
            return None
        try:
            paciente = Paciente.objects.select_related('escuela').get(pk=pk)
        except Paciente.DoesNotExist:
            return None
        if not request.user.is_superuser and str(paciente.escuela_id) != str(escuela_id):
            return None
        return paciente

    def get(self, request, pk):
        paciente = self._get_paciente(request, pk)
        if not paciente:
            return Response({'detail': 'Alumno no encontrado o sin permiso.'}, status=status.HTTP_404_NOT_FOUND)
        from apps.antecedentes.models import AntecedentePersonal
        ant, _ = AntecedentePersonal.objects.get_or_create(paciente=paciente)
        return Response(AntecedentePersonalOutputSerializer(ant).data)

    def patch(self, request, pk):
        paciente = self._get_paciente(request, pk)
        if not paciente:
            return Response({'detail': 'Alumno no encontrado o sin permiso.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AntecedentePersonalInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        from .services.alumnos import actualizar_antecedentes_paciente
        ant = actualizar_antecedentes_paciente(paciente, serializer.validated_data)
        return Response(AntecedentePersonalOutputSerializer(ant).data)

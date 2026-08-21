from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

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


class AlumnoEscuelaOutputSerializer(serializers.ModelSerializer):
    persona = PersonaAlumnoSerializer(read_only=True)
    domicilio = DomicilioAlumnoSerializer(read_only=True)
    escuela_nombre = serializers.CharField(source='escuela.nombre', read_only=True)
    operativos = serializers.SerializerMethodField()

    class Meta:
        model = Paciente
        fields = [
            'id', 'persona', 'domicilio', 'escuela', 'escuela_nombre', 'edad',
            'tiene_cud', 'tipo_cobertura', 'nombre_cobertura',
            'telefono_fijo', 'celular', 'consentimiento_aceptado',
            'operativos',
        ]

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

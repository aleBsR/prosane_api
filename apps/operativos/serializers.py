from rest_framework import serializers
from .models import Operativo, OperativoProfesional, OperativoAlumno


class OperativoProfesionalSerializer(serializers.ModelSerializer):
    profesional_email = serializers.EmailField(
        source='profesional.email', read_only=True,
    )
    profesional_nombre = serializers.CharField(source='profesional.persona.nombre', read_only=True)
    profesional_apellido = serializers.CharField(source='profesional.persona.apellido', read_only=True)

    class Meta:
        model = OperativoProfesional
        fields = [
            'id', 'operativo', 'profesional', 'profesional_email',
            'profesional_nombre', 'profesional_apellido',
            'rol_en_operativo', 'confirmado', 'observaciones',
        ]
        read_only_fields = ['id']


class OperativoListSerializer(serializers.ModelSerializer):
    escuela_nombre = serializers.CharField(source='escuela.nombre', read_only=True)
    cantidad_alumnos = serializers.SerializerMethodField()
    cantidad_profesionales = serializers.SerializerMethodField()

    class Meta:
        model = Operativo
        fields = [
            'id', 'nombre', 'escuela', 'escuela_nombre', 'fecha',
            'lugar_realizacion', 'estado',
            'cantidad_alumnos', 'cantidad_profesionales',
        ]

    def get_cantidad_alumnos(self, obj):
        return obj.alumnos.count()

    def get_cantidad_profesionales(self, obj):
        return obj.profesionales_asignados.count()


class OperativoDetailSerializer(serializers.ModelSerializer):
    profesionales_asignados = OperativoProfesionalSerializer(many=True, read_only=True)
    alumnos_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Operativo
        fields = [
            'id', 'nombre', 'escuela', 'fecha', 'lugar_realizacion',
            'estado', 'notas', 'created_by', 'created_at', 'updated_at',
            'profesionales_asignados', 'alumnos_count',
        ]
        read_only_fields = ['id', 'estado', 'created_by', 'created_at', 'updated_at']

    def get_alumnos_count(self, obj):
        return obj.alumnos.count()


class OperativoAlumnoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperativoAlumno
        fields = [
            'id', 'operativo', 'paciente', 'curso',
            'apellido', 'nombre', 'tipo_dni', 'dni',
            'fecha_nacimiento', 'sexo', 'estado', 'observaciones',
        ]
        read_only_fields = ['id', 'operativo']


class OperativoAlumnoEstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperativoAlumno
        fields = ['estado', 'observaciones']

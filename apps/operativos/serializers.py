from rest_framework import serializers
from .models import (
    Operativo, OperativoProfesional, OperativoAlumno,
    EvaluacionMedica, EvaluacionOdontologica,
)


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
    completo = serializers.BooleanField(read_only=True)
    medica_completada = serializers.SerializerMethodField(read_only=True)
    odontologica_completada = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OperativoAlumno
        fields = [
            'id', 'operativo', 'paciente', 'curso',
            'apellido', 'nombre', 'tipo_dni', 'dni',
            'fecha_nacimiento', 'sexo', 'estado', 'observaciones',
            'completo', 'medica_completada', 'odontologica_completada',
            'escuela_completado',
        ]
        read_only_fields = ['id', 'operativo']

    def get_medica_completada(self, obj):
        try:
            return obj.evaluacion_medica.completada
        except (OperativoAlumno.evaluacion_medica.RelatedObjectDoesNotExist, AttributeError):
            return False

    def get_odontologica_completada(self, obj):
        try:
            return obj.evaluacion_odontologica.completada
        except (OperativoAlumno.evaluacion_odontologica.RelatedObjectDoesNotExist, AttributeError):
            return False


class OperativoAlumnoEstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperativoAlumno
        fields = ['estado', 'observaciones']


class EvaluacionMedicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluacionMedica
        fields = [
            'id', 'operativo_alumno', 'profesional', 'fecha_evaluacion',
            'examen_realizado', 'motivo_no_examen', 'lugar_examen',
            'trajo_carnet', 'carnet_completo', 'vacunas_aplicadas', 'vacunas_indicadas',
            'peso', 'talla', 'imc', 'percentil_talla', 'percentil_imc',
            'pas', 'pad', 'presion_clasificacion',
            'agudeza_evaluada', 'ojo_derecho', 'ojo_izquierdo', 'usa_lentes',
            'audiometria_realizada', 'audiometria_resultado',
            'hallazgos', 'derivaciones',
            'completada',
        ]
        read_only_fields = ['id', 'operativo_alumno', 'profesional', 'fecha_evaluacion']


class EvaluacionOdontologicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluacionOdontologica
        fields = [
            'id', 'operativo_alumno', 'profesional', 'fecha_evaluacion',
            'salud_bucal', 'lesiones_tejidos_blandos', 'maloclusion',
            'fluorosis', 'caries', 'otros',
            'topicacion_fluor', 'ensenanza_cepillado', 'alta_basica',
            'cpo_c', 'cpo_p', 'cpo_o', 'ceo_c', 'ceo_e', 'ceo_o',
            'odontograma',
            'completada',
        ]
        read_only_fields = ['id', 'operativo_alumno', 'profesional', 'fecha_evaluacion']


class SeccionEscuelaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperativoAlumno
        fields = [
            'escuela_preocupa_salud', 'escuela_preocupa_detalle',
            'escuela_dificultad_lenguaje', 'escuela_bajo_tratamiento',
            'escuela_completado',
        ]

from rest_framework import serializers
from .models import (
    Operativo, OperativoProfesional, OperativoAlumno,
    EvaluacionMedica, EvaluacionOdontologica,
)

PIEZAS_PERMANENTES = {
    '18', '17', '16', '15', '14', '13', '12', '11',
    '21', '22', '23', '24', '25', '26', '27', '28',
    '48', '47', '46', '45', '44', '43', '42', '41',
    '31', '32', '33', '34', '35', '36', '37', '38',
}
PIEZAS_TEMPORARIAS = {
    '55', '54', '53', '52', '51', '61', '62', '63', '64', '65',
    '85', '84', '83', '82', '81', '71', '72', '73', '74', '75',
}
CARAS = {'oclusal', 'mesial', 'distal', 'vestibular', 'lingual'}
ESTADOS_GENERALES = {
    'ausente', 'perdido', 'extraido', 'corona', 'protesis', 'implante',
    'a_extraer', 'fractura_total',
}
ESTADOS_CARA = {
    'caries', 'restauracion', 'sellador', 'fractura', 'a_tratar', 'tratada',
}
ESTADOS_RAIZ = {'conducto_realizado', 'conducto_pendiente'}
ESTADOS_INCOMPATIBLES = {'ausente', 'perdido', 'extraido'}


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
    curso_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OperativoAlumno
        fields = [
            'id', 'operativo', 'paciente', 'curso', 'curso_display',
            'apellido', 'nombre', 'tipo_dni', 'dni',
            'fecha_nacimiento', 'sexo', 'estado', 'observaciones',
            'completo', 'medica_completada', 'odontologica_completada',
            'escuela_completado', 'antecedentes_completado',
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

    def get_curso_display(self, obj):
        if not obj.curso_id:
            return ''
        partes = [p for p in [obj.curso.sala_grado_anio, obj.curso.division] if p]
        return ' '.join(partes)


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
    def validate_odontograma(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('El odontograma debe ser un objeto.')

        piezas_validas = PIEZAS_PERMANENTES | PIEZAS_TEMPORARIAS
        for numero, pieza in value.items():
            numero = str(numero)
            if numero not in piezas_validas:
                raise serializers.ValidationError(f'Pieza dental inválida: {numero}.')
            if not isinstance(pieza, dict):
                raise serializers.ValidationError(f'La pieza {numero} debe ser un objeto.')

            denticion = pieza.get('denticion')
            denticion_esperada = (
                'permanente' if numero in PIEZAS_PERMANENTES else 'temporaria'
            )
            if denticion not in (None, denticion_esperada):
                raise serializers.ValidationError(
                    f'La pieza {numero} no pertenece a dentición {denticion_esperada}.'
                )

            general = pieza.get('estado_general') or ''
            if general and general not in ESTADOS_GENERALES:
                raise serializers.ValidationError(
                    f'Estado general inválido para la pieza {numero}.'
                )
            caras = pieza.get('caras') or {}
            if not isinstance(caras, dict) or set(caras) - CARAS:
                raise serializers.ValidationError(f'Caras inválidas para la pieza {numero}.')
            if general in ESTADOS_INCOMPATIBLES and caras:
                raise serializers.ValidationError(
                    f'La pieza {numero} no puede tener caras si está {general}.'
                )
            for cara, estado in caras.items():
                if estado and estado not in ESTADOS_CARA:
                    raise serializers.ValidationError(
                        f'Estado inválido en {numero}/{cara}.'
                    )
            raiz = pieza.get('raiz') or ''
            if general in ESTADOS_INCOMPATIBLES and raiz:
                raise serializers.ValidationError(
                    f'La pieza {numero} no puede tener estado de raíz si está {general}.'
                )
            if raiz and raiz not in ESTADOS_RAIZ:
                raise serializers.ValidationError(f'Estado de raíz inválido para la pieza {numero}.')
            if 'notas' in pieza and not isinstance(pieza['notas'], str):
                raise serializers.ValidationError(f'Las notas de la pieza {numero} deben ser texto.')
        return value

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

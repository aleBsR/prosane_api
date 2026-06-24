from django.db import models
from common.models import BaseModel


class EvaluacionMedica(BaseModel):
    """Evaluación clínica del médico por alumno (planilla PROSANE, equipo de salud)."""

    SI = 'si'
    NO = 'no'

    MOTIVO_CHOICES = [
        ('negativa_familiar', 'Negativa familiar'),
        ('negativa_nino', 'Negativa del niño/adolescente'),
        ('ausente', 'Ausente el día del examen'),
        ('otros', 'Otros'),
    ]
    LUGAR_CHOICES = [
        ('escuela', 'En la escuela'),
        ('centro_salud', 'En el centro de salud'),
    ]
    PERCENTIL_TALLA_CHOICES = [
        ('menor_3', 'Menor a 3'),
        ('mayor_igual_3', 'Mayor o igual a 3'),
    ]
    PERCENTIL_IMC_CHOICES = [
        ('menor_3', 'Menor a 3 (emaciación)'),
        ('entre_3_9', 'Entre 3 y 9 (riesgo de bajo peso)'),
        ('entre_10_84', 'Entre 10 y 84 (normal)'),
        ('entre_85_97', 'Entre 85 y 97 (sobrepeso)'),
        ('mayor_97', 'Mayor a 97 (obesidad)'),
    ]
    AUDIOMETRIA_CHOICES = [
        ('pasa', 'Pasa'),
        ('no_pasa', 'No pasa'),
    ]

    operativo_alumno = models.OneToOneField(
        'operativos.OperativoAlumno', on_delete=models.CASCADE,
        related_name='evaluacion_medica',
    )
    profesional = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='evaluaciones_medicas',
    )
    fecha_evaluacion = models.DateTimeField(null=True, blank=True)

    # Hoja 1 — examen clínico
    examen_realizado = models.BooleanField(default=False)
    motivo_no_examen = models.CharField(max_length=30, choices=MOTIVO_CHOICES, blank=True, default='')
    lugar_examen = models.CharField(max_length=20, choices=LUGAR_CHOICES, blank=True, default='')

    # Hoja 1 — vacunación
    trajo_carnet = models.BooleanField(default=False)
    carnet_completo = models.BooleanField(default=False)
    vacunas_aplicadas = models.TextField(blank=True, default='')
    vacunas_indicadas = models.TextField(blank=True, default='')

    # Hoja 2 — antropometría
    peso = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    talla = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    imc = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    percentil_talla = models.CharField(max_length=20, choices=PERCENTIL_TALLA_CHOICES, blank=True, default='')
    percentil_imc = models.CharField(max_length=20, choices=PERCENTIL_IMC_CHOICES, blank=True, default='')

    # Hoja 2 — presión arterial
    pas = models.IntegerField(null=True, blank=True)
    pad = models.IntegerField(null=True, blank=True)
    presion_clasificacion = models.CharField(max_length=30, blank=True, default='')

    # Hoja 2 — agudeza visual / audiometría
    agudeza_evaluada = models.BooleanField(default=False)
    ojo_derecho = models.CharField(max_length=10, blank=True, default='')
    ojo_izquierdo = models.CharField(max_length=10, blank=True, default='')
    usa_lentes = models.BooleanField(default=False)
    audiometria_realizada = models.BooleanField(default=False)
    audiometria_resultado = models.CharField(max_length=10, choices=AUDIOMETRIA_CHOICES, blank=True, default='')

    # Hoja 2 — hallazgos clínicos (11 sistemas) + derivaciones
    # hallazgos: {"piel": {"estado": "con|sin|no_eval", "detalle": "..."}, ...}
    hallazgos = models.JSONField(default=dict, blank=True)
    # derivaciones: {"odontologia": {"deriva": true, "motivo": "..."}, ...}
    derivaciones = models.JSONField(default=dict, blank=True)

    completada = models.BooleanField(default=False)

    class Meta:
        db_table = 'operativos_evaluaciones_medicas'
        verbose_name = 'evaluación médica'
        verbose_name_plural = 'evaluaciones médicas'

    def __str__(self):
        return f'Eval. médica de {self.operativo_alumno_id}'


class EvaluacionOdontologica(BaseModel):
    """Evaluación odontológica por alumno (planilla PROSANE, sección odontólogo)."""

    SALUD_BUCAL_CHOICES = [
        ('con_hallazgos', 'Con hallazgos'),
        ('sin_hallazgos', 'Sin hallazgos'),
        ('no_eval', 'No se evaluó'),
    ]

    operativo_alumno = models.OneToOneField(
        'operativos.OperativoAlumno', on_delete=models.CASCADE,
        related_name='evaluacion_odontologica',
    )
    profesional = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='evaluaciones_odontologicas',
    )
    fecha_evaluacion = models.DateTimeField(null=True, blank=True)

    salud_bucal = models.CharField(max_length=20, choices=SALUD_BUCAL_CHOICES, blank=True, default='')
    lesiones_tejidos_blandos = models.BooleanField(default=False)
    maloclusion = models.BooleanField(default=False)
    fluorosis = models.BooleanField(default=False)
    caries = models.BooleanField(default=False)
    otros = models.TextField(blank=True, default='')

    topicacion_fluor = models.BooleanField(default=False)
    ensenanza_cepillado = models.BooleanField(default=False)
    alta_basica = models.BooleanField(default=False)

    # Índice CPO (dientes permanentes) / ceo (dientes temporarios)
    cpo_c = models.IntegerField(null=True, blank=True)
    cpo_p = models.IntegerField(null=True, blank=True)
    cpo_o = models.IntegerField(null=True, blank=True)
    ceo_c = models.IntegerField(null=True, blank=True)
    ceo_e = models.IntegerField(null=True, blank=True)
    ceo_o = models.IntegerField(null=True, blank=True)

    # odontograma: {"18": "realizar|realizado|...", ...} por pieza dental
    odontograma = models.JSONField(default=dict, blank=True)

    completada = models.BooleanField(default=False)

    class Meta:
        db_table = 'operativos_evaluaciones_odontologicas'
        verbose_name = 'evaluación odontológica'
        verbose_name_plural = 'evaluaciones odontológicas'

    def __str__(self):
        return f'Eval. odontológica de {self.operativo_alumno_id}'

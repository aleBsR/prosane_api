from django.db import models
from common.models import BaseModel


class OperativoAlumno(BaseModel):
    PENDIENTE = 'pendiente'
    PRESENTE = 'presente'
    AUSENTE = 'ausente'
    EVALUADO = 'evaluado'

    ESTADO_CHOICES = [
        (PENDIENTE, 'Pendiente'),
        (PRESENTE, 'Presente'),
        (AUSENTE, 'Ausente'),
        (EVALUADO, 'Evaluado'),
    ]

    operativo = models.ForeignKey(
        'operativos.Operativo', on_delete=models.CASCADE, related_name='alumnos',
    )
    paciente = models.ForeignKey(
        'pacientes.Paciente', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='operativos_como_alumno',
    )
    curso = models.ForeignKey(
        'escuelas.Curso', on_delete=models.SET_NULL, null=True, blank=True,
    )

    # Snapshots del CSV
    apellido = models.CharField(max_length=200)
    nombre = models.CharField(max_length=200)
    tipo_dni = models.CharField(max_length=10, default='DNI')
    dni = models.CharField(max_length=15, db_index=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=10, blank=True, default='')

    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=PENDIENTE,
    )
    observaciones = models.TextField(blank=True, default='')

    # Sección ESCUELA (por alumno) — planilla PROSANE
    escuela_preocupa_salud = models.BooleanField(default=False)
    escuela_preocupa_detalle = models.TextField(blank=True, default='')
    escuela_dificultad_lenguaje = models.BooleanField(default=False)
    escuela_bajo_tratamiento = models.BooleanField(default=False)
    escuela_completado = models.BooleanField(default=False)
    antecedentes_completado = models.BooleanField(default=False)

    class Meta:
        db_table = 'operativos_alumnos'
        verbose_name = 'alumno en operativo'
        unique_together = ('operativo', 'dni')

    def __str__(self):
        return f'{self.apellido}, {self.nombre} (DNI: {self.dni})'

    @property
    def completo(self):
        """Indica si el alumno está completo a efectos de finalizar el operativo.

        - Si está ausente, no requiere evaluación → completo.
        - Si no, requiere evaluación médica completada, evaluación
          odontológica completada y la sección escuela completada.
        """
        if self.estado == self.AUSENTE:
            return True

        try:
            medica_ok = self.evaluacion_medica.completada
        except (OperativoAlumno.evaluacion_medica.RelatedObjectDoesNotExist, AttributeError):
            medica_ok = False

        try:
            odontologica_ok = self.evaluacion_odontologica.completada
        except (OperativoAlumno.evaluacion_odontologica.RelatedObjectDoesNotExist, AttributeError):
            odontologica_ok = False

        return bool(medica_ok and odontologica_ok and self.escuela_completado and self.antecedentes_completado)

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

    class Meta:
        db_table = 'operativos_alumnos'
        verbose_name = 'alumno en operativo'
        unique_together = ('operativo', 'dni')

    def __str__(self):
        return f'{self.apellido}, {self.nombre} (DNI: {self.dni})'

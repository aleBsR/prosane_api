from django.db import models
from common.models import BaseModel


class OperativoProfesional(BaseModel):
    ROL_CHOICES = [
        ('medico', 'Médico'),
        ('odontologo', 'Odontólogo'),
        ('ayudante', 'Ayudante'),
    ]

    operativo = models.ForeignKey(
        'operativos.Operativo', on_delete=models.CASCADE,
        related_name='profesionales_asignados',
    )
    profesional = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.CASCADE,
        related_name='operativos_asignados',
    )
    rol_en_operativo = models.CharField(max_length=20, choices=ROL_CHOICES)
    confirmado = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'operativos_profesionales'
        verbose_name = 'profesional en operativo'
        unique_together = ('operativo', 'profesional')

    def __str__(self):
        return f'{self.profesional.email} → {self.operativo}'

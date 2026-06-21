from django.db import models
from common.models import BaseModel


class Operativo(BaseModel):
    BORRADOR = 'borrador'
    CONFIRMADO = 'confirmado'
    EN_CURSO = 'en_curso'
    FINALIZADO = 'finalizado'
    CANCELADO = 'cancelado'

    ESTADO_CHOICES = [
        (BORRADOR, 'Borrador'),
        (CONFIRMADO, 'Confirmado'),
        (EN_CURSO, 'En curso'),
        (FINALIZADO, 'Finalizado'),
        (CANCELADO, 'Cancelado'),
    ]

    LUGAR_CHOICES = [
        ('escuela', 'En la escuela'),
        ('centro_salud', 'En el centro de salud'),
        ('otros', 'Otros'),
    ]

    nombre = models.CharField(max_length=200, blank=True, default='')
    escuela = models.ForeignKey(
        'escuelas.Escuela', on_delete=models.PROTECT, related_name='operativos',
    )
    fecha = models.DateField(db_index=True)
    lugar_realizacion = models.CharField(
        max_length=20, choices=LUGAR_CHOICES, default='escuela',
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=BORRADOR, db_index=True,
    )
    notas = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='operativos_creados',
    )

    class Meta:
        db_table = 'operativos'
        verbose_name = 'operativo'
        verbose_name_plural = 'operativos'
        ordering = ['-fecha', '-created_at']

    def __str__(self):
        return f'{self.nombre or self.escuela.nombre} - {self.fecha} ({self.get_estado_display()})'

from django.db import models
from common.models import BaseModel


class Curso(BaseModel):
    escuela = models.ForeignKey(
        'escuelas.Escuela', on_delete=models.CASCADE, related_name='cursos',
    )
    nivel = models.CharField(max_length=10, blank=True, default='')
    sala_grado_anio = models.CharField(max_length=20, blank=True, default='')
    division = models.CharField(max_length=10, blank=True, default='')
    ciclo_lectivo = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'cursos'
        verbose_name = 'curso'
        verbose_name_plural = 'cursos'

    def __str__(self):
        return f'{self.sala_grado_anio}{self.division} - {self.ciclo_lectivo or ""}'

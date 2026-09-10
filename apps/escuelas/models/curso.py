from django.core.exceptions import ValidationError
from django.db import models
from common.models import BaseModel


def normalizar_grado(valor):
    """Normaliza el grado para evitar duplicados por tipografía.

    - Quita espacios, unifica '1º'/'1ª' a '1°'.
    - Un número solo ('1') equivale a '1°' (autocompletado de la app).
    """
    import re

    if not valor:
        return valor or ''
    v = valor.strip().replace('º', '°').replace('ª', '°')
    if re.fullmatch(r'\d{1,2}', v):
        return f'{v}°'
    return v


def normalizar_division(valor):
    """Normaliza división: sin espacios y en mayúsculas ('a' == 'A')."""
    if not valor:
        return valor or ''
    return valor.strip().upper()


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
        constraints = [
            models.UniqueConstraint(
                fields=['escuela', 'sala_grado_anio', 'division', 'ciclo_lectivo'],
                name='uq_curso_escuela_grado_division_ciclo',
                nulls_distinct=False,
                condition=models.Q(deleted_at__isnull=True),
            ),
        ]

    def __str__(self):
        return f'{self.sala_grado_anio}{self.division} - {self.ciclo_lectivo or ""}'

    def clean(self):
        super().clean()
        if self.escuela_id is None:
            return
        qs = Curso.objects.filter(
            escuela_id=self.escuela_id,
            sala_grado_anio__iexact=normalizar_grado(self.sala_grado_anio),
            division__iexact=normalizar_division(self.division),
        )
        if self.ciclo_lectivo is not None:
            qs = qs.filter(
                models.Q(ciclo_lectivo=self.ciclo_lectivo)
                | models.Q(ciclo_lectivo__isnull=True)
            )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(
                'Ya existe un curso con ese grado, división y ciclo lectivo en esta escuela.'
            )

    def save(self, *args, **kwargs):
        self.sala_grado_anio = normalizar_grado(self.sala_grado_anio)
        self.division = normalizar_division(self.division)
        if isinstance(self.nivel, str):
            self.nivel = self.nivel.strip()
        super().save(*args, **kwargs)

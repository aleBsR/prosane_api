from django.db import models
from common.models import BaseModel


class Escuela(BaseModel):
    nombre = models.CharField(max_length=200)
    cue = models.CharField(max_length=20, unique=True, blank=True, null=True)
    ambito = models.CharField(max_length=20, blank=True, default='')
    sector_gestion = models.CharField(max_length=20, blank=True, default='')
    modalidad_educativa = models.CharField(max_length=50, blank=True, default='')
    intercultural_bilingue = models.BooleanField(default=False)
    plurigrado_rural = models.BooleanField(default=False)
    domicilio = models.ForeignKey(
        'personas.Domicilio', on_delete=models.SET_NULL, null=True, blank=True,
    )
    telefono = models.CharField(max_length=20, blank=True, default='')
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = 'escuelas'
        verbose_name = 'escuela'
        verbose_name_plural = 'escuelas'
        ordering = ['nombre']

    def __str__(self):
        cue_str = f' ({self.cue})' if self.cue else ''
        return f'{self.nombre}{cue_str}'

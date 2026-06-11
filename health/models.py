from django.db import models

from common.models import BaseModel


class Apto(BaseModel):
    """Apto físico (Constancia standalone). Borrador editable → firmado inmutable."""
    BORRADOR = 'borrador'
    FIRMADO = 'firmado'
    ESTADO_CHOICES = ((BORRADOR, 'borrador'), (FIRMADO, 'firmado'))

    paciente = models.ForeignKey('patients.Pacientes', models.PROTECT, related_name='aptos')
    profesional = models.ForeignKey('authentication.Usuarios', models.PROTECT, related_name='aptos_firmados')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=BORRADOR)

    # editable en borrador
    peso_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    altura_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    observaciones = models.TextField(blank=True, default='')

    # snapshots (se congelan al firmar)
    nna_dni = models.CharField(max_length=20, null=True, blank=True)
    nna_nombre_completo = models.CharField(max_length=200, null=True, blank=True)
    nna_edad = models.IntegerField(null=True, blank=True)
    profesional_nombre = models.CharField(max_length=200, null=True, blank=True)
    matricula_firmante = models.CharField(max_length=50, null=True, blank=True)

    # firma
    fecha_emision = models.DateField(null=True, blank=True)
    validez_hasta = models.DateField(null=True, blank=True)
    firma_hash = models.CharField(max_length=128, null=True, blank=True)
    timestamp_firma = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'aptos'

    @property
    def esta_firmado(self):
        return self.estado == self.FIRMADO

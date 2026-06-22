from django.db import models
from common.models import BaseModel


class Paciente(BaseModel):
    domicilio = models.ForeignKey(
        "personas.Domicilio",
        models.DO_NOTHING,
        db_column="id_domicilio",
    )
    tutor = models.ForeignKey(
        "tutores.Tutor",
        models.DO_NOTHING,
        db_column="id_responsable",
        null=True,
    )
    persona = models.ForeignKey(
        "personas.Persona",
        models.DO_NOTHING,
        db_column="id_persona",
    )
    edad = models.IntegerField()
    tiene_cud = models.CharField(max_length=2, blank=True, null=True)
    tipo_cobertura = models.CharField(max_length=20, blank=True, null=True)
    nombre_cobertura = models.CharField(max_length=20, blank=True, null=True)

    consentimiento_aceptado = models.BooleanField(default=False)
    fecha_consentimiento = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "pacientes"

    @property
    def adulto(self):
        """Adulto que firma el consentimiento: siempre es el tutor del paciente."""
        if self.tutor_id and self.tutor.persona:
            persona = self.tutor.persona
            return {
                "nombre": persona.nombre,
                "apellido": persona.apellido,
                "tipo_documento": persona.tipo_dni,
                "dni": persona.dni,
            }
        return None

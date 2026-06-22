from django.db import models
from common.models import BaseModel


class AntecedenteFamiliarTutor(BaseModel):
    SI_NO_NO_SABE_CHOICES = [
        ("si", "Sí"),
        ("no", "No"),
        ("no_sabe", "No sabe"),
    ]

    tutor = models.OneToOneField(
        "tutores.Tutor",
        on_delete=models.CASCADE,
        related_name="antecedente_familiar",
        db_column="id_tutor",
    )
    problema_salud_importante = models.CharField(
        max_length=10,
        choices=SI_NO_NO_SABE_CHOICES,
        blank=True,
        null=True,
    )
    problema_salud_cual = models.TextField(blank=True, null=True)
    muerte_subita_familiar = models.CharField(
        max_length=10,
        choices=SI_NO_NO_SABE_CHOICES,
        blank=True,
        null=True,
    )

    class Meta:
        managed = True
        db_table = "antecedentes_familiares_tutor"
        verbose_name = "antecedente familiar del tutor"
        verbose_name_plural = "antecedentes familiares del tutor"

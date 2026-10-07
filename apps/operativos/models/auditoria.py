from django.conf import settings
from django.db import models

from common.models import BaseModel


class AuditoriaDocumento(BaseModel):
    """Quién accedió/imprimió un documento con datos sensibles de salud.

    Respalda la leyenda de protección de datos impresa en planillas y
    constancias ("el acceso y la impresión quedan registrados y auditados",
    Leyes N° 25.326 y N° 26.529).
    """

    PLANILLA = "planilla"
    CONSTANCIA = "constancia"
    EXPORT_PDF = "export_pdf"
    EXPORT_EXCEL = "export_excel"
    EXPORT_CSV = "export_csv"

    TIPOS = (
        (PLANILLA, "Planilla por alumno"),
        (CONSTANCIA, "Constancia por alumno"),
        (EXPORT_PDF, "Exportación del operativo (PDF)"),
        (EXPORT_EXCEL, "Exportación del operativo (Excel)"),
        (EXPORT_CSV, "Exportación del operativo (CSV)"),
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_documentos",
        db_column="id_actor",
    )
    operativo = models.ForeignKey(
        "operativos.Operativo",
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_documentos",
        db_column="id_operativo",
    )
    alumno = models.ForeignKey(
        "operativos.OperativoAlumno",
        models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_documentos",
        db_column="id_alumno",
    )
    tipo = models.CharField(max_length=32)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "auditoria_documentos"

import io
from datetime import datetime

from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from .models import Operativo, OperativoAlumno


COLOR_PRIMARIO = HexColor('#6C5CE7')
COLOR_VERDE = HexColor('#00B894')
COLOR_GRIS = HexColor('#636E72')


def _safe(v, default='—'):
    if v is None or v == '':
        return default
    return str(v)


def generar_constancia_pdf(operativo: Operativo, alumno: OperativoAlumno) -> bytes:
    """Genera PDF de constancia por alumno (OperativoAlumno).

    Requiere operativo en estado FINALIZADO (validado por la vista).
    No realiza validación de permisos ni de estado — eso queda en la view.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f'Constancia PROSANE - {alumno.dni}',
    )

    styles = getSampleStyleSheet()
    s_title = ParagraphStyle('TitleCustom', parent=styles['Title'], textColor=COLOR_PRIMARIO, fontSize=18, alignment=TA_CENTER, spaceAfter=2)
    s_subtitle = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=9, textColor=COLOR_GRIS, alignment=TA_CENTER, spaceAfter=8)
    s_h1 = ParagraphStyle('H1', parent=styles['Heading2'], textColor=COLOR_PRIMARIO, fontSize=12, spaceBefore=10, spaceAfter=6, leading=14)
    s_h2 = ParagraphStyle('H2', parent=styles['Heading3'], textColor=HexColor('#2D3436'), fontSize=10, spaceBefore=6, spaceAfter=4)
    s_normal = ParagraphStyle('NormalCustom', parent=styles['Normal'], fontSize=9, leading=12, textColor=HexColor('#2D3436'))
    s_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=7, leading=9, textColor=COLOR_GRIS, alignment=TA_CENTER)
    s_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=10)
    s_cell_bold = ParagraphStyle('CellBold', parent=s_cell, fontName='Helvetica-Bold')

    story = []

    # Header
    story.append(Paragraph('PROSANE — Programa Nacional de Salud Escolar', s_title))
    story.append(Paragraph('Constancia de Control Integral de Salud', s_subtitle))
    story.append(HRFlowable(width='100%', thickness=1, color=COLOR_PRIMARIO, spaceAfter=8))

    # Info operativo
    story.append(Paragraph('Datos del operativo', s_h1))
    operativo_rows = [
        [Paragraph('<b>Operativo</b>', s_cell_bold), Paragraph(_safe(operativo.nombre or operativo.escuela.nombre), s_cell)],
        [Paragraph('<b>Escuela</b>', s_cell_bold), Paragraph(_safe(getattr(operativo.escuela, 'nombre', '')), s_cell)],
        [Paragraph('<b>CUE</b>', s_cell_bold), Paragraph(_safe(getattr(operativo.escuela, 'cue', '')), s_cell)],
        [Paragraph('<b>Fecha</b>', s_cell_bold), Paragraph(_safe(operativo.fecha), s_cell)],
        [Paragraph('<b>Lugar</b>', s_cell_bold), Paragraph(_safe(operativo.get_lugar_realizacion_display()), s_cell)],
        [Paragraph('<b>Estado</b>', s_cell_bold), Paragraph(_safe(operativo.get_estado_display()), s_cell)],
    ]
    t = Table(operativo_rows, colWidths=[38 * mm, 120 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#F8F9FA')),
        ('GRID', (0, 0), (-1, -1), 0.4, HexColor('#DFE6E9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    # Alumno
    story.append(Paragraph('Alumno', s_h1))
    curso_label = ''
    try:
        if alumno.curso:
            curso_label = f'{alumno.curso.sala_grado_anio or ""} {alumno.curso.division or ""}'.strip()
    except Exception:
        pass
    alumno_rows = [
        [Paragraph('<b>Apellido y nombre</b>', s_cell_bold), Paragraph(f"{_safe(alumno.apellido)} , {_safe(alumno.nombre)}", s_cell)],
        [Paragraph('<b>DNI</b>', s_cell_bold), Paragraph(f"{_safe(alumno.tipo_dni)} {_safe(alumno.dni)}", s_cell)],
        [Paragraph('<b>Fecha nac.</b>', s_cell_bold), Paragraph(_safe(alumno.fecha_nacimiento), s_cell)],
        [Paragraph('<b>Sexo</b>', s_cell_bold), Paragraph(_safe(alumno.sexo), s_cell)],
        [Paragraph('<b>Curso</b>', s_cell_bold), Paragraph(_safe(curso_label, default='Sin curso'), s_cell)],
        [Paragraph('<b>Estado en operativo</b>', s_cell_bold), Paragraph(_safe(alumno.get_estado_display()), s_cell)],
    ]
    t2 = Table(alumno_rows, colWidths=[38 * mm, 120 * mm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#F8F9FA')),
        ('GRID', (0, 0), (-1, -1), 0.4, HexColor('#DFE6E9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t2)

    # Evaluación médica
    try:
        med = alumno.evaluacion_medica
    except Exception:
        med = None

    story.append(Paragraph('Evaluación médica', s_h1))
    if alumno.estado == OperativoAlumno.AUSENTE:
        story.append(Paragraph('Alumno ausente el día del operativo — no se realizó evaluación.', s_normal))
    elif med is None or not med.completada:
        story.append(Paragraph('Evaluación médica no registrada o incompleta.', s_normal))
    else:
        # Antropometría
        story.append(Paragraph('Antropometría y signos vitales', s_h2))
        antro_rows = [
            [Paragraph('<b>Peso</b>', s_cell_bold), Paragraph(_safe(med.peso, '—') + (' kg' if med.peso else ''), s_cell),
             Paragraph('<b>Talla</b>', s_cell_bold), Paragraph(_safe(med.talla, '—') + (' cm' if med.talla else ''), s_cell)],
            [Paragraph('<b>IMC</b>', s_cell_bold), Paragraph(_safe(med.imc), s_cell),
             Paragraph('<b>Percentil IMC</b>', s_cell_bold), Paragraph(_safe(med.percentil_imc), s_cell)],
            [Paragraph('<b>Percentil talla</b>', s_cell_bold), Paragraph(_safe(med.percentil_talla), s_cell),
             Paragraph('<b>Presión (PAS/PAD)</b>', s_cell_bold), Paragraph(f"{_safe(med.pas, '—')}/{_safe(med.pad, '—')}  {_safe(med.presion_clasificacion, '')}", s_cell)],
        ]
        t3 = Table(antro_rows, colWidths=[28 * mm, 50 * mm, 32 * mm, 48 * mm])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#F8F9FA')),
            ('BACKGROUND', (2, 0), (2, -1), HexColor('#F8F9FA')),
            ('GRID', (0, 0), (-1, -1), 0.4, HexColor('#DFE6E9')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t3)

        # Vacunación
        story.append(Paragraph('Vacunación', s_h2))
        story.append(Paragraph(f"Trajo carnet: <b>{'Sí' if med.trajo_carnet else 'No'}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Carnet completo: <b>{'Sí' if med.carnet_completo else 'No'}</b>", s_normal))
        if med.vacunas_aplicadas:
            story.append(Paragraph(f"<b>Vacunas aplicadas:</b> {_safe(med.vacunas_aplicadas)}", s_normal))
        if med.vacunas_indicadas:
            story.append(Paragraph(f"<b>Vacunas indicadas:</b> {_safe(med.vacunas_indicadas)}", s_normal))

        # Hallazgos y derivaciones (resumen)
        if med.hallazgos:
            story.append(Paragraph('Hallazgos clínicos', s_h2))
            for sistema, val in med.hallazgos.items():
                if isinstance(val, dict):
                    estado = _safe(val.get('estado'))
                    detalle = _safe(val.get('detalle'), '')
                    if estado and estado != '—':
                        txt = f"<b>{sistema}:</b> {estado}"
                        if detalle and detalle != '—':
                            txt += f" — {detalle}"
                        story.append(Paragraph(txt, s_normal))
        if med.derivaciones:
            deriv_list = [k for k, v in med.derivaciones.items() if isinstance(v, dict) and v.get('deriva')]
            if deriv_list:
                story.append(Paragraph('Derivaciones indicadas', s_h2))
                for esp in deriv_list:
                    motivo = ''
                    try:
                        motivo = med.derivaciones[esp].get('motivo', '')
                    except Exception:
                        pass
                    txt = f"• {esp}"
                    if motivo:
                        txt += f" — {motivo}"
                    story.append(Paragraph(txt, s_normal))

        # Agudeza / audiometría
        story.append(Paragraph('Screening sensorial', s_h2))
        story.append(Paragraph(f"Agudeza evaluada: <b>{'Sí' if med.agudeza_evaluada else 'No'}</b> &nbsp; OD: {_safe(med.ojo_derecho)} &nbsp; OI: {_safe(med.ojo_izquierdo)} &nbsp; Usa lentes: <b>{'Sí' if med.usa_lentes else 'No'}</b>", s_normal))
        story.append(Paragraph(f"Audiometría realizada: <b>{'Sí' if med.audiometria_realizada else 'No'}</b> &nbsp; Resultado: {_safe(med.audiometria_resultado)}", s_normal))

    # Evaluación odontológica
    try:
        odonto = alumno.evaluacion_odontologica
    except Exception:
        odonto = None

    story.append(Paragraph('Evaluación odontológica', s_h1))
    if alumno.estado == OperativoAlumno.AUSENTE:
        story.append(Paragraph('Alumno ausente — no evaluado.', s_normal))
    elif odonto is None or not odonto.completada:
        story.append(Paragraph('Evaluación odontológica no registrada o incompleta.', s_normal))
    else:
        story.append(Paragraph(f"Salud bucal: <b>{_safe(odonto.salud_bucal)}</b>", s_normal))
        flags = []
        if odonto.lesiones_tejidos_blandos:
            flags.append('lesiones tejidos blandos')
        if odonto.maloclusion:
            flags.append('maloclusión')
        if odonto.fluorosis:
            flags.append('fluorosis')
        if odonto.caries:
            flags.append('caries')
        if flags:
            story.append(Paragraph('<b>Hallazgos:</b> ' + ', '.join(flags), s_normal))
        if odonto.otros:
            story.append(Paragraph(f"<b>Otros:</b> {_safe(odonto.otros)}", s_normal))
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"CPO: C:{_safe(odonto.cpo_c, '—')}  P:{_safe(odonto.cpo_p, '—')}  O:{_safe(odonto.cpo_o, '—')} &nbsp;&nbsp;|&nbsp;&nbsp; ceo: c:{_safe(odonto.ceo_c, '—')}  e:{_safe(odonto.ceo_e, '—')}  o:{_safe(odonto.ceo_o, '—')}", s_normal))
        pract = []
        if odonto.topicacion_fluor:
            pract.append('topicación flúor')
        if odonto.ensenanza_cepillado:
            pract.append('enseñanza cepillado')
        if odonto.alta_basica:
            pract.append('alta básica')
        if pract:
            story.append(Paragraph('<b>Prácticas:</b> ' + ', '.join(pract), s_normal))

    # Sección escuela
    story.append(Paragraph('Sección escuela', s_h1))
    story.append(Paragraph(f"Preocupación por salud: <b>{'Sí' if alumno.escuela_preocupa_salud else 'No'}</b>" + (f" — {_safe(alumno.escuela_preocupa_detalle)}" if alumno.escuela_preocupa_detalle else ""), s_normal))
    story.append(Paragraph(f"Dificultad en el lenguaje: <b>{'Sí' if alumno.escuela_dificultad_lenguaje else 'No'}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Bajo tratamiento: <b>{'Sí' if alumno.escuela_bajo_tratamiento else 'No'}</b>", s_normal))

    # Footer
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width='100%', thickness=0.6, color=HexColor('#DFE6E9'), spaceAfter=6))
    ahora = timezone.now().strftime('%d/%m/%Y %H:%M')
    story.append(Paragraph(f"Constancia generada el {ahora} — Operativo {operativo.id} — Alumno {alumno.id} — PROSANE Salta", s_small))
    story.append(Paragraph("Documento informativo — no reemplaza la historia clínica. Validación con DNI y fecha de operativo.", s_small))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

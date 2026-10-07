"""Mapea la planilla oficial en papel (planilla_2025.pdf) a coordenadas.

Lee palabras y rectángulos vectoriales con PyMuPDF (origen arriba-izq.,
puntos, página 612x1008) y genera planilla_mapa.json con:
  - boxes: {id: [page, x0, y0, x1, y1]}  casillas a marcar con X
  - texts: {id: [page, x, y_base, size]} puntos de inserción de valores
  - teeth: {num: [page, cx, cy]}         centros de piezas del odontograma
  - scales: {od_1/10: [page, cx, cy]}    centros de números de escala visual

Uso:  python mapear.py   (corre desde esta carpeta)
Requiere: pymupdf
"""

import json
import unicodedata
from pathlib import Path

import pymupdf

BASE = Path(__file__).parent
PDF = BASE / 'planilla_2025.pdf'
OUT = BASE / 'planilla_mapa.json'


def norm(s):
    s = (s or '').replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return s.lower().strip()


def norm_word(s):
    return norm(s).strip('"«»“”.,:;()¿?¡!')


class Pg:
    def __init__(self, page, idx):
        self.page = page
        self.idx = idx
        self.words = []
        for x0, y0, x1, y1, text, *_ in page.get_text('words'):
            t = text.strip()
            if not t:
                continue
            self.words.append({
                'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
                'cx': (x0 + x1) / 2, 'cy': (y0 + y1) / 2, 'text': t,
            })
        self.boxes = []
        for g in page.get_drawings():
            if g.get('type') not in ('s', 'fs'):
                continue
            r = g['rect']
            w, h = r.width, r.height
            if 4.5 <= w <= 11 and 4.5 <= h <= 10:
                self.boxes.append({
                    'x0': r.x0, 'y0': r.y0, 'x1': r.x1, 'y1': r.y1,
                    'cx': (r.x0 + r.x1) / 2, 'cy': (r.y0 + r.y1) / 2,
                })

    def find(self, sub, y=None, tol=7, occ=0, xmin=-1, xmax=1e9):
        """N-ésima palabra que empieza con sub (normalizado)."""
        key = norm_word(sub)
        cands = [w for w in self.words
                 if norm_word(w['text']).startswith(key) and xmin <= w['x0'] <= xmax]
        if y is not None:
            cands = [w for w in cands if abs(w['cy'] - y) <= tol]
        cands.sort(key=lambda w: (round(w['cy']), w['x0']))
        if occ >= len(cands):
            return None
        return cands[occ]


BOXES = {}
TEXTS = {}
TEETH = {}
SCALES = {}
WARN = []


def put_box(fid, page_idx, rect):
    BOXES[fid] = [page_idx, round(rect['x0'], 1), round(rect['y0'], 1),
                  round(rect['x1'], 1), round(rect['y1'], 1)]


def put_text(fid, page_idx, x, y_base, size=8.5, align='l'):
    e = [page_idx, round(x, 1), round(y_base, 1), size]
    if align == 'c':
        e.append('c')
    TEXTS[fid] = e


def box_left(pg, word, max_gap=20, y_tol=8.0):
    if word is None:
        return None
    cands = [b for b in pg.boxes
             if b['x1'] <= word['x0'] + 1.5
             and abs(b['cy'] - word['cy']) <= y_tol
             and word['x0'] - b['x1'] <= max_gap]
    if not cands:
        return None
    return min(cands, key=lambda b: word['x0'] - b['x1'])


def box_right(pg, word, max_gap=20, y_tol=8.0):
    if word is None:
        return None
    cands = [b for b in pg.boxes
             if b['x0'] >= word['x1'] - 1.5
             and abs(b['cy'] - word['cy']) <= y_tol
             and b['x0'] - word['x1'] <= max_gap]
    if not cands:
        return None
    return min(cands, key=lambda b: b['x0'] - word['x1'])


def opt(pg, fid, sub, y, side='left', occ=0, tol=7, xmin=-1, xmax=1e9):
    w = pg.find(sub, y, tol, occ, xmin, xmax)
    if w is None:
        WARN.append(f'{fid}: palabra no encontrada ({sub!r} y={y})')
        return None
    b = box_left(pg, w) if side == 'left' else box_right(pg, w)
    if b is None:
        WARN.append(f'{fid}: casilla no encontrada ({w["text"]!r} y={y})')
        return None
    put_box(fid, pg.idx, b)
    return b


def row_boxes(pg, fid_prefix, y, n, x_min, tol=6.5):
    cands = sorted(
        [b for b in pg.boxes if abs(b['cy'] - y) <= tol and b['x0'] >= x_min],
        key=lambda b: b['x0'],
    )
    if len(cands) < n:
        WARN.append(f'{fid_prefix}: hay {len(cands)} casillas, se pedían {n} (y={y})')
    for b, suf in zip(cands[-n:], ('_si', '_no', '_ns')[:n]):
        put_box(f'{fid_prefix}{suf}', pg.idx, b)
    return cands[-n:]


def val_after(pg, fid, sub, y, occ=0, dx=3.0, size=8.5, tol=7):
    w = pg.find(sub, y, tol, occ)
    if w is None:
        WARN.append(f'{fid}: etiqueta no encontrada ({sub!r} y={y})')
        return None
    put_text(fid, pg.idx, w['x1'] + dx, w['y1'] - 2.0, size)
    return w


def _letra(pg, fid, letra, y, tol=7):
    """Posición de una letra suelta (para subrayar, ej. Sexo F/M)."""
    cands = [w for w in pg.words
             if norm_word(w['text']) == norm(letra) and abs(w['cy'] - y) <= tol]
    if not cands:
        WARN.append(f'{fid}: letra no encontrada ({letra!r} y={y})')
        return None
    w = sorted(cands, key=lambda w: w['x0'])[0]
    put_text(fid, pg.idx, w['x0'], w['y1'] - 2.0, 8.5)
    return w


def main():
    doc = pymupdf.open(PDF)
    p1 = Pg(doc[0], 0)
    p2 = Pg(doc[1], 1)
    print(f'P1: {len(p1.words)} palabras, {len(p1.boxes)} casillas')
    print(f'P2: {len(p2.words)} palabras, {len(p2.boxes)} casillas')

    # ══ P1: encabezado (fecha partida en 3 segmentos) ══
    put_text('t_fex_d', 0, 537.0, 70.0, 8.5, 'c')
    put_text('t_fex_m', 0, 551.5, 70.0, 8.5, 'c')
    put_text('t_fex_a', 0, 574.0, 70.0, 8, 'c')
    val_after(p1, 't_consent_nino', 'adolescente)', 129, occ=0, size=8)
    val_after(p1, 't_tutor_nom', 'responsable:', 152, occ=0)
    val_after(p1, 't_tutor_tipodoc', 'responsable:', 165, occ=0)
    val_after(p1, 't_tutor_doc', 'documento:', 165, occ=1)

    # ══ P1: datos niño ══
    val_after(p1, 't_nino_nom', 'adolescente:', 218, occ=0)
    for fid, sub, occ in [('t_dom_calle', 'Calle', 0), ('t_dom_nro', 'N°', 0),
                          ('t_dom_piso', 'Piso', 0), ('t_dom_dpto', 'Dpto.', 0),
                          ('t_dom_manzana', 'Manzana', 0), ('t_dom_casa', 'Casa', 0),
                          ('t_dom_nrocasa', 'N°', 1), ('t_dom_pieza', 'Pieza', 0)]:
        val_after(p1, fid, sub, 228, occ=occ, dx=2.0, size=8)
    val_after(p1, 't_provincia', 'Provincia:', 238, occ=0, dx=2.0, size=8)
    val_after(p1, 't_departamento', 'Departamento:', 238, occ=0, dx=2.0, size=8)
    val_after(p1, 't_localidad', 'Localidad:', 238, occ=0, dx=2.0, size=8)
    val_after(p1, 't_tel_fijo', 'ﬁjo:', 248, occ=0, dx=2.0, size=8)
    val_after(p1, 't_celular', 'Celular:', 248, occ=0, dx=2.0, size=8)
    val_after(p1, 't_tipodoc', 'documento:', 258, occ=0, dx=2.0, size=8)
    val_after(p1, 't_numdoc', 'documento:', 258, occ=1, dx=2.0, size=8)
    # Sexo no tiene casillas: se subraya la letra (ver renderer).
    _letra(p1, 't_sexo_f', 'F', 258)
    _letra(p1, 't_sexo_m', 'M', 258)
    # Fecha de nacimiento partida en 3 segmentos punteados
    put_text('t_fnac_d', 0, 138.0, 272.7, 8.5, 'c')
    put_text('t_fnac_m', 0, 172.0, 272.7, 8.5, 'c')
    put_text('t_fnac_a', 0, 212.0, 272.7, 8.5, 'c')
    val_after(p1, 't_edad', 'años):', 269, occ=0, dx=2.0, size=8)
    opt(p1, 'bx_cud_si', 'SI', 269, side='right')
    opt(p1, 'bx_cud_no', 'NO', 269, side='right')
    opt(p1, 'bx_cob_obra', 'Obra', 293)
    opt(p1, 'bx_cob_estatal', 'Programas', 305)
    opt(p1, 'bx_cob_privada', 'Plan', 317, occ=0)
    opt(p1, 'bx_cob_ninguna', 'No', 317, occ=0)
    opt(p1, 'bx_nivel_inicial', 'Inicial', 302)
    val_after(p1, 't_nivel_sala', 'Sala:', 302, occ=0, dx=2.0, size=8)
    opt(p1, 'bx_nivel_primario', 'Primario', 314)
    val_after(p1, 't_nivel_grado', 'Grado:', 314, occ=0, dx=2.0, size=8)
    opt(p1, 'bx_nivel_secundario', 'Secundario', 326)
    val_after(p1, 't_nivel_anio', 'Año:', 326, occ=0, dx=2.0, size=8)

    # ══ P1: antecedentes (prematurez con triple rotulado; resto pelado) ══
    opt(p1, 'bx_prematuro_si', 'Sí', 341, occ=0)
    opt(p1, 'bx_prematuro_no', 'No', 341, occ=0)
    opt(p1, 'bx_prematuro_ns', 'No', 341, occ=1)
    val_after(p1, 't_peso_nac', '(kg.):', 341, occ=0, dx=7.0, size=8)
    for fid, y in [('bx_convulsiones', 352), ('bx_mareos', 372),
                   ('bx_itu', 383), ('bx_asma', 394), ('bx_tbc', 405),
                   ('bx_diabetes', 416), ('bx_hta', 427),
                   ('bx_cardiopatia', 438), ('bx_trauma', 449),
                   ('bx_diarrea', 460), ('bx_oido', 471),
                   ('bx_internado', 482)]:
        row_boxes(p1, fid, y, 3, 440)
    val_after(p1, 't_causa_intern', 'Causa', 492, occ=0, dx=2.0, size=8)
    row_boxes(p1, 'bx_tratamiento', 503, 3, 440)
    val_after(p1, 't_cual_trat', '¿Cuál?', 513, occ=0, dx=2.0, size=8)
    val_after(p1, 't_preocupa_fam', 'preocupa?', 524, occ=0, dx=2.0, size=8)
    val_after(p1, 't_que_preocupa_fam', 'preocupa?', 535, occ=0, dx=2.0, size=8)
    opt(p1, 'bx_ult_menos', 'Hace', 556, occ=0)
    opt(p1, 'bx_ult_mas', 'Hace', 556, occ=1)
    opt(p1, 'bx_ult_norec', 'No', 556, occ=0)
    val_after(p1, 't_otro_prob_cual', '¿Cuál?', 578, occ=0, dx=2.0, size=8)
    opt(p1, 'bx_men_si', 'Sí', 590, occ=0)
    opt(p1, 'bx_men_no', 'No', 590, occ=0)
    opt(p1, 'bx_men_ns', 'No', 590, occ=1)
    val_after(p1, 't_men_edad', 'Edad:', 590, occ=0, dx=2.0, size=8)

    # ══ P1: familia + escuela ══
    opt(p1, 'bx_fam_si', 'Sí', 613, occ=0)
    opt(p1, 'bx_fam_no', 'No', 613, occ=0)
    opt(p1, 'bx_fam_ns', 'No', 613, occ=1)
    val_after(p1, 't_fam_cual', '¿Cuál/es?', 613, occ=0, dx=2.0, size=8)
    opt(p1, 'bx_ms_si', 'Sí', 625, occ=0)
    opt(p1, 'bx_ms_no', 'No', 625, occ=0)
    opt(p1, 'bx_ms_ns', 'No', 625, occ=1)
    val_after(p1, 't_escuela_nom', 'escuela:', 660, occ=0)
    opt(p1, 'bx_amb_rural', 'Rural', 686)
    opt(p1, 'bx_amb_urbana', 'Urbana', 697)
    opt(p1, 'bx_sec_estatal', 'Estatal', 686)
    opt(p1, 'bx_sec_privado', 'Privado', 686)
    opt(p1, 'bx_sec_social', 'Social', 697)
    opt(p1, 'bx_mod_comun', 'Común', 685)
    opt(p1, 'bx_mod_especial', 'Especial', 696)
    opt(p1, 'bx_inter_si', 'Sí', 675, occ=0)
    opt(p1, 'bx_inter_no', 'No', 675, occ=0)
    opt(p1, 'bx_pluri_si', 'Sí', 687, occ=0)
    opt(p1, 'bx_pluri_no', 'No', 687, occ=0)
    opt(p1, 'bx_esc_preoc_si', 'Sí', 709, occ=0)
    opt(p1, 'bx_esc_preoc_no', 'No', 709, occ=0)
    val_after(p1, 't_esc_preocupa', 'preocupa?', 709, occ=1, dx=2.0, size=8)
    opt(p1, 'bx_leng_si', 'Sí', 720, occ=0)
    opt(p1, 'bx_leng_no', 'No', 720, occ=0)
    opt(p1, 'bx_trat_si', 'Sí', 720, occ=1)
    opt(p1, 'bx_trat_no', 'No', 720, occ=1)
    opt(p1, 'bx_trat_ns', 'sabe', 720, occ=0)

    # ══ P1: equipo salud + vacunas ══
    val_after(p1, 't_prof_nom', 'profesional:', 758, occ=0)
    val_after(p1, 't_prof_mat', 'N°', 772, occ=0, dx=3.0, size=8)
    opt(p1, 'bx_ex_si', 'Sí', 784, occ=0)
    opt(p1, 'bx_ex_no', 'No', 796, occ=0)
    opt(p1, 'bx_lugar_esc', 'En', 785, occ=0)
    opt(p1, 'bx_lugar_centro', 'En', 785, occ=1)
    opt(p1, 'bx_mot_fam', 'Negativa', 797, occ=0)
    opt(p1, 'bx_mot_aus', 'Ausente', 797, occ=0)
    opt(p1, 'bx_mot_nino', 'Negativa', 809, occ=0)
    opt(p1, 'bx_mot_otros', 'Otros', 809, occ=0)
    opt(p1, 'bx_carnet_si', 'Sí', 833, occ=0)
    opt(p1, 'bx_carnet_no', 'No', 833, occ=0)
    opt(p1, 'bx_completo_si', 'Sí', 846, occ=0)
    # (carnet completo no tiene casilla "No": se expresa con aplicadas/indicadas)
    opt(p1, 'bx_aplic_si', 'Sí', 853, occ=0, xmin=200)
    opt(p1, 'bx_aplic_no', 'No', 857, occ=0)
    val_after(p1, 't_aplic_cuales', 'Cuáles:', 853, occ=0, dx=2.0, size=8)
    opt(p1, 'bx_indic_si', 'Sí', 874, occ=0)
    opt(p1, 'bx_indic_no', 'No', 883, occ=0)
    val_after(p1, 't_indic_cuales', 'Cuáles:', 873, occ=0, dx=2.0, size=8)
    # Fecha constancia (cabecera p1) partida en 3 segmentos
    put_text('t_fexc_d', 0, 537.0, 971.5, 8.5, 'c')
    put_text('t_fexc_m', 0, 551.5, 971.5, 8.5, 'c')
    put_text('t_fexc_a', 0, 574.0, 971.5, 8, 'c')

    # ══ P2: antropometría / PA / visual / audio ══
    opt(p2, 'bx_ant_si', 'Se', 61, occ=0)
    opt(p2, 'bx_ant_no', 'No', 73, occ=0)
    # Peso/talla/IMC van dentro de las cajas grises, después de la unidad
    val_after(p2, 't_peso', '(kg.):', 61, occ=0, dx=3.0, size=9)
    val_after(p2, 't_talla', '(cm.):', 73, occ=0, dx=3.0, size=9)
    val_after(p2, 't_imc', 'IMC:', 85, occ=0, dx=2.0, size=8)
    opt(p2, 'bx_pt_menor', 'Menor', 60, occ=0)
    opt(p2, 'bx_pt_mayor', 'Mayor', 60, occ=0)
    opt(p2, 'bx_pi_menor', 'Menor', 72, occ=0)
    opt(p2, 'bx_pi_3_9', 'Entre', 84, occ=0)
    opt(p2, 'bx_pi_10_84', 'Entre', 84, occ=1)
    opt(p2, 'bx_pi_85_97', 'Entre', 95, occ=0)
    opt(p2, 'bx_pi_mayor', 'Mayor', 95, occ=0)
    opt(p2, 'bx_pa_si', 'Se', 110, occ=0)
    opt(p2, 'bx_pa_no', 'No', 121, occ=0)
    # (el grupo etario <16/≥16 no tiene casillas: se deduce de la edad)
    opt(p2, 'bx_pas_a', 'PC', 133, occ=0, xmax=370)
    opt(p2, 'bx_pas_b', 'PC', 133, occ=1, xmax=370)
    opt(p2, 'bx_pas_c', 'Menor', 142, occ=0, xmax=370)
    opt(p2, 'bx_pas_d', 'Mayor', 142, occ=1, xmax=370)
    opt(p2, 'bx_pad_a', 'PC', 134, occ=0, xmin=380)
    opt(p2, 'bx_pad_b', 'PC', 134, occ=1, xmin=380)
    opt(p2, 'bx_pad_c', 'Menor', 143, occ=0, xmin=380)
    opt(p2, 'bx_pad_d', 'Mayor', 143, occ=0, xmin=380)
    val_after(p2, 't_pas_valor', '(PAS):', 110, occ=0, dx=2.0, size=8)
    val_after(p2, 't_pad_valor', '(PAD):', 111, occ=0, dx=2.0, size=8)
    opt(p2, 'bx_vis_si', 'Se', 157, occ=0)
    opt(p2, 'bx_vis_no', 'No', 168, occ=0)
    opt(p2, 'bx_len_si', 'Sí', 181, occ=0)
    opt(p2, 'bx_len_no', 'No', 181, occ=0)
    _scales(p2)
    val_after(p2, 't_od_valor', 'derecho', 168, occ=0, dx=2.0, size=7)
    val_after(p2, 't_oi_valor', 'izquierdo', 168, occ=0, dx=2.0, size=7)
    opt(p2, 'bx_aud_hecha_no', 'No', 178, occ=0)
    opt(p2, 'bx_aud_hecha_si', 'Sí', 186, occ=0)
    opt(p2, 'bx_aud_pasa', 'Pasa', 186, occ=0)
    opt(p2, 'bx_aud_nopasa', 'No', 195, occ=0)
    _sistemas(p2)

    # ══ P2: odonto ══
    val_after(p2, 't_odo_prof', 'profesional:', 671, occ=0)
    # Fecha examen odonto partida en 3 segmentos
    put_text('t_ofecha_d', 1, 132.5, 687.4, 8.5, 'c')
    put_text('t_ofecha_m', 1, 155.0, 687.4, 8.5, 'c')
    put_text('t_ofecha_a', 1, 186.0, 687.4, 8.5, 'c')
    opt(p2, 'bx_sb_con', 'Con', 699, occ=0)
    opt(p2, 'bx_sb_sin', 'Sin', 710, occ=0)
    opt(p2, 'bx_sb_no', 'No', 721, occ=0)
    opt(p2, 'bx_lesiones', 'Lesiones', 699, occ=0)
    opt(p2, 'bx_maloclusion', 'Maloclusión', 719, occ=0)
    opt(p2, 'bx_fluorosis', 'Fluorosis', 730, occ=0)
    opt(p2, 'bx_caries', 'Caries', 741, occ=0)
    opt(p2, 'bx_odo_otros', 'Otros:', 752, occ=0)
    val_after(p2, 't_odo_otros', 'Otros:', 752, occ=0, dx=2.0, size=8)
    # CPO/ceo: la plantilla trae DOS casillas por fila (mayúscula a la
    # izquierda, minúscula a la derecha). Rectángulos vectoriales reales
    # extraídos de la plantilla (las medidas anteriores caían sobre la letra).
    for fid, (x0, y0, x1, y1) in [
        ('bx_cpo_C', (301.2, 720.0, 307.7, 726.0)),
        ('bx_cpo_P', (301.2, 730.0, 307.7, 735.9)),
        ('bx_cpo_O', (301.2, 740.2, 307.7, 746.2)),
        ('bx_cpo_c', (326.0, 720.0, 332.5, 726.0)),
        ('bx_cpo_e', (326.0, 730.0, 332.5, 735.9)),
        ('bx_cpo_o', (326.0, 740.2, 332.5, 746.2)),
    ]:
        put_box(fid, p2.idx, {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1})
    opt(p2, 'bx_top_si', 'Sí', 732, occ=0)
    opt(p2, 'bx_top_no', 'No', 732, occ=0)
    opt(p2, 'bx_cep_si', 'Sí', 749, occ=0)
    opt(p2, 'bx_cep_no', 'No', 749, occ=0)
    opt(p2, 'bx_alta_si', 'Sí', 761, occ=0)
    opt(p2, 'bx_alta_no', 'No', 761, occ=0)
    _teeth(p2)

    # ══ P2: derivaciones ══
    _derivaciones(p2)

    # ══ P2: constancia (posiciones fijas sobre los punteados) ══
    put_text('t_const_nom', 1, 118.0, 914.5, 8.5)
    put_text('t_const_dni', 1, 52.0, 924.8, 8.5)
    put_text('t_const_edad', 1, 148.0, 924.8, 8.5)
    val_after(p2, 't_const_obs', 'Observaciones:', 943, occ=0, dx=2.0, size=8)
    opt(p2, 'bx_cv_completas', 'Presenta', 967, occ=0)
    opt(p2, 'bx_cv_curso', 'Presenta', 977, occ=0)
    opt(p2, 'bx_cv_debe', 'Debe', 987, occ=0)
    val_after(p2, 't_const_peso', 'Peso:', 977, occ=0, dx=7.0, size=8)
    val_after(p2, 't_const_talla', 'Altura:', 987, occ=0, dx=7.0, size=8)
    # Fecha constancia sobre la línea punteada, partida en 3
    put_text('t_const_d', 1, 388.0, 981.0, 8, 'c')
    put_text('t_const_m', 1, 411.0, 981.0, 8, 'c')
    put_text('t_const_a', 1, 438.0, 981.0, 8, 'c')

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'boxes': BOXES, 'texts': TEXTS,
                   'teeth': TEETH}, f, ensure_ascii=False)
    print(f'boxes={len(BOXES)} texts={len(TEXTS)} teeth={len(TEETH)}')
    rep = '\n'.join(WARN)
    Path(str(OUT) + '.warn.txt').write_text(
        f'WARN ({len(WARN)}):\n{rep}\n', encoding='utf-8')
    print(f'WARN ({len(WARN)}), detalle en planilla_mapa.json.warn.txt')


def _scales(pg):
    """Cada número de escala tiene su casilla a la izquierda: se marca con X."""
    od = {'1/10': 205, '2/10': 205, '3/10': 205, '4/10': 238,
          '5/10': 238, '6/10': 238, '7/10': 272, '8/10': 272,
          '9/10': 272, '10/10': 272}
    oi = {'1/10': 312, '2/10': 312, '3/10': 312, '4/10': 345,
          '5/10': 345, '6/10': 345, '7/10': 379, '8/10': 379,
          '9/10': 379, '10/10': 379}
    for side, xs in (('od', od), ('oi', oi)):
        for v, x in xs.items():
            cands = [w for w in pg.words
                     if norm_word(w['text']) == norm(v) and abs(w['x0'] - x) <= 14]
            if not cands:
                WARN.append(f'scale {side} {v}: número no encontrado (x={x})')
                continue
            w = sorted(cands, key=lambda w: abs(w['x0'] - x))[0]
            b = box_left(pg, w)
            if b is None:
                WARN.append(f'scale {side} {v}: casilla no encontrada')
                continue
            put_box(f'bx_vis_{side}_{v}', pg.idx, b)


ESTADOS = [('con', 'Con'), ('sin', 'Sin'), ('no_eval', 'No')]
SISTEMA_YS = {
    'piel': 225, 'partes_blandas': 263, 'cardiovascular': 298,
    'respiratorio': 333, 'abdominal': 367, 'genitourinario_ninos': 402,
    'genitourinario_ninas': 440, 'osteoarticular': 475, 'neurologico': 511,
    'salud_visual': 546, 'salud_fonoaudiologica': 582, 'icv': 618,
}
ESTADO_DY = {'con': 0, 'sin': 10, 'no_eval': 21}

CHECKS = {
    'piel': [('nevo_derivacion', 'Nevos'), ('escabiosis', 'Escabiosis'),
             ('piodermitis', 'Piodermitis'), ('pediculosis', 'Pediculosis'),
             ('otro_piel', 'Otros:')],
    'partes_blandas': [('adenomegalia_localizada', 'Adenomegalia'),
                       ('adenomegalias_generalizada', 'Ademomegalias'),
                       ('otro_partes', 'Otros:')],
    'cardiovascular': [('presion_elevada', 'Presión'), ('pulso_alterado', 'Ausencia'),
                       ('soplo', 'Soplo'), ('arritmia', 'Arritmia'),
                       ('otro_cardio', 'Otros:')],
    'respiratorio': [('hallazgo_auscultatorio', 'Hallazgos'),
                     ('respiracion_bucal', 'Respiración'),
                     ('otro_resp', 'Otros:')],
    'abdominal': [('hepatomegalia', 'Hepatomegalía'),
                  ('masa_palpable', 'Masa'), ('esplenomegalia', 'Esplenomegalia'),
                  ('hernias', 'Hernias'), ('otro_abd', 'Otros:')],
    'genitourinario_ninos': [('pubertad_precoz', 'Signos'),
                             ('testiculo_no_descendido', 'Testículo/s'),
                             ('hernia', 'Hernia'), ('fimosis', 'Fimosis'),
                             ('asimetria_testicular', 'Asimetría'),
                             ('varicocele', 'Varicocele'),
                             ('otro_gn', 'Otros:')],
    'genitourinario_ninas': [('pubertad_precoz', 'Signos'),
                             ('otro_gn', 'Otros:')],
    'osteoarticular': [('adams_positiva', 'Maniobra'),
                       ('alteracion_marcha', 'Alteraciones'),
                       ('otro_osteo', 'Otros:')],
    'neurologico': [('paresias_focales', 'Paresias'),
                    ('movimientos_anormales', 'Movimientos'),
                    ('otro_neuro', 'Otros:')],
    'icv': [],
    'salud_visual': [('disminucion_agudeza', 'Disminución'),
                     ('estrabismo', 'Estrabismo'),
                     ('posicion_cabeza', 'Posición'),
                     ('ojo_externo', 'Alteraciones'),
                     ('otro_vis', 'Otros:')],
    'salud_fonoaudiologica': [('audiometria_no_pasa', 'pasa'),
                              ('alteracion_lenguaje', 'Alteraciones'),
                              ('otro_fono', 'Otros:')],
}


def _sistemas(pg):
    for sistema, y0 in SISTEMA_YS.items():
        for suf, sub in ESTADOS:
            opt(pg, f'bx_{sistema}_{suf}', sub, y0 + ESTADO_DY[suf], occ=0)
        for cid, sub in CHECKS.get(sistema, []):
            _check(pg, sistema, cid, sub)


def _check(pg, sistema, cid, sub):
    y0 = SISTEMA_YS[sistema]
    key = norm_word(sub)
    cands = [w for w in pg.words
             if norm_word(w['text']).startswith(key)
             and y0 - 2 <= w['cy'] <= y0 + 24 and w['x0'] > 200]
    if not cands:
        WARN.append(f'bx_{sistema}_{cid}: check no encontrado ({sub!r})')
        return
    w = sorted(cands, key=lambda w: (w['cy'], w['x0']))[0]
    b = box_left(pg, w) or box_right(pg, w)
    if b is None:
        WARN.append(f'bx_{sistema}_{cid}: casilla no encontrada ({w["text"]!r})')
        return
    put_box(f'bx_{sistema}_{cid}', pg.idx, b)
    if norm(sub).rstrip(':') in ('otros', 'otro'):
        put_text(f't_{sistema}_{cid}', pg.idx,
                 max(w['x1'], b['x1']) + 3.0, w['y1'] - 2.0, 7.5)


# Geometría del odontograma calibrada sobre el raster (pt, origen arriba-izq).
# 4 filas de formas; por lado: 8 piezas (permanentes) o 5 (temporarias).
TEETH_COLS = {
    'perm_l': [399.3, 410.8, 422.3, 433.9, 445.3, 456.9, 468.4, 479.8],
    'perm_r': [499.5, 510.9, 522.4, 534.0, 545.5, 556.9, 568.5, 579.8],
    'temp_l': [434.0, 445.4, 456.9, 468.5, 479.8],
    'temp_r': [499.5, 510.9, 522.4, 534.0, 545.3],
}
TEETH_ROWS = {'perm_sup': 681.0, 'perm_inf': 695.8,
              'temp_sup': 737.5, 'temp_inf': 753.9}
TEETH_SEQS = {
    ('perm_sup', 'perm_l'): ['18', '17', '16', '15', '14', '13', '12', '11'],
    ('perm_sup', 'perm_r'): ['21', '22', '23', '24', '25', '26', '27', '28'],
    ('perm_inf', 'perm_l'): ['48', '47', '46', '45', '44', '43', '42', '41'],
    ('perm_inf', 'perm_r'): ['31', '32', '33', '34', '35', '36', '37', '38'],
    ('temp_sup', 'temp_l'): ['55', '54', '53', '52', '51'],
    ('temp_sup', 'temp_r'): ['61', '62', '63', '64', '65'],
    ('temp_inf', 'temp_l'): ['85', '84', '83', '82', '81'],
    ('temp_inf', 'temp_r'): ['71', '72', '73', '74', '75'],
}


def _teeth(pg):
    for (row, side), seq in TEETH_SEQS.items():
        key = {'perm_l': 'perm_l', 'perm_r': 'perm_r',
               'temp_l': 'temp_l', 'temp_r': 'temp_r'}[side]
        cols = TEETH_COLS[key]
        cy = TEETH_ROWS[row]
        for num, cx in zip(seq, cols):
            TEETH[num] = [pg.idx, round(cx, 1), round(cy, 1)]


DERIV_YS_LEFT = [809, 819, 830, 840, 850, 860, 870, 880, 890]
DERIV_IDS_LEFT = ['odontologia', 'oftalmologia', 'nutricion', 'vacunatorio',
                  'pediatria', 'fonoaudiologia', 'cardiologia',
                  'traumatologia', 'cirugia']
DERIV_YS_RIGHT = [810, 820, 830, 840, 850, 860, 870, 880, 890]
DERIV_IDS_RIGHT = ['urologia', 'orl', 'dermatologia', 'neurologia',
                   'trabajo_social', 'psicologia', 'psicopedagogia',
                   'agente_sanitario', 'otros']


def _derivaciones(pg):
    for y, esp in zip(DERIV_YS_LEFT, DERIV_IDS_LEFT):
        _deriv_row(pg, esp, y, 0, 250)
    for y, esp in zip(DERIV_YS_RIGHT, DERIV_IDS_RIGHT):
        _deriv_row(pg, esp, y, 280, 600)


def _deriv_row(pg, esp, y, xmin, xmax):
    words = [w for w in pg.words
             if abs(w['cy'] - y) <= 6 and xmin <= w['x0'] <= xmax]
    si = next((w for w in words if norm_word(w['text']) == 'si'), None)
    no = next((w for w in words if norm_word(w['text']) == 'no'), None)
    mot = next((w for w in words if norm_word(w['text']).startswith('motivo')), None)
    for fid, w in [(f'bx_deriv_{esp}_si', si), (f'bx_deriv_{esp}_no', no)]:
        if w is None:
            WARN.append(f'{fid}: palabra no encontrada (y={y})')
            continue
        b = box_left(pg, w)
        if b is None:
            WARN.append(f'{fid}: casilla no encontrada')
            continue
        put_box(fid, pg.idx, b)
    if mot is None:
        WARN.append(f't_deriv_{esp}: Motivo no encontrado (y={y})')
    else:
        put_text(f't_deriv_{esp}', pg.idx, mot['x1'] + 3.0, mot['y1'] - 2.0, 8)


if __name__ == '__main__':
    main()

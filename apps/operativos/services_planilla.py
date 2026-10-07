"""Planilla PROSANE por alumno con formato idéntico al papel.

Motor: la plantilla oficial (planilla_base/planilla_2025.pdf, 2 hojas oficio)
se usa como fondo y encima se estampan X en casillas y valores en líneas,
según el mapa planilla_base/planilla_mapa.json (generado con mapear.py).

Requiere operativo en estado FINALIZADO (validado por la vista).
"""

import io
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor, black
from reportlab.pdfgen import canvas

from .models import Operativo, OperativoAlumno

BASE = Path(__file__).parent / 'planilla_base'
TEMPLATE = BASE / 'planilla_2025.pdf'
MAPA = BASE / 'planilla_mapa.json'

PAGE_W, PAGE_H = 612.0, 1008.0

AZUL = HexColor('#1E63D0')  # tratamientos a realizar
ROJO = HexColor('#D32F2F')  # tratamientos realizados
GRIS = HexColor('#757575')

with open(MAPA, encoding='utf-8') as _f:
    _MAP = json.load(_f)
_BX = _MAP['boxes']
_TX = _MAP['texts']
_TEETH = _MAP['teeth']

BLOQ_PIEZA = {'ausente', 'perdido', 'extraido'}
CARAS_REALIZAR = {'caries', 'fractura', 'a_tratar'}
CARAS_HECHO = {'restauracion', 'sellador', 'tratada'}


# ──────────────────────────────────────────────
#  Datos
# ──────────────────────────────────────────────
def _g(obj, attr, default=None):
    return getattr(obj, attr, default) if obj is not None else default


def _fecha(d):
    try:
        return d.strftime('%d/%m/%Y') if d else ''
    except Exception:
        return str(d or '')


_SI = {'SI', 'SÍ', 'S', 'YES', '1', 'TRUE', 'VERDADERO', 'V'}
_NO = {'NO', 'N', '0', 'FALSE', 'FALSO'}
_NS = {'NO SABE', 'NOSABE', 'N/S', 'NS', 'NO SE', 'DESCONOCE', 'DESCONOCIDO'}


def _sn3(raw):
    """Devuelve (si, no, ns, detalle). Texto libre no-opción → Sí + detalle."""
    t = str(raw or '').strip().upper()
    if t in ('', '—', '-', 'NINGUNO', 'NINGUNA'):
        return False, False, False, ''
    if t in _SI:
        return True, False, False, ''
    if t in _NO:
        return False, True, False, ''
    if t in _NS:
        return False, False, True, ''
    return True, False, False, str(raw).strip()


def _cobertura(tipo):
    t = str(tipo or '').lower()
    out = {'privada': False, 'obra': False, 'estatal': False, 'ninguna': False}
    if any(k in t for k in ('privad', 'prepaga')):
        out['privada'] = True
    elif any(k in t for k in ('obra', 'pami')):
        out['obra'] = True
    elif any(k in t for k in ('sumar', 'asignaci', 'estatal', 'programa')):
        out['estatal'] = True
    elif any(k in t for k in ('no tiene', 'ningun', 'sin cobertura')):
        out['ninguna'] = True
    return out


def _contiene(valor, *claves):
    t = str(valor or '').lower()
    return any(k in t for k in claves)


def _prof_repr(usuario):
    if usuario is None:
        return '', ''
    try:
        from apps.profesionales.models import Profesional
        p = Profesional.objects.filter(id_usuario=usuario).first()
        if p is None:
            return getattr(usuario, 'email', '') or '', ''
        nombre = f"{p.nombre or ''} {p.apellido or ''}".strip() or getattr(usuario, 'email', '')
        return nombre or '', p.matricula or ''
    except Exception:
        return '', ''


def _juntar(operativo, alumno):
    escuela = getattr(operativo, 'escuela', None)
    curso = getattr(alumno, 'curso', None)
    curso_label = ''
    nivel = ''
    try:
        if curso:
            curso_label = f"{curso.sala_grado_anio or ''} {curso.division or ''}".strip()
            nivel = str(curso.nivel or '')
    except Exception:
        pass
    try:
        med = alumno.evaluacion_medica
    except Exception:
        med = None
    try:
        odo = alumno.evaluacion_odontologica
    except Exception:
        odo = None
    paciente = getattr(alumno, 'paciente', None)
    persona = getattr(paciente, 'persona', None) if paciente else None
    domicilio = getattr(paciente, 'domicilio', None) if paciente else None
    tutor = getattr(paciente, 'tutor', None) if paciente else None
    tutor_persona = getattr(tutor, 'persona', None) if tutor else None
    ant_p = ant_f = ant_ft = None
    if paciente is not None:
        try:
            from apps.antecedentes.models import AntecedenteFamiliar, AntecedentePersonal
            ant_p = AntecedentePersonal.objects.filter(paciente=paciente).first()
            ant_f = AntecedenteFamiliar.objects.filter(paciente=paciente).first()
        except Exception:
            pass
    if tutor is not None:
        try:
            from apps.antecedentes.models import AntecedenteFamiliarTutor
            ant_ft = AntecedenteFamiliarTutor.objects.filter(tutor=tutor).first()
        except Exception:
            pass
    fnac = getattr(persona, 'fecha_nacimiento', None) or getattr(alumno, 'fecha_nacimiento', None)
    edad = getattr(paciente, 'edad', None) if paciente else None
    try:
        fop = getattr(operativo, 'fecha', None)
        if fnac and fop:
            edad = fop.year - fnac.year - ((fop.month, fop.day) < (fnac.month, fnac.day))
    except Exception:
        pass
    return {
        'operativo': operativo, 'escuela': escuela, 'curso_label': curso_label,
        'nivel': nivel, 'alumno': alumno, 'med': med, 'odo': odo,
        'paciente': paciente, 'persona': persona, 'domicilio': domicilio,
        'tutor_persona': tutor_persona, 'ant_p': ant_p, 'ant_f': ant_f,
        'ant_ft': ant_ft, 'edad': edad, 'fnac': fnac,
    }


def _estado_diente(p):
    if isinstance(p, str):
        t = p.strip().lower()
        if t in BLOQ_PIEZA:
            return 'gris'
        if t in ('', 'sano', 'sana', 'normal', 'no'):
            return ''
        return 'rojo'
    eg = str((p or {}).get('estado_general') or '')
    caras = (p or {}).get('caras') or {}
    raiz = str((p or {}).get('raiz') or '')
    if eg in BLOQ_PIEZA:
        return 'gris'
    vals = [str(v) for v in caras.values() if v]
    if eg in ('a_extraer', 'fractura_total') or any(v in CARAS_REALIZAR for v in vals) or raiz == 'conducto_pendiente':
        return 'azul'
    if eg or any(v in CARAS_HECHO for v in vals) or raiz == 'conducto_realizado':
        return 'rojo'
    return ''


# ──────────────────────────────────────────────
#  Overlay sobre la plantilla
# ──────────────────────────────────────────────
class _Overlay:
    def __init__(self):
        self.marks = set()
        self.texts = {}
        self.teeth = {}

    def marcar(self, *ids):
        for i in ids:
            if i in _BX:
                self.marks.add(i)

    def texto(self, fid, valor):
        if fid in _TX and valor not in (None, ''):
            s = str(valor).strip()
            if s:
                self.texts[fid] = s

    def sn3(self, prefijo, si=False, no=False, ns=False):
        if si:
            self.marcar(f'{prefijo}_si')
        elif no:
            self.marcar(f'{prefijo}_no')
        elif ns:
            self.marcar(f'{prefijo}_ns')

    def par(self, prefijo, si):
        self.marcar(f'{prefijo}_{"si" if si else "no"}')


def _fecha3(o, prefijo, valor_fecha):
    """Parte dd/mm/aaaa en tres textos centrados (ids prefijo_d/m/a)."""
    try:
        dd, mm, aa = _fecha(valor_fecha).split('/')
        o.texto(f'{prefijo}_d', dd)
        o.texto(f'{prefijo}_m', mm)
        o.texto(f'{prefijo}_a', aa)
    except Exception:
        pass


def _armar_overlay(d):
    o = _Overlay()
    op, al, med, odo = d['operativo'], d['alumno'], d['med'], d['odo']
    pac, per, dom = d['paciente'], d['persona'], d['domicilio']
    ant = d['ant_p']
    es_ausente = getattr(al, 'estado', '') == OperativoAlumno.AUSENTE

    snap_nom = f"{_g(al, 'apellido', '') or ''}, {_g(al, 'nombre', '') or ''}".strip(' ,')
    if per is not None:
        nom_ape = f"{_g(per, 'apellido', '') or ''}, {_g(per, 'nombre', '') or ''}".strip(' ,') or snap_nom
    else:
        nom_ape = snap_nom
    dni = _g(per, 'dni', None) or _g(al, 'dni', '')

    # Encabezado + consentimiento
    _fecha3(o, 't_fex', _g(op, 'fecha', None))
    _fecha3(o, 't_fexc', _g(op, 'fecha', None))
    o.texto('t_consent_nino', nom_ape)
    tp = d['tutor_persona']
    o.texto('t_tutor_nom', f"{_g(tp, 'nombre', '') or ''} {_g(tp, 'apellido', '') or ''}".strip())
    o.texto('t_tutor_tipodoc', _g(tp, 'tipo_dni', ''))
    o.texto('t_tutor_doc', _g(tp, 'dni', ''))

    # Datos niño
    o.texto('t_nino_nom', nom_ape)
    if dom is not None:
        o.texto('t_dom_calle', _g(dom, 'calle', ''))
        o.texto('t_dom_nro', _g(dom, 'nro_calle', ''))
        o.texto('t_dom_piso', _g(dom, 'piso', ''))
        o.texto('t_dom_dpto', _g(dom, 'dpto', ''))
        o.texto('t_dom_manzana', _g(dom, 'manzana', ''))
        o.texto('t_dom_casa', f"{_g(dom, 'casa', '') or ''} {_g(dom, 'nro_casa', '') or ''}".strip())
        o.texto('t_dom_pieza', _g(dom, 'pieza', ''))
        o.texto('t_provincia', _g(dom, 'provincia', ''))
        o.texto('t_departamento', _g(dom, 'departamento', ''))
        o.texto('t_localidad', _g(dom, 'localidad', ''))
    o.texto('t_tel_fijo', _g(pac, 'telefono_fijo', ''))
    o.texto('t_celular', _g(pac, 'celular', ''))
    o.texto('t_tipodoc', _g(per, 'tipo_dni', None) or _g(al, 'tipo_dni', ''))
    o.texto('t_numdoc', dni)
    o.texts['t_sexo'] = 'F'  # placeholder, se resuelve abajo
    sexo = str(_g(per, 'sexo', None) or _g(al, 'sexo', '') or '').upper()
    o.texts['t_sexo'] = 't_sexo_f' if sexo.startswith('F') else ('t_sexo_m' if sexo.startswith('M') else '')
    _fecha3(o, 't_fnac', d['fnac'])
    o.texto('t_edad', d['edad'] if d['edad'] is not None else '')
    cud = str(_g(pac, 'tiene_cud', '') or '').upper()
    if cud in ('SI', 'SÍ', 'S', '1'):
        o.marcar('bx_cud_si')
    elif cud in ('NO', 'N', '0'):
        o.marcar('bx_cud_no')
    cob = _cobertura(_g(pac, 'tipo_cobertura', ''))
    for k in ('privada', 'obra', 'estatal', 'ninguna'):
        if cob[k]:
            o.marcar(f'bx_cob_{k}')
    o.texto('t_nivel_sala', d['curso_label'] if 'inicial' in d['nivel'].lower() else '')
    o.texto('t_nivel_grado', d['curso_label'] if 'primar' in d['nivel'].lower() else '')
    o.texto('t_nivel_anio', d['curso_label'] if 'secund' in d['nivel'].lower() else '')
    niv = d['nivel'].lower()
    if 'inicial' in niv:
        o.marcar('bx_nivel_inicial')
    elif 'primar' in niv:
        o.marcar('bx_nivel_primario')
    elif 'secund' in niv:
        o.marcar('bx_nivel_secundario')

    # Antecedentes personales
    si, no, ns, _det = _sn3(_g(ant, 'nacio_prematuro', ''))
    o.sn3('bx_prematuro', si, no, ns)
    o.texto('t_peso_nac', _g(ant, 'peso_nacimiento', ''))
    for attr, pref in [('convulsiones_epilepsia', 'bx_convulsiones'),
                       ('mareos_desmayos', 'bx_mareos'),
                       ('infecciones_urinarias', 'bx_itu'),
                       ('asma_espasmos', 'bx_asma'),
                       ('tuberculosis', 'bx_tbc'),
                       ('diabetes', 'bx_diabetes'),
                       ('hipertension', 'bx_hta'),
                       ('cardiopatia_congenita', 'bx_cardiopatia'),
                       ('traumatismo_internacion', 'bx_trauma'),
                       ('diarrea_frecuente', 'bx_diarrea'),
                       ('infecciones_oido', 'bx_oido')]:
        si, no, ns, det = _sn3(_g(ant, attr, ''))
        o.sn3(pref, si, no, ns)
    causa = str(_g(ant, 'causa_hospitalizacion', '') or '').strip()
    if causa and causa.upper() not in ('NO', 'NINGUNA', 'NINGUNO', '-', '—'):
        o.sn3('bx_internado', True, False, False)
        o.texto('t_causa_intern', causa)
    else:
        si, no, ns, _d = _sn3(_g(ant, 'internacion_previa', ''))
        o.sn3('bx_internado', si, no, ns)
    desc = str(_g(ant, 'descripcion_tratamiento', '') or '').strip()
    if desc and desc.upper() not in ('NO', 'NINGUNO', 'NINGUNA'):
        o.sn3('bx_tratamiento', True, False, False)
        o.texto('t_cual_trat', desc)
    else:
        si, no, ns, _d = _sn3(_g(ant, 'tratamiento_actual', ''))
        o.sn3('bx_tratamiento', si, no, ns)
    ult = str(_g(ant, 'ultima_consulta_medica', '') or '')
    t = ult.lower()
    o.marcar('bx_ult_menos' if ('menos de 1' in t or 'menos de un' in t)
             else 'bx_ult_mas' if (('más de 1' in t or 'mas de 1' in t) and 'menos' not in t)
             else 'bx_ult_norec' if ('recuerda' in t or 'no sabe' in t) else '')
    o.marks.discard('')
    otro_prob = str(_g(ant, 'otros_problemas_salud', '') or '')
    if otro_prob and otro_prob.upper() not in ('NINGUNO', 'NINGUNA', 'NO'):
        o.texto('t_otro_prob_cual', otro_prob)
    si, no, ns, _d = _sn3(_g(ant, 'primera_menstruacion', ''))
    o.sn3('bx_men', si, no, ns)
    edad_men = _g(ant, 'edad_primera_menstruacion', 0) or 0
    o.texto('t_men_edad', '' if not edad_men else edad_men)

    # Familia
    fam_prob = _g(d['ant_f'], 'problemas_salud', '') or _g(d['ant_ft'], 'problema_salud_importante', '')
    fam_cual = _g(d['ant_f'], 'detalle_problema_salud', '') or _g(d['ant_ft'], 'problema_salud_cual', '')
    fam_ms = _g(d['ant_f'], 'familiar_con_muerte_subita', '') or _g(d['ant_ft'], 'muerte_subita_familiar', '')
    si, no, ns, _d = _sn3(fam_prob)
    o.sn3('bx_fam', si, no, ns)
    if str(fam_cual or '').strip().upper() not in ('', 'NO', 'NINGUNO'):
        o.texto('t_fam_cual', fam_cual)
    si, no, ns, _d = _sn3(fam_ms)
    o.sn3('bx_ms', si, no, ns)

    # Escuela
    esc = d['escuela']
    o.texto('t_escuela_nom', _g(esc, 'nombre', ''))
    if _contiene(_g(esc, 'ambito', ''), 'rur'):
        o.marcar('bx_amb_rural')
    elif _contiene(_g(esc, 'ambito', ''), 'urb'):
        o.marcar('bx_amb_urbana')
    if _contiene(_g(esc, 'sector_gestion', ''), 'estatal'):
        o.marcar('bx_sec_estatal')
    elif _contiene(_g(esc, 'sector_gestion', ''), 'privad'):
        o.marcar('bx_sec_privado')
    elif _contiene(_g(esc, 'sector_gestion', ''), 'social', 'coop'):
        o.marcar('bx_sec_social')
    if _contiene(_g(esc, 'modalidad_educativa', ''), 'comun', 'común'):
        o.marcar('bx_mod_comun')
    elif _contiene(_g(esc, 'modalidad_educativa', ''), 'especial'):
        o.marcar('bx_mod_especial')
    if esc is not None:
        o.marcar('bx_inter_si' if _g(esc, 'intercultural_bilingue', False) else 'bx_inter_no')
        o.marcar('bx_pluri_si' if _g(esc, 'plurigrado_rural', False) else 'bx_pluri_no')
    o.par('bx_esc_preoc', bool(_g(al, 'escuela_preocupa_salud', False)))
    o.texto('t_esc_preocupa', _g(al, 'escuela_preocupa_detalle', ''))
    o.par('bx_leng', bool(_g(al, 'escuela_dificultad_lenguaje', False)))
    o.par('bx_trat', bool(_g(al, 'escuela_bajo_tratamiento', False)))

    # Equipo de salud
    med_prof_nom, med_prof_mat = _prof_repr(_g(med, 'profesional', None))
    o.texto('t_prof_nom', med_prof_nom)
    o.texto('t_prof_mat', med_prof_mat)
    motivo = str(_g(med, 'motivo_no_examen', '') or '')
    if es_ausente:
        motivo = 'ausente'
    o.par('bx_ex', bool(_g(med, 'examen_realizado', False)) and not es_ausente)
    _MOT = {'negativa_familiar': 'bx_mot_fam', 'ausente': 'bx_mot_aus',
            'negativa_nino': 'bx_mot_nino', 'otros': 'bx_mot_otros'}
    if motivo in _MOT:
        o.marcar(_MOT[motivo])
    lugar = str(_g(med, 'lugar_examen', '') or '')
    if lugar == 'escuela':
        o.marcar('bx_lugar_esc')
    elif lugar == 'centro_salud':
        o.marcar('bx_lugar_centro')

    # Vacunación
    o.par('bx_carnet', bool(_g(med, 'trajo_carnet', False)))
    if _g(med, 'carnet_completo', False):
        o.marcar('bx_completo_si')
    ap = str(_g(med, 'vacunas_aplicadas', '') or '').strip()
    o.par('bx_aplic', bool(ap))
    o.texto('t_aplic_cuales', ap)
    ind = str(_g(med, 'vacunas_indicadas', '') or '').strip()
    o.par('bx_indic', bool(ind))
    o.texto('t_indic_cuales', ind)

    # Antropometría / PA / visual / audio
    o.par('bx_ant', bool(_g(med, 'antropometria_evaluada', False)))
    o.texto('t_peso', _g(med, 'peso', ''))
    o.texto('t_talla', _g(med, 'talla', ''))
    o.texto('t_imc', _g(med, 'imc', ''))
    pt = str(_g(med, 'percentil_talla', '') or '')
    o.marcar('bx_pt_menor' if pt == 'menor_3' else 'bx_pt_mayor' if pt == 'mayor_igual_3' else '')
    o.marks.discard('')
    pi = str(_g(med, 'percentil_imc', '') or '')
    _PI = {'menor_3': 'bx_pi_menor', 'entre_3_9': 'bx_pi_3_9',
           'entre_10_84': 'bx_pi_10_84', 'entre_85_97': 'bx_pi_85_97',
           'mayor_97': 'bx_pi_mayor'}
    if pi in _PI:
        o.marcar(_PI[pi])
    o.par('bx_pa', bool(_g(med, 'presion_evaluada', False)))
    o.texto('t_pas_valor', _g(med, 'pas', ''))
    o.texto('t_pad_valor', _g(med, 'pad', ''))
    pas, pad = _g(med, 'pas', None), _g(med, 'pad', None)
    try:
        menor16 = d['edad'] is not None and int(d['edad']) < 16
    except Exception:
        menor16 = False
    if pas is not None and pad is not None and bool(_g(med, 'presion_evaluada', False)):
        try:
            if menor16:
                o.marcar('bx_pas_a' if float(pas) < 90 else 'bx_pas_b')
                o.marcar('bx_pad_a' if float(pad) < 90 else 'bx_pad_b')
            else:
                o.marcar('bx_pas_c' if float(pas) < 130 else 'bx_pas_d')
                o.marcar('bx_pad_c' if float(pad) < 80 else 'bx_pad_d')
        except Exception:
            pass
    o.par('bx_vis', bool(_g(med, 'agudeza_evaluada', False)))
    for lado, val in (('od', _g(med, 'ojo_derecho', '')), ('oi', _g(med, 'ojo_izquierdo', ''))):
        v = str(val or '').strip()
        key = f'bx_vis_{lado}_{v}'
        if v and key in _BX:
            o.marcar(key)
        else:
            o.texto(f't_{lado}_valor', v)
    o.par('bx_len', bool(_g(med, 'usa_lentes', False)))
    o.par('bx_aud_hecha', bool(_g(med, 'audiometria_realizada', False)))
    res_a = str(_g(med, 'audiometria_resultado', '') or '')
    if bool(_g(med, 'audiometria_realizada', False)):
        if res_a == 'pasa':
            o.marcar('bx_aud_pasa')
        elif res_a == 'no_pasa':
            o.marcar('bx_aud_nopasa')

    # Hallazgos
    hall = _g(med, 'hallazgos', None) or {}
    _EST = {'con': 'con', 'sin': 'sin', 'no_eval': 'no_eval'}
    for sistema in ('piel', 'partes_blandas', 'cardiovascular', 'respiratorio',
                    'abdominal', 'genitourinario_ninos', 'genitourinario_ninas',
                    'osteoarticular', 'neurologico', 'icv', 'salud_visual',
                    'salud_fonoaudiologica'):
        val = hall.get(sistema) if isinstance(hall, dict) else None
        if not isinstance(val, dict):
            continue
        est = _EST.get(str(val.get('estado') or ''))
        if est:
            o.marcar(f'bx_{sistema}_{est}')
        checks = val.get('checks') if isinstance(val.get('checks'), list) else []
        for c in checks:
            o.marcar(f'bx_{sistema}_{c}')
        det = str(val.get('detalle') or '').strip()
        if det:
            o.texto(f't_{sistema}_otro', det)

    # Odontología
    odo_prof_nom, _m = _prof_repr(_g(odo, 'profesional', None))
    o.texto('t_odo_prof', odo_prof_nom)
    _fecha3(o, 't_ofecha', _g(odo, 'fecha_evaluacion', None))
    sb = str(_g(odo, 'salud_bucal', '') or '')
    if sb == 'con_hallazgos':
        o.marcar('bx_sb_con')
    elif sb == 'sin_hallazgos':
        o.marcar('bx_sb_sin')
    elif sb == 'no_eval':
        o.marcar('bx_sb_no')
    if _g(odo, 'lesiones_tejidos_blandos', False):
        o.marcar('bx_lesiones')
    if _g(odo, 'maloclusion', False):
        o.marcar('bx_maloclusion')
    if _g(odo, 'fluorosis', False):
        o.marcar('bx_fluorosis')
    if _g(odo, 'caries', False):
        o.marcar('bx_caries')
    if str(_g(odo, 'otros', '') or '').strip():
        o.marcar('bx_odo_otros')
        o.texto('t_odo_otros', _g(odo, 'otros', ''))
    for letra, attr in [('C', 'cpo_c'), ('P', 'cpo_p'), ('O', 'cpo_o'),
                        ('c', 'ceo_c'), ('e', 'ceo_e'), ('o', 'ceo_o')]:
        v = _g(odo, attr, None)
        try:
            if v is not None and int(v) > 0:
                o.marcar(f'bx_cpo_{letra}')
        except Exception:
            pass
    o.par('bx_top', bool(_g(odo, 'topicacion_fluor', False)))
    o.par('bx_cep', bool(_g(odo, 'ensenanza_cepillado', False)))
    o.par('bx_alta', bool(_g(odo, 'alta_basica', False)))
    odonto_data = _g(odo, 'odontograma', None) or {}
    for num, p in odonto_data.items():
        if str(num) in _TEETH:
            o.teeth[str(num)] = _estado_diente(p)

    # Derivaciones
    deriv = _g(med, 'derivaciones', None) or {}
    for esp in ('odontologia', 'oftalmologia', 'nutricion', 'vacunatorio',
                'pediatria', 'fonoaudiologia', 'cardiologia', 'traumatologia',
                'cirugia', 'urologia', 'orl', 'dermatologia', 'neurologia',
                'trabajo_social', 'psicologia', 'psicopedagogia',
                'agente_sanitario', 'otros'):
        val = deriv.get(esp) if isinstance(deriv, dict) else None
        deriva = bool(val.get('deriva')) if isinstance(val, dict) else False
        o.marcar(f'bx_deriv_{esp}_{"si" if deriva else "no"}')
        if deriva:
            o.texto(f't_deriv_{esp}', val.get('motivo', '') if isinstance(val, dict) else '')

    # Constancia
    o.texto('t_const_nom', nom_ape)
    o.texto('t_const_dni', dni)
    o.texto('t_const_edad', d['edad'] if d['edad'] is not None else '')
    o.texto('t_const_obs', _g(al, 'observaciones', ''))
    if _g(med, 'carnet_completo', False):
        o.marcar('bx_cv_completas')
    elif ap or ind:
        o.marcar('bx_cv_curso')
    else:
        o.marcar('bx_cv_debe')
    o.texto('t_const_peso', _g(med, 'peso', ''))
    o.texto('t_const_talla', _g(med, 'talla', ''))
    _fecha3(o, 't_const', _g(med, 'fecha_evaluacion', None))
    return o


def _dibujar(o):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    for page in (0, 1):
        # X en casillas
        c.setStrokeColor(black)
        c.setLineWidth(1.1)
        for fid in o.marks:
            e = _BX.get(fid)
            if not e or e[0] != page:
                continue
            x0, y0t, x1, y1t = e[1], e[2], e[3], e[4]
            ya, yb = PAGE_H - y1t, PAGE_H - y0t
            dx = min(1.0, (x1 - x0) * 0.18)
            dy = min(1.0, (yb - ya) * 0.18)
            c.line(x0 + dx, ya + dy, x1 - dx, yb - dy)
            c.line(x0 + dx, yb - dy, x1 - dx, ya + dy)
        # Valores
        for fid, valor in o.texts.items():
            if fid == 't_sexo':
                continue
            e = _TX.get(fid)
            if not e or e[0] != page:
                continue
            _x, y_top, size = e[1], e[2], e[3] if len(e) > 3 else 8.5
            alineado = e[4] if len(e) > 4 else 'l'
            c.setFillColor(black)
            c.setFont('Helvetica', size)
            if alineado == 'c':
                c.drawCentredString(_x, PAGE_H - y_top, valor)
            else:
                c.drawString(_x, PAGE_H - y_top, valor)
        # Sexo: subraya la letra
        letra = o.texts.get('t_sexo', '')
        if letra in ('t_sexo_f', 't_sexo_m'):
            e = _TX.get(letra)
            if e and e[0] == page:
                _x, y_top, size = e[1], e[2], e[3] if len(e) > 3 else 8.5
                c.setFillColor(black)
                c.setFont('Helvetica-Bold', size + 1)
                c.drawString(_x, PAGE_H - y_top, 'F' if letra == 't_sexo_f' else 'M')
                c.setLineWidth(1.2)
                c.line(_x - 1, PAGE_H - y_top - 1.5, _x + 8, PAGE_H - y_top - 1.5)
        # Dientes a color
        for num, est in o.teeth.items():
            e = _TEETH.get(num)
            if not e or e[0] != page or not est:
                continue
            cx, cy_top = e[1], e[2]
            cy = PAGE_H - cy_top
            color = {'azul': AZUL, 'rojo': ROJO, 'gris': GRIS}.get(est, black)
            c.setStrokeColor(color)
            c.setLineWidth(1.8)
            r = 3.4
            c.line(cx - r, cy - r, cx + r, cy + r)
            c.line(cx - r, cy + r, cx + r, cy - r)
        c.showPage()
    c.save()
    return buf.getvalue()


def generar_planilla_pdf(operativo: Operativo, alumno: OperativoAlumno) -> bytes:
    """Planilla PROSANE por alumno con formato idéntico al papel (oficio).

    Requiere operativo en estado FINALIZADO (validado por la vista).
    """
    overlay = _dibujar(_armar_overlay(_juntar(operativo, alumno)))
    base = PdfReader(str(TEMPLATE))
    over = PdfReader(io.BytesIO(overlay))
    out = PdfWriter()
    for i in range(len(base.pages)):
        pg = base.pages[i]
        if i < len(over.pages):
            pg.merge_page(over.pages[i])
        out.add_page(pg)
    buf = io.BytesIO()
    out.write(buf)
    return buf.getvalue()

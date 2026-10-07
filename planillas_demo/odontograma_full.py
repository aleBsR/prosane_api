"""Genera una planilla de muestra con el odontograma COMPLETO (todas las
piezas marcadas en todos los estados) para verificar la impresión.

Modifica la evaluación odontológica de UN alumno demo (dev únicamente).
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.operativos.models import EvaluacionOdontologica, Operativo
from apps.operativos.services_planilla import generar_planilla_pdf

PERMANENTES = (
    ["18", "17", "16", "15", "14", "13", "12", "11"]
    + ["21", "22", "23", "24", "25", "26", "27", "28"]
    + ["48", "47", "46", "45", "44", "43", "42", "41"]
    + ["31", "32", "33", "34", "35", "36", "37", "38"]
)
TEMPORARIAS = (
    ["55", "54", "53", "52", "51"]
    + ["61", "62", "63", "64", "65"]
    + ["85", "84", "83", "82", "81"]
    + ["71", "72", "73", "74", "75"]
)

# (estado_general, caras, raiz) rotando por los 4 estados visuales:
# sano (sin marca) / azul (a realizar) / rojo (realizado) / gris (bloqueada)
PATRON = [
    (None, None, None),                                            # sano
    ("caries", {"oclusal": "caries"}, None),                      # azul
    ("restauracion", {"oclusal": "restauracion"}, None),           # rojo
    ("ausente", {}, None),                                        # gris
    (None, {"oclusal": "sellador"}, None),                        # rojo
    ("a_extraer", {"oclusal": "a_tratar"}, None),                  # azul
    ("extraido", {}, None),                                       # gris
    (None, {"oclusal": "fractura"}, "conducto_pendiente"),        # azul
    (None, {"oclusal": "tratada"}, "conducto_realizado"),         # rojo
]


def pieza(i):
    eg, caras, raiz = PATRON[i % len(PATRON)]
    return {
        "estado_general": eg or "",
        "caras": caras or {},
        "raiz": raiz or "",
    }


op = Operativo.objects.filter(estado=Operativo.FINALIZADO).order_by("fecha").first()
alumno = (
    op.alumnos.exclude(estado="ausente")
    .select_related("paciente__persona")
    .order_by("apellido", "nombre")
    .first()
)
print("alumno:", alumno.apellido, alumno.nombre)

odonto = {}
for i, num in enumerate(PERMANENTES + TEMPORARIAS):
    odonto[num] = pieza(i)

evo, _ = EvaluacionOdontologica.objects.get_or_create(operativo_alumno=alumno)
evo.salud_bucal = "con_hallazgos"
evo.lesiones_tejidos_blandos = True
evo.maloclusion = True
evo.fluorosis = False
evo.caries = True
evo.topicacion_fluor = True
evo.ensenanza_cepillado = True
evo.alta_basica = False
evo.cpo_c, evo.cpo_p, evo.cpo_o = True, True, True
evo.ceo_c, evo.ceo_e, evo.ceo_o = True, True, True
evo.odontograma = odonto
evo.completada = True
evo.save()
print(f"odontograma: {len(odonto)} piezas marcadas")

pdf = generar_planilla_pdf(op, alumno)
out = os.path.join(
    "planillas_demo",
    f"odontograma-completo-{alumno.apellido}-{alumno.nombre}.pdf".replace(" ", "_"),
)
with open(out, "wb") as f:
    f.write(pdf)
print("OK:", out)

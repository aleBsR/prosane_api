import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.operativos.models import Operativo
from apps.operativos.services_constancia import generar_constancia_pdf
from apps.operativos.services_planilla import generar_planilla_pdf

op = Operativo.objects.filter(estado=Operativo.FINALIZADO).order_by("fecha").first()
print("operativo:", op.id, op.escuela.nombre)
alumnos = list(op.alumnos.all())
print("total alumnos:", len(alumnos))

out = os.path.join("planillas_demo")
os.makedirs(out, exist_ok=True)
for a in alumnos[:6]:
    planilla = generar_planilla_pdf(op, a)
    safe = f"{a.id}-planilla.pdf"
    with open(os.path.join(out, safe), "wb") as f:
        f.write(planilla)
    print("  + planilla:", safe)

    constancia = generar_constancia_pdf(op, a)
    safe_c = f"{a.id}-constancia.pdf"
    with open(os.path.join(out, safe_c), "wb") as f:
        f.write(constancia)
    print("  + constancia:", safe_c)

print("OK")
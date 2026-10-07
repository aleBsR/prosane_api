"""Seed de desarrollo: datos completos para ver la planilla PROSANE impresa.

Completa lo que la planilla necesita y hoy falta en dev:
  - Profesionales (matrícula/nombre) para medico@ y odontologo@.
  - Tutores (Persona adulta + parentesco + AntecedenteFamiliarTutor) para
    todos los pacientes que no tengan tutor.
  - Domicilios completos (calle, nro, piso, dpto, localidad, ...).
  - AntecedenteFamiliar por paciente.
  - Catálogo de vacunas + carnet por paciente.
  - Evaluaciones médicas y odontológicas con todos los campos de la planilla
    (vacunas aplicadas/indicadas, hallazgos, derivaciones, odontograma).

Recomendado correr tras seed_escuelas_operativos y seed_demo_flujo.
Idempotente: solo completa lo que falta. Solo desarrollo (SEEDS_ENABLED).
"""
from datetime import date, timedelta
from decimal import Decimal
from random import Random

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.antecedentes.models import AntecedenteFamiliar, AntecedenteFamiliarTutor, AntecedentePersonal
from apps.operativos.models import (
    EvaluacionMedica, EvaluacionOdontologica, Operativo, OperativoAlumno,
)
from apps.pacientes.models import Paciente
from apps.personas.models import Persona
from apps.profesionales.models import Profesional
from apps.tutores.models import Tutor
from apps.usuarios.models import Usuario
from apps.vacunas.models import CarnetVacuna, Vacuna

VACUNAS_CATALOGO = [
    "BCG", "Hepatitis B", "Neumococo conjugada", "Quíntuple (Pentavalente)",
    "IPV (Sabín)", "Triple Viral (SRP)", "Triple Bacteriana Celular (DPT)",
    "Hepatitis A", "Varicela", "Meningococo", "Antigripal", "Fiebre Amarilla",
    "COVID-19", "VPH",
]

VACUNAS_BASICAS = [
    "BCG", "Hepatitis B", "Neumococo conjugada", "Quíntuple (Pentavalente)",
    "IPV (Sabín)", "Triple Viral (SRP)", "Hepatitis A", "Varicela",
]

NOMBRES_MADRE = ["María", "Rosa", "Lucía", "Gabriela", "Mirta", "Norma",
                 "Andrea", "Silvia", "Verónica", "Estela", "Claudia", "Patricia"]
NOMBRES_PADRE = ["Juan", "Carlos", "Miguel", "Ramón", "José", "Luis",
                 "Héctor", "Oscar", "Sergio", "Raúl", "Daniel", "Mario"]

CALLES = ["Av. Belgrano", "Calle Mitre", "Ruta 51", "Combate de Salta",
          "Av. Reyes Católicos", "Caseros", "Alvarado", "Camino al Valle"]
DEPARTAMENTOS = ["Capital", "Cerrillos", "Chicoana", "Cafayate", "Orán",
                 "Rosario de Lerma"]
LOCALIDADES = ["Salta", "Cerrillos", "Chicoana", "Cafayate", "Pichanal",
               "Rosario de Lerma"]


def _rng(alumno):
    return Random((alumno.operativo_id.int ^ alumno.id.int))


class Command(BaseCommand):
    help = "Completa datos (profesionales, tutores, domicilios, vacunas, evaluaciones) para planillas (solo dev)."

    def handle(self, *args, **options):
        if not getattr(settings, "SEEDS_ENABLED", False):
            raise CommandError(
                "SEEDS_ENABLED no está activo: este comando es SOLO para desarrollo local."
            )

        self._profesionales()
        self._tutores_y_domicilios()
        self._vacunas()
        self._evaluaciones()

        self.stdout.write(self.style.SUCCESS("seed_datos_planillas completado"))

    # ── Profesionales ──────────────────────────────────────────────────────
    def _profesionales(self):
        for email, nombre, apellido, matricula in [
            ("medico@prosane.test", "Laura", "Fernández", "M-12045"),
            ("odontologo@prosane.test", "Ricardo", "Álvarez", "O-08432"),
        ]:
            usuario = Usuario.objects.filter(email=email).first()
            if not usuario:
                self.stdout.write(self.style.WARNING(f"  ! no existe {email}"))
                continue
            if Profesional.objects.filter(id_usuario=usuario).exists():
                self.stdout.write(f"  = profesional {email} ya existía")
                continue
            Profesional.objects.create(
                id_usuario=usuario, nombre=nombre, apellido=apellido, matricula=matricula,
            )
            self.stdout.write(f"  + profesional {email} ({nombre} {apellido}, {matricula})")

    # ── Tutores + domicilios + ant. familiares ─────────────────────────────
    def _tutores_y_domicilios(self):
        pacientes = (
            Paciente.objects.filter(persona__isnull=False)
            .select_related("persona", "domicilio", "tutor__persona")
            .order_by("persona__apellido", "persona__nombre")
        )
        for k, paciente in enumerate(pacientes):
            if paciente.domicilio_id:
                self._completar_domicilio(paciente, k)
            if not paciente.tutor_id:
                self._crear_tutor(paciente, k)
            self._antecedente_familiar(paciente, k)
            self.stdout.write(f"  ~ {paciente.persona.apellido}, {paciente.persona.nombre}")

    def _completar_domicilio(self, paciente, k):
        dom = paciente.domicilio
        if dom.calle:
            return
        dom.calle = CALLES[k % len(CALLES)]
        dom.nro_calle = str(100 + (k % 90) * 3)
        dom.piso = "" if k % 4 else str(k % 6)
        dom.dpto = "" if k % 4 else chr(65 + k % 6)
        dom.manzana = "" if (k % 3) else f"M{k % 12 + 1}"
        dom.casa = "" if (k % 3) else f"C{k % 9 + 1}"
        dom.nro_casa = str(1 + (k % 8)) if (k % 3 == 0) else ""
        dom.provincia = "Salta"
        dom.departamento = DEPARTAMENTOS[k % len(DEPARTAMENTOS)]
        dom.localidad = LOCALIDADES[k % len(LOCALIDADES)]
        dom.save()

    def _crear_tutor(self, paciente, k):
        es_madre = k % 2 == 0
        apellido = paciente.persona.apellido or "Sin apellido"
        nombre = NOMBRES_MADRE[k % len(NOMBRES_MADRE)] if es_madre else NOMBRES_PADRE[k % len(NOMBRES_PADRE)]
        dni = str(28_000_000 + paciente.id.int % 9_000_000)
        while Persona.objects.filter(dni=dni).exists():
            dni = str(int(dni) + 1)
        tutor_persona = Persona.objects.create(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            tipo_dni="DNI",
            sexo="femenino" if es_madre else "masculino",
            fecha_nacimiento=date(1975, 1, 1) + timedelta(days=paciente.id.int % 9000),
        )
        tutor = Tutor.objects.create(
            persona=tutor_persona,
            parentesco="madre" if es_madre else "padre",
            consentimiento_aceptado=True,
            fecha_consentimiento=timezone.now() - timedelta(days=30),
        )
        paciente.tutor = tutor
        paciente.consentimiento_aceptado = True
        paciente.fecha_consentimiento = tutor.fecha_consentimiento
        paciente.save(update_fields=[
            "tutor", "consentimiento_aceptado", "fecha_consentimiento", "updated_at",
        ])
        if not AntecedenteFamiliarTutor.objects.filter(tutor=tutor).exists():
            AntecedenteFamiliarTutor.objects.create(
                tutor=tutor,
                problema_salud_importante="no" if k % 3 else "si",
                problema_salud_cual="Hipertensión arterial" if not k % 3 else "",
                muerte_subita_familiar="no" if k % 5 else "si",
            )

    def _antecedente_familiar(self, paciente, k):
        if AntecedenteFamiliar.objects.filter(paciente=paciente).exists():
            return
        AntecedenteFamiliar.objects.create(
            paciente=paciente,
            problemas_salud="NO" if k % 2 else "SI",
            detalle_problema_salud="Diabetes tipo 2 en abuelos" if not k % 2 else "",
            familiar_con_muerte_subita="NO" if k % 4 else "SI",
        )

    # ── Vacunas catálogo + carnet ──────────────────────────────────────────
    def _vacunas(self):
        por_nombre = {}
        for nombre in VACUNAS_CATALOGO:
            v, ctx = Vacuna.objects.get_or_create(nombre=nombre)
            por_nombre[nombre] = v
            if ctx:
                self.stdout.write(f"  + vacuna: {nombre}")

        pacientes = Paciente.objects.filter(persona__isnull=False)
        for k, paciente in enumerate(pacientes):
            if CarnetVacuna.objects.filter(paciente=paciente).exists():
                continue
            if k % 2:
                for nombre in VACUNAS_BASICAS:
                    CarnetVacuna.objects.create(paciente=paciente, vacuna=por_nombre[nombre])
                self.stdout.write(f"  ~ carnet {paciente.persona.apellido}: {len(VACUNAS_BASICAS)} vacunas")

    # ── Evaluaciones (todas las secciones de la planilla) ──────────────────
    def _evaluaciones(self):
        medico = Usuario.objects.filter(email="medico@prosane.test").first()
        odontologo = Usuario.objects.filter(email="odontologo@prosane.test").first()
        alumnos = OperativoAlumno.objects.filter(
            operativo__estado=Operativo.FINALIZADO,
        ).select_related(
            "paciente__persona", "paciente__tutor", "operativo__escuela", "curso",
        )
        for alumno in alumnos:
            self._seccion_escuela(alumno)
            self._seccion_datos(alumno)
            if alumno.estado == OperativoAlumno.AUSENTE:
                self.stdout.write(f"  ~ {alumno.apellido}, {alumno.nombre}: ausente (sin evals)")
                continue
            self._evaluacion_medica(alumno, medico)
            self._evaluacion_odontologica(alumno, odontologo)
            self.stdout.write(f"  ~ {alumno.apellido}, {alumno.nombre} ({alumno.operativo.escuela.nombre[:24]})")

    def _seccion_escuela(self, alumno):
        alumno.escuela_completado = True
        alumno.escuela_preocupa_salud = True
        alumno.escuela_preocupa_detalle = "Presenta bajo peso según docente."
        alumno.escuela_dificultad_lenguaje = True
        alumno.escuela_bajo_tratamiento = False
        alumno.save(update_fields=[
            "escuela_completado", "escuela_preocupa_salud",
            "escuela_preocupa_detalle", "escuela_dificultad_lenguaje",
            "escuela_bajo_tratamiento", "updated_at",
        ])

    def _seccion_datos(self, alumno):
        paciente = alumno.paciente
        if not paciente:
            return
        rng = _rng(alumno)
        ant, _ = AntecedentePersonal.objects.get_or_create(paciente=paciente)
        ant.nacio_prematuro = "NO" if rng.random() < 0.6 else "SI"
        ant.peso_nacimiento = str(rng.randint(2500, 4200))
        ant.convulsiones_epilepsia = "NO"
        ant.mareos_desmayos = "NO"
        ant.infecciones_urinarias = "SI" if rng.random() < 0.2 else "NO"
        ant.asma_espasmos = "NO"
        ant.tuberculosis = "NO"
        ant.diabetes = "NO"
        ant.hipertension = "NO"
        ant.cardiopatia_congenita = "NO"
        ant.traumatismo_internacion = "NO" if rng.random() < 0.8 else "SI"
        ant.diarrea_frecuente = "NO"
        ant.infecciones_oido = "NO" if rng.random() < 0.7 else "SI"
        ant.internacion_previa = "NO"
        ant.causa_hospitalizacion = "NO"
        ant.tratamiento_actual = "NO"
        ant.descripcion_tratamiento = "NINGUNO"
        ant.ultima_consulta_medica = "menos_1_anio"
        ant.otros_problemas_salud = "NINGUNO"
        ant.primera_menstruacion = "SI" if rng.random() < 0.5 else "NO"
        ant.edad_primera_menstruacion = 12 if rng.random() < 0.5 else 0
        ant.save()
        alumno.antecedentes_completado = True
        alumno.save(update_fields=["antecedentes_completado", "updated_at"])

    def _evaluacion_medica(self, alumno, medico):
        rng = _rng(alumno)
        peso = Decimal(rng.randint(20, 55)) + Decimal("0.7")
        talla = Decimal(rng.randint(112, 155)) + Decimal("0.3")
        imc = (peso / ((talla / 100) ** 2)).quantize(Decimal("0.1"))
        hall = {
            "piel": {"estado": "con", "detalle": "Pediculosis en cuero cabelludo.", "checks": ["pediculosis", "escabiosis"]},
            "partes_blandas": {"estado": "sin", "detalle": "", "checks": []},
            "cardiovascular": {"estado": "sin", "detalle": "", "checks": []},
            "respiratorio": {"estado": "con", "detalle": "Respirador bucal habitual.", "checks": ["respiracion_bucal"]},
            "abdominal": {"estado": "sin", "detalle": "", "checks": []},
            "genitourinario_ninos": {"estado": "sin", "detalle": "", "checks": []},
            "genitourinario_ninas": {"estado": "sin", "detalle": "", "checks": []},
            "osteoarticular": {"estado": "sin", "detalle": "", "checks": []},
            "neurologico": {"estado": "sin", "detalle": "", "checks": []},
            "icv": {"estado": "sin", "detalle": "", "checks": []},
            "salud_visual": {"estado": "con", "detalle": "Disminución de agudeza visual.", "checks": ["disminucion_agudeza"]},
            "salud_fonoaudiologica": {"estado": "sin", "detalle": "", "checks": []},
        }
        deriv = {
            "odontologia": {"deriva": False, "motivo": ""},
            "oftalmologia": {"deriva": True, "motivo": "Disminución agudeza visual"},
            "nutricion": {"deriva": False, "motivo": ""},
            "vacunatorio": {"deriva": False, "motivo": ""},
            "pediatria": {"deriva": True, "motivo": "Control por respiración bucal"},
            "fonoaudiologia": {"deriva": False, "motivo": ""},
        }
        EvaluacionMedica.all_objects.filter(operativo_alumno=alumno).update(deleted_at=None)
        EvaluacionMedica.objects.update_or_create(
            operativo_alumno=alumno,
            defaults={
                "profesional": medico,
                "fecha_evaluacion": timezone.now() - timedelta(days=3),
                "examen_realizado": True,
                "lugar_examen": "escuela",
                "trajo_carnet": True,
                "carnet_completo": rng.random() < 0.5,
                "vacunas_aplicadas": "BCG, Hepatitis B, Quíntuple, Triple Viral" if rng.random() < 0.7 else "",
                "vacunas_indicadas": "Triple Viral 2ª dosis" if rng.random() < 0.3 else "",
                "antropometria_evaluada": True,
                "peso": peso,
                "talla": talla,
                "imc": imc,
                "percentil_talla": "mayor_igual_3",
                "percentil_imc": "entre_10_84",
                "presion_evaluada": True,
                "pas": rng.randint(95, 110),
                "pad": rng.randint(55, 70),
                "presion_clasificacion": "normal",
                "agudeza_evaluada": True,
                "ojo_derecho": "10/10" if rng.random() < 0.6 else "8/10",
                "ojo_izquierdo": "10/10" if rng.random() < 0.6 else "8/10",
                "usa_lentes": rng.random() < 0.2,
                "audiometria_realizada": True,
                "audiometria_resultado": "pasa" if rng.random() < 0.8 else "no_pasa",
                "hallazgos": hall,
                "derivaciones": deriv,
                "completada": True,
            },
        )

    def _evaluacion_odontologica(self, alumno, odontologo):
        rng = _rng(alumno)
        piezas = ["51", "52", "53", "54", "55", "61", "62", "63", "64", "65",
                  "71", "72", "73", "74", "75", "81", "82", "83", "84", "85"]
        odontograma = {}
        for p in piezas:
            v = rng.random()
            if v < 0.6:
                odontograma[p] = {"estado_general": "", "caras": {}, "raiz": ""}
            elif v < 0.75:
                odontograma[p] = {"estado_general": "caries", "caras": {"oclusal": "caries"}, "raiz": ""}
            elif v < 0.85:
                odontograma[p] = {"estado_general": "restauracion", "caras": {"oclusal": "restauracion"}, "raiz": ""}
            elif v < 0.95:
                odontograma[p] = {"estado_general": "ausente", "caras": {}, "raiz": ""}
            else:
                odontograma[p] = {"estado_general": "extraido", "caras": {}, "raiz": ""}
        cpo_c = rng.random() < 0.6
        cpo_p = rng.random() < 0.2
        cpo_o = rng.random() < 0.2
        ceo_c = rng.random() < 0.6
        ceo_e = rng.random() < 0.2
        ceo_o = rng.random() < 0.2
        EvaluacionOdontologica.all_objects.filter(operativo_alumno=alumno).update(deleted_at=None)
        EvaluacionOdontologica.objects.update_or_create(
            operativo_alumno=alumno,
            defaults={
                "profesional": odontologo,
                "fecha_evaluacion": timezone.now() - timedelta(days=3),
                "salud_bucal": "con_hallazgos" if rng.random() < 0.5 else "sin_hallazgos",
                "lesiones_tejidos_blandos": rng.random() < 0.2,
                "maloclusion": rng.random() < 0.3,
                "fluorosis": rng.random() < 0.2,
                "caries": bool(cpo_c or ceo_c),
                "otros": "",
                "topicacion_fluor": True,
                "ensenanza_cepillado": True,
                "alta_basica": True,
                "cpo_c": cpo_c,
                "cpo_p": cpo_p,
                "cpo_o": cpo_o,
                "ceo_c": ceo_c,
                "ceo_e": ceo_e,
                "ceo_o": ceo_o,
                "odontograma": odontograma,
                "completada": True,
            },
        )
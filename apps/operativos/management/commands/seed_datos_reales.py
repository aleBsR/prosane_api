"""Seed de desarrollo: base de datos completa y realista.

Genera todo el circuito PROSANE con datos de aspecto «real» para evaluar el
sistema de punta a punta (web + móvil + planillas) antes de pasarlo a testers:

- 6 escuelas (urbanas públicas, privada, rurales plurigrado) con sus cursos.
- 8 operativos distribuidos en TODOS los estados:
    * 2 FINALIZADO (histórico 2025 y actual 2026).
    * 2 EN_CURSO (uno con nómina grande mixta, otro rural chico).
    * 1 CONFIRMADO (escuela + datos completos, sin evaluaciones).
    * 1 BORRADOR (nómina cargada, sin datos).
    * 1 CANCELADO.
  Con ~850 alumnos en total (nóminas masivas por import CSV).
- Profesionales con matrícula (4 usuarios: 2 médicos, 2 odontólogos).
- Tutores con domicilio completo, parentesco, consentimiento y antecedentes
  familiares (padre o madre).
- Antecedentes personales variados y antecedentes familiares del paciente.
- Catálogo de vacunas + carnet por paciente.
- Evaluaciones médicas y odontológicas completas (con odontograma, CPO/ceo,
  hallazgos, derivaciones) para FINALIZADO y EN_CURSO; parciales en EN_CURSO.

Solo para desarrollo local (SEEDS_ENABLED). No es idempotente: ejecutar tras
`flush` + `loaddata roles users` + `seed_permissions`.
"""
import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from random import Random

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.antecedentes.models import (
    AntecedenteFamiliar, AntecedenteFamiliarTutor, AntecedentePersonal,
)
from apps.escuelas.models import Escuela
from apps.operativos import services
from apps.operativos.models import (
    EvaluacionMedica, EvaluacionOdontologica, Operativo, OperativoAlumno,
)
from apps.pacientes.models import Paciente
from apps.personas.models import Domicilio, Persona
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

APELLIDOS = [
    "Mamani", "Flores", "Vilte", "Torres", "Coronel", "Cruz", "Morales",
    "Choque", "Tolaba", "Soria", "Sara", "Sura", "Gutiérrez", "Villagra",
    "Arias", "Medina", "Romano", "Chocobar", "Lopez", "Fernandez", "Gomez",
    "Diaz", "Martinez", "Pereyra", "Salazar", "Vargas", "Rojas", "Vega",
    "Ramírez", "Acosta", "Benitez", "Cardozo", "Escobar", "Farías", "Ferrari",
    "Godoy", "Herrera", "Ibáñez", "Juárez", "Leiva", "Molina", "Núñez",
    "Ortiz", "Paz", "Quispe", "Rivas", "Sánchez", "Tapia", "Uribe",
]
NOMBRES_MASC = [
    "Lautaro", "Mateo", "Benjamín", "Santiago", "Thiago", "Joaquín",
    "Tiziano", "Santino", "Bruno", "Agustín", "Facundo", "Kevin", "Brian",
    "Axel", "Luca", "Franco", "Leonardo", "Tomás", "Valentín", "Francisco",
    "Juan", "Maximiliano", "Felipe", "Diego", "Rodrigo", "Nicolás",
]
NOMBRES_FEM = [
    "Camila", "Morena", "Sofía", "Martina", "Candela", "Valentina",
    "Guadalupe", "Mía", "Julieta", "Emilia", "Abril", "Delfina", "Pilar",
    "Luz", "Carla", "Milagros", "Selena", "Isabel", "Florencia", "Agustina",
    "Victoria", "Catalina", "Antonela", "Rocío", "Celeste", "Natalia",
]
NOMBRES_MADRE = ["María", "Rosa", "Lucía", "Gabriela", "Mirta", "Norma",
                 "Andrea", "Silvia", "Verónica", "Estela", "Claudia", "Patricia"]
NOMBRES_PADRE = ["Juan", "Carlos", "Miguel", "Ramón", "José", "Luis",
                 "Héctor", "Oscar", "Sergio", "Raúl", "Daniel", "Mario"]

CALLES = ["Av. Belgrano", "Calle Mitre", "Ruta 51", "Combate de Salta",
          "Av. Reyes Católicos", "Caseros", "Alvarado", "Camino al Valle",
          "El Carril", "Av. Del Bicentenario", "Pasaje Las Acacias",
          "Calle Los Lapachos"]
DEPARTAMENTOS = ["Capital", "Cerrillos", "Chicoana", "Cafayate", "Orán",
                 "Rosario de Lerma"]
LOCALIDADES = ["Salta", "Cerrillos", "Chicoana", "Cafayate", "Pichanal",
               "Rosario de Lerma"]

GRADOS = ["1°", "2°", "3°", "4°", "5°", "6°"]
DIVISIONES = ["A", "B", "C"]

# Edad mínima (años cumplidos al 31/03 del año del operativo) por grado.
EDAD_POR_GRADO = {"1°": 6, "2°": 7, "3°": 8, "4°": 9, "5°": 10, "6°": 11}

# URIs definidos en la planilla física para la sección escuela.
PRIMERA_MENSTRUACION = False

HALLAZGOS_KEYS = [
    "piel", "partes_blandas", "cardiovascular", "respiratorio", "abdominal",
    "genitourinario_ninos", "genitourinario_ninas", "osteoarticular",
    "neurologico", "icv", "salud_visual", "salud_fonoaudiologica",
]
DERIVACION_KEYS = [
    "odontologia", "oftalmologia", "nutricion", "vacunatorio", "pediatria",
    "fonoaudiologia",
]


def _edad_y_nacimiento(anio_operativo, grado, rng):
    """Devuelve una fecha de nacimiento coherente con el grado (ciclo lectivo)."""
    edad_min = EDAD_POR_GRADO[grado]
    anio_nac = anio_operativo - edad_min
    mes = rng.randint(1, 12)
    dia = rng.randint(1, 28)
    return date(anio_nac, mes, dia)


def _rng(alumno):
    return Random(alumno.operativo_id.int ^ alumno.id.int)


class Command(BaseCommand):
    help = "Carga una base completa y realista para evaluar PROSANE (solo dev)."

    def handle(self, *args, **options):
        if not getattr(settings, "SEEDS_ENABLED", False):
            raise CommandError(
                "SEEDS_ENABLED no está activo: este comando es SOLO desarrollo."
            )

        self.rng = Random(20260503)
        self.dni_global = 46000000  # DNI únicos para toda la base
        self.dni_tutor = 25000000   # DNI únicos para tutores
        self.n_creados = 0
        self.n_ausentes = 0
        self.n_evaluados = 0
        self.n_parciales = 0

        usuarios = {
            u.email: u for u in Usuario.objects.all()
        }
        self.usuario_superadmin = usuarios.get("superadmin@prosane.test")
        self.medicos = [usuarios.get("medico@prosane.test"), usuarios.get("medico1@prosane.test")]
        self.odontologos = [usuarios.get("odontologo@prosane.test"), usuarios.get("odontologo1@prosane.test")]
        self.medico = self.medicos[0]
        self.odontologo = self.odontologos[0]
        if not self.medico or not self.odontologo:
            raise CommandError("Faltan usuarios médico/odontólogo. Corré loaddata users.")

        self._profesionales()
        escuelas = self._escuelas_y_operativos()
        self._vacunas_catalogo()

        # Definición de operativos por escuela.
        planes = [
            ("güemes", "finalizado_2025", 130),
            ("güemes", "finalizado_2026", 170),
            ("san_martín", "en_curso", 140),
            ("valle", "confirmado", 100),
            ("los_andes", "en_curso_rural", 55),
            ("belgrano", "borrador", 90),
            ("santa_rosa", "cancelado", 70),
            ("los_andes", "finalizado_2026", 60),
        ]

        for idx, (esc_key, plan, n) in enumerate(planes):
            escuela = escuelas[esc_key]
            self._crear_operativo(escuela, idx, plan, n)

        # Cursos de plurigrado rural: para Los Andes ya se crearon al importar.
        self.asignar_escuela_a_escuela_user(escuelas)

        self.stdout.write(self.style.SUCCESS(
            f"seed_datos_reales OK: {self.n_creados} alumnos "
            f"({self.n_evaluados} evaluados, {self.n_parciales} parciales, "
            f"{self.n_ausentes} ausentes)"
        ))

    # ── Profesionales ──────────────────────────────────────────────────
    def _profesionales(self):
        datos = [
            ("medico@prosane.test", "Laura", "Fernández", "M-12045"),
            ("odontologo@prosane.test", "Ricardo", "Álvarez", "O-08432"),
            ("medico1@prosane.test", "Matías", "Cordero", "M-13001"),
            ("odontologo1@prosane.test", "Carolina", "Molinas", "O-09102"),
        ]
        for email, nombre, apellido, matricula in datos:
            usuario = Usuario.objects.filter(email=email).first()
            if not usuario:
                self.stdout.write(self.style.WARNING(f"  ! no existe {email}"))
                continue
            if Profesional.objects.filter(id_usuario=usuario).exists():
                continue
            Profesional.objects.create(
                id_usuario=usuario, nombre=nombre, apellido=apellido,
                matricula=matricula,
            )
        self.stdout.write(self.style.SUCCESS("  + 4 profesionales con matrícula"))

    # ── Escuelas ───────────────────────────────────────────────────────
    def _escuelas_y_operativos(self):
        escuelas = {}
        base = [
            {
                "key": "güemes", "nombre": 'Escuela Nº 4.501 "General Güemes"',
                "cue": "66004501", "ambito": "urbano", "sector_gestion": "publica",
                "modalidad": "comun", "plurigrado": False,
                "calle": "Av. Belgrano", "nro": "1200",
            },
            {
                "key": "san_martín", "nombre": 'Escuela Nº 4.502 "San Martín"',
                "cue": "66004502", "ambito": "urbano", "sector_gestion": "publica",
                "modalidad": "comun", "plurigrado": False,
                "calle": "Calle Mitre", "nro": "340",
            },
            {
                "key": "valle", "nombre": 'Escuela Nº 4.503 "Nuestra Señora del Valle"',
                "cue": "66004503", "ambito": "urbano", "sector_gestion": "privada",
                "modalidad": "comun", "plurigrado": False,
                "calle": "Ruta 51", "nro": "km 8",
            },
            {
                "key": "los_andes", "nombre": 'Escuela Rural Nº 4.504 "Los Andes"',
                "cue": "66004504", "ambito": "rural", "sector_gestion": "publica",
                "modalidad": "plurigrado", "plurigrado": True,
                "calle": "Camino al Valle", "nro": "s/n",
            },
            {
                "key": "belgrano", "nombre": 'Escuela Nº 4.505 "Manuel Belgrano"',
                "cue": "66004505", "ambito": "urbano", "sector_gestion": "publica",
                "modalidad": "comun", "plurigrado": False,
                "calle": "Av. Del Bicentenario", "nro": "780",
            },
            {
                "key": "santa_rosa", "nombre": 'Escuela Nº 4.506 "Santa Rosa de Lima"',
                "cue": "66004506", "ambito": "urbano", "sector_gestion": "publica",
                "modalidad": "comun", "plurigrado": False,
                "calle": "Alvarado", "nro": "505",
            },
        ]
        for data in base:
            domicilio, _ = Domicilio.objects.get_or_create(
                calle=data["calle"], nro_calle=data["nro"], localidad="Salta",
                provincia="Salta", departamento="Capital",
            )
            escuela, created = Escuela.objects.get_or_create(
                cue=data["cue"],
                defaults={
                    "nombre": data["nombre"], "ambito": data["ambito"],
                    "sector_gestion": data["sector_gestion"],
                    "modalidad_educativa": data["modalidad"],
                    "plurigrado_rural": data["plurigrado"],
                    "domicilio": domicilio,
                },
            )
            escuelas[data["key"]] = escuela
            estado = "creada" if created else "ya existía"
            self.stdout.write(f"  + escuela {escuela.nombre[:40]}… ({estado})")
        return escuelas

    def asignar_escuela_a_escuela_user(self, escuelas):
        escuela_user = Usuario.objects.filter(email="escuela@prosane.test").first()
        if escuela_user:
            escuela_user.escuela = escuelas["güemes"]
            escuela_user.save(update_fields=["escuela"])

    # ── Crear operativo + nómina + datos según plan ─────────────────────
    def _crear_operativo(self, escuela, idx, plan, n_alumnos):
        fechas = [
            date(2025, 3, 15), date(2026, 3, 9), date(2026, 5, 11),
            date(2026, 6, 8), date(2026, 4, 20), date(2026, 8, 10),
            date(2026, 4, 30), date(2026, 7, 20),
        ]
        fecha = fechas[idx % len(fechas)]
        lugares = ["escuela", "centro_salud"]
        notas_por_plan = {
            "finalizado_2025": "Operativo anual 2025 programado por el equipo de salud.",
            "finalizado_2026": "Operativo anual 2026. Vacunación completa y entrega de constancias.",
            "en_curso": "Jornada mixta: se evalúa por curso durante la mañana.",
            "en_curso_rural": "Recorrida por parajes. Plurigrado.",
            "confirmado": "Nómina confirmada por la escuela, pendiente inicio.",
            "borrador": "Nómina cargada, aún sin confirmar.",
            "cancelado": "Suspendido por reorganización de agenda de salud.",
        }
        operativo, created = Operativo.objects.get_or_create(
            escuela=escuela, fecha=fecha,
            defaults={
                "nombre": f"Operativo PROSANE - {escuela.nombre}",
                "lugar_realizacion": lugares[idx % 2],
                "estado": Operativo.BORRADOR,
                "notas": notas_por_plan.get(plan, ""),
                "created_by": self.usuario_superadmin,
            },
        )
        if not created:
            operativo.estado = Operativo.BORRADOR
            operativo.save(update_fields=["estado"])
        self.stdout.write(f"> {operativo.nombre[:45]}… :: {plan} ({n_alumnos})")

        # Profesionales según plan.
        self._asignar_profesionales(operativo, plan)

        # Nómina masiva.
        if not operativo.alumnos.exists():
            self._importar_nomina(operativo, plan, n_alumnos)

        alumnos = list(
            operativo.alumnos.select_related(
                "paciente__persona", "paciente__domicilio", "curso",
            ).order_by("apellido", "nombre")
        )
        operativo.refresh_from_db()

        # Datos por plan.
        if plan.startswith("finalizado"):
            self._rellenar_finalizado(operativo, alumnos, plan)
        elif plan == "en_curso":
            self._rellenar_en_curso(operativo, alumnos, mixto=True)
        elif plan == "en_curso_rural":
            self._rellenar_en_curso(operativo, alumnos)
        elif plan == "confirmado":
            self._rellenar_confirmado(operativo, alumnos)
        elif plan == "borrador":
            pass  # Solo nómina.
        elif plan == "cancelado":
            self._rellenar_cancelado(operativo, alumnos)

        # Transiciones de estado del operativo.
        if plan.startswith("finalizado"):
            services.confirmar_operativo(operativo.id)
            services.iniciar_operativo(operativo.id)
            services.finalizar_operativo(operativo.id)
            self.stdout.write("    -> finalizado")
        elif plan == "en_curso" or plan == "en_curso_rural":
            services.confirmar_operativo(operativo.id)
            services.iniciar_operativo(operativo.id)
            self.stdout.write("    -> en curso")
        elif plan == "confirmado":
            services.confirmar_operativo(operativo.id)
            self.stdout.write("    -> confirmado")
        elif plan == "borrador":
            self.stdout.write("    -> borrador (sin datos)")
        elif plan == "cancelado":
            try:
                services.confirmar_operativo(operativo.id)
            except ValueError:
                pass  # Si no tiene profesionales, se cancela desde borrador.
            try:
                services.cancelar_operativo(operativo.id)
            except ValueError as e:
                self.stdout.write(self.style.WARNING(f"    ! cancelar: {e}"))
                operativo.estado = Operativo.CANCELADO
                operativo.save(update_fields=["estado"])
            self.stdout.write("    -> cancelado")

    def _asignar_profesionales(self, operativo, plan):
        medicos = [self.medicos[0]]
        odontologos = [self.odontologos[0]]
        if plan in ("en_curso", "en_curso_rural", "finalizado_2026"):
            medicos = self.medicos
            odontologos = self.odontologos
        parejas = []
        for m in medicos:
            if m:
                parejas.append((m, "medico"))
        for o in odontologos:
            if o:
                parejas.append((o, "odontologo"))
        if plan != "borrador":
            # Cancelado sin confirmación necesaria: asignar igual (borrador).
            pass
        if plan == "borrador":
            return  # Un borrador recién armado aún no tiene profesionales.
        for usuario, rol in parejas:
            try:
                services.asignar_profesional(operativo.id, usuario.id, rol)
            except ValueError as e:
                if "asignado" not in str(e):
                    self.stdout.write(self.style.WARNING(f"    ! {rol}: {e}"))

    def _importar_nomina(self, operativo, plan, n_alumnos):
        """Genera una nómina CSV masiva y la importa (crea alumnos y pacientes)."""
        plurigrado = operativo.escuela.plurigrado_rural
        filas = [] if n_alumnos > 0 else []
        for _ in range(n_alumnos):
            self.dni_global += 1
            apellido = self.rng.choice(APELLIDOS)
            femenino = self.rng.random() < 0.5
            nombre = self.rng.choice(NOMBRES_FEM if femenino else NOMBRES_MASC)
            if self.rng.random() < 0.25:
                segundo = self.rng.choice(NOMBRES_MASC if not femenino else NOMBRES_FEM)
                nombre = f"{nombre} {segundo}"
            grado = self.rng.choice(GRADOS)
            division = "" if plurigrado else self.rng.choice(DIVISIONES)
            nac = _edad_y_nacimiento(operativo.fecha.year, grado, self.rng)
            filas.append({
                "dni": str(self.dni_global),
                "apellido": apellido,
                "nombre": nombre,
                "tipo_dni": "DNI",
                "fecha_nacimiento": nac.strftime("%d/%m/%Y"),
                "sexo": "femenino" if femenino else "masculino",
                "grado": grado,
                "division": division,
            })
        buff = io.StringIO()
        writer = csv.DictWriter(buff, fieldnames=list(filas[0].keys()))
        writer.writeheader()
        writer.writerows(filas)
        csv_bytes = buff.getvalue().encode("utf-8-sig")
        resultado = services.importar_csv(
            operativo.id, ContentFile(csv_bytes, name="nomina.csv")
        )
        self.n_creados += resultado["creados"]
        for etiqueta, cantidad in sorted(resultado["creados_por_curso"].items()):
            self.stdout.write(f"    · curso {etiqueta}: {cantidad}")
        if resultado["errores"]:
            self.stdout.write(self.style.WARNING(f"    ! errores CSV: {resultado['errores'][:3]}"))

    # ── Rellenos por plan ───────────────────────────────────────────────
    def _seccion_escuela(self, alumno, i):
        alumno.escuela_preocupa_salud = (i % 4 == 0)
        alumno.escuela_preocupa_detalle = (
            "Observaciones de la docente sobre el peso." if i % 4 == 0 else ""
        )
        alumno.escuela_dificultad_lenguaje = (i % 5 == 0)
        alumno.escuela_bajo_tratamiento = (i % 6 == 0)
        alumno.escuela_completado = True
        alumno.save(update_fields=[
            "escuela_preocupa_salud", "escuela_preocupa_detalle",
            "escuela_dificultad_lenguaje", "escuela_bajo_tratamiento",
            "escuela_completado", "updated_at",
        ])

    def _seccion_paciente(self, alumno):
        """Completa Paciente + domicilio + tutor + antecedentes."""
        paciente = alumno.paciente
        if not paciente:
            return
        persona = paciente.persona
        nac = persona.fecha_nacimiento or date(2018, 1, 1)
        hoy = timezone.now().date()
        paciente.edad = max(
            5, hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
        )
        paciente.celular = f"387{self.rng.randint(3000000, 5999999)}"
        paciente.tipo_cobertura = self.rng.choice(
            ["obra_social", "obra_social", "privado", "publico"]
        )
        paciente.nombre_cobertura = self.rng.choice(
            ["OSDE", "Swiss Medical", "Medifé", "IOMA", "Galeno", "PAMI", ""]
        )
        paciente.consentimiento_aceptado = True
        paciente.fecha_consentimiento = timezone.now() - timedelta(days=30)
        paciente.save()

        # Domicilio completo.
        dom = paciente.domicilio
        if dom and not dom.calle:
            k = id(alumno) % len(CALLES)
            dom.calle = self.rng.choice(CALLES)
            dom.nro_calle = str(self.rng.randint(100, 2500))
            dom.piso = "" if self.rng.random() < 0.7 else str(self.rng.randint(1, 10))
            dom.dpto = "" if self.rng.random() < 0.7 else self.rng.choice("ABCDE")
            if not dom.provincia:
                dom.provincia = "Salta"
                dom.departamento = self.rng.choice(DEPARTAMENTOS)
                dom.localidad = self.rng.choice(LOCALIDADES)
            dom.save()

        # Tutor.
        if not paciente.tutor_id:
            self._crear_tutor(paciente, alumno)

        # Antecedente familiar del paciente.
        if not AntecedenteFamiliar.objects.filter(paciente=paciente).exists():
            AntecedenteFamiliar.objects.create(
                paciente=paciente,
                problemas_salud="SI" if self.rng.random() < 0.3 else "NO",
                detalle_problema_salud=(
                    "Diabetes tipo 2 en abuelos." if self.rng.random() < 0.3 else ""
                ),
                familiar_con_muerte_subita="SI" if self.rng.random() < 0.1 else "NO",
            )

        # Antecedente personal (sección A).
        self._antecedente_personal(paciente, alumno)
        alumno.antecedentes_completado = True
        alumno.save(update_fields=["antecedentes_completado", "updated_at"])

    def _crear_tutor(self, paciente, alumno):
        es_madre = self.rng.random() < 0.6
        apellido = paciente.persona.apellido or "Apellido"
        while True:
            self.dni_tutor += 1
            if not Persona.objects.filter(dni=str(self.dni_tutor)).exists():
                break
        tutor_persona = Persona.objects.create(
            nombre=(self.rng.choice(NOMBRES_MADRE) if es_madre
                    else self.rng.choice(NOMBRES_PADRE)),
            apellido=apellido,
            dni=str(self.dni_tutor),
            tipo_dni="DNI",
            sexo="femenino" if es_madre else "masculino",
            fecha_nacimiento=date(1975, 1, 1) + timedelta(days=alumno.id.int % 9000),
        )
        tutor = Tutor.objects.create(
            persona=tutor_persona,
            parentesco="madre" if es_madre else "padre",
            consentimiento_aceptado=True,
            fecha_consentimiento=timezone.now() - timedelta(days=30),
        )
        AntecedenteFamiliarTutor.objects.create(
            tutor=tutor,
            problema_salud_importante="no" if self.rng.random() < 0.8 else "si",
            problema_salud_cual="Hipertensión arterial" if self.rng.random() < 0.2 else "",
            muerte_subita_familiar="no" if self.rng.random() < 0.9 else "si",
        )
        paciente.tutor = tutor
        paciente.save(update_fields=["tutor", "updated_at"])
        return tutor

    def _antecedente_personal(self, paciente, alumno):
        rng = self.rng
        ant, _ = AntecedentePersonal.objects.get_or_create(paciente=paciente)
        ant.nacio_prematuro = "SI" if rng.random() < 0.15 else "NO"
        mes_gest = 7 if ant.nacio_prematuro == "SI" else 9
        ant.peso_nacimiento = str(rng.randint(2200, 4200)) if mes_gest == 9 else str(rng.randint(1600, 2500))
        ant.convulsiones_epilepsia = "SI" if rng.random() < 0.03 else "NO"
        ant.mareos_desmayos = "SI" if rng.random() < 0.06 else "NO"
        ant.infecciones_urinarias = "SI" if rng.random() < 0.12 else "NO"
        ant.asma_espasmos = "SI" if rng.random() < 0.08 else "NO"
        ant.tuberculosis = "NO"
        ant.diabetes = "SI" if rng.random() < 0.02 else "NO"
        ant.hipertension = "NO"
        ant.cardiopatia_congenita = "NO"
        ant.traumatismo_internacion = "SI" if rng.random() < 0.04 else "NO"
        ant.diarrea_frecuente = "SI" if rng.random() < 0.06 else "NO"
        ant.infecciones_oido = "SI" if rng.random() < 0.14 else "NO"
        ant.internacion_previa = "SI" if rng.random() < 0.09 else "NO"
        ant.causa_hospitalizacion = (
            "Internación por cuadro respiratorio." if ant.internacion_previa == "SI" else "NO"
        )
        ant.tratamiento_actual = "NO"
        ant.descripcion_tratamiento = "NINGUNO"
        ant.ultima_consulta_medica = rng.choice(
            ["menos_1_anio", "menos_1_anio", "mas_1_anio", "no_recuerda"]
        )
        ant.otros_problemas_salud = "NINGUNO"
        if persona_femenina(paciente) and paciente.edad >= 11:
            ant.primera_menstruacion = "SI" if rng.random() < 0.7 else "NO"
            ant.edad_primera_menstruacion = 12 if ant.primera_menstruacion == "SI" else 0
        ant.save()

    def _evaluacion_medica(self, alumno, completada=True):
        if alumno.estado == OperativoAlumno.AUSENTE:
            return None
        medicos = self.medicos
        medico = medicos[alumno.id.int % len([m for m in medicos if m])]
        rng = Random(alumno.id.int)
        peso = Decimal(rng.randint(20, 60)) + Decimal("0.5")
        talla = Decimal(rng.randint(112, 158)) + Decimal("0.0")
        imc = (peso / ((talla / 100) ** 2)).quantize(Decimal("0.1"))
        # Percentil de IMC coherente (mayoritariamente normal).
        roll = rng.random()
        if roll < 0.68:
            percentil_imc = "entre_10_84"
        elif roll < 0.82:
            percentil_imc = "entre_85_97"
        elif roll < 0.92:
            percentil_imc = "mayor_97"
        elif roll < 0.97:
            percentil_imc = "entre_3_9"
        else:
            percentil_imc = "menor_3"

        hallazgos = {}
        for key in HALLAZGOS_KEYS:
            estado = "sin"
            detalle = ""
            checks = []
            if key == "piel" and rng.random() < 0.25:
                estado, detalle = "con", "Pediculosis en cuero cabelludo."
                checks = ["pediculosis"]
            elif key == "respiratorio" and rng.random() < 0.12:
                estado, detalle = "con", "Respirador bucal habitual."
                checks = ["respiracion_bucal"]
            elif key == "salud_visual" and rng.random() < 0.18:
                estado, detalle = "con", "Disminución de agudeza visual."
                checks = ["disminucion_agudeza"]
            hallazgos[key] = {"estado": estado, "detalle": detalle, "checks": checks}

        derivaciones = {}
        for key in DERIVACION_KEYS:
            deriva = rng.random() < 0.10
            motivos = {
                "odontologia": "Caries múltiples", "oftalmologia": "Disminución agudeza",
                "nutricion": "Control de peso", "vacunatorio": "Actualizar carnet",
                "pediatria": "Control clínico", "fonoaudiologia": "Derivación por lenguaje",
            }
            derivaciones[key] = {
                "deriva": deriva, "motivo": motivos[key] if deriva else "",
            }

        ojo = rng.choice(["10/10", "10/10", "8/10", "6/10"])
        EvaluacionMedica.objects.update_or_create(
            operativo_alumno=alumno,
            defaults={
                "profesional": medico,
                "fecha_evaluacion": timezone.now() - timedelta(days=3),
                "examen_realizado": True,
                "lugar_examen": "escuela",
                "trajo_carnet": True,
                "carnet_completo": rng.random() < 0.6,
                "vacunas_aplicadas": (
                    "BCG, Hepatitis B, Quíntuple, Triple Viral"
                    if rng.random() < 0.75 else ""
                ),
                "vacunas_indicadas": (
                    "Triple Viral 2ª dosis" if rng.random() < 0.25 else ""
                ),
                "antropometria_evaluada": True,
                "peso": peso, "talla": talla, "imc": imc,
                "percentil_talla": "mayor_igual_3",
                "percentil_imc": percentil_imc,
                "presion_evaluada": True,
                "pas": rng.randint(90, 118),
                "pad": rng.randint(55, 76),
                "presion_clasificacion": (
                    "normal" if rng.random() < 0.85 else "elevada"
                ),
                "agudeza_evaluada": True,
                "ojo_derecho": ojo,
                "ojo_izquierdo": ojo,
                "usa_lentes": rng.random() < 0.12,
                "audiometria_realizada": True,
                "audiometria_resultado": "pasa" if rng.random() < 0.85 else "no_pasa",
                "hallazgos": hallazgos,
                "derivaciones": derivaciones,
                "completada": completada,
            },
        )

    def _evaluacion_odontologica(self, alumno, completada=True):
        if alumno.estado == OperativoAlumno.AUSENTE:
            return None
        odontologos = self.odontologos
        lista = [o for o in odontologos if o]
        odontologo = lista[alumno.id.int % len(lista)]
        rng = Random(alumno.id.int + 1)
        # Odontograma según edad (temporarios para chicos, mixto para grandes).
        paciente = alumno.paciente
        edad = paciente.edad if paciente else 9
        temporarias = True
        odontograma = {}
        piezas_temp = ["51", "52", "53", "54", "55", "61", "62", "63", "64",
                       "65", "71", "72", "73", "74", "75", "81", "82", "83",
                       "84", "85"]
        piezas_perm = ["18", "17", "16", "15", "14", "13", "12", "11",
                       "21", "22", "23", "24", "25", "26", "27", "28",
                       "48", "47", "46", "45", "44", "43", "42", "41",
                       "31", "32", "33", "34", "35", "36", "37", "38"]
        if edad <= 7:
            piezas = piezas_temp
        elif edad <= 10:
            # Mixto: temporarios anteriores + permanentes centrales.
            piezas = piezas_temp + ["11", "21", "31", "41", "16", "26", "36", "46"]
        else:
            piezas = piezas_perm
            temporarias = False
        for p in piezas:
            v = rng.random()
            if v < 0.72:
                odontograma[p] = {"estado_general": "", "caras": {}, "raiz": ""}
            elif v < 0.84:
                odontograma[p] = {
                    "estado_general": "",
                    "caras": {"oclusal": "caries"},
                    "raiz": "",
                }
            elif v < 0.92:
                odontograma[p] = {
                    "estado_general": "",
                    "caras": {"oclusal": "restauracion"},
                    "raiz": "",
                }
            elif v < 0.97:
                odontograma[p] = {"estado_general": "ausente", "caras": {}, "raiz": ""}
            else:
                odontograma[p] = {"estado_general": "extraido", "caras": {}, "raiz": ""}

        cpo_c = rng.random() < 0.5 and not temporarias
        cpo_p = rng.random() < 0.15 and not temporarias
        cpo_o = rng.random() < 0.15 and not temporarias
        ceo_c = rng.random() < 0.6 and temporarias
        ceo_e = rng.random() < 0.2 and temporarias
        ceo_o = rng.random() < 0.2 and temporarias
        salud = (
            "con_hallazgos" if (cpo_c or ceo_c or rng.random() < 0.2)
            else "sin_hallazgos"
        )
        EvaluacionOdontologica.objects.update_or_create(
            operativo_alumno=alumno,
            defaults={
                "profesional": odontologo,
                "fecha_evaluacion": timezone.now() - timedelta(days=3),
                "salud_bucal": salud,
                "lesiones_tejidos_blandos": rng.random() < 0.08,
                "maloclusion": rng.random() < 0.16,
                "fluorosis": rng.random() < 0.1,
                "caries": bool(cpo_c or ceo_c),
                "otros": "",
                "topicacion_fluor": rng.random() < 0.9,
                "ensenanza_cepillado": True,
                "alta_basica": True,
                "cpo_c": cpo_c, "cpo_p": cpo_p, "cpo_o": cpo_o,
                "ceo_c": ceo_c, "ceo_e": ceo_e, "ceo_o": ceo_o,
                "odontograma": odontograma,
                "completada": completada,
            },
        )

    def _marcar_estado(self, alumno, estado):
        alumno.estado = estado
        alumno.save(update_fields=["estado", "updated_at"])

    def _rellenar_finalizado(self, operativo, alumnos, plan):
        """Todos completos salvo un pequeño % de ausentes."""
        for i, alumno in enumerate(alumnos):
            if (i + 1) % 13 == 0:
                self._marcar_estado(alumno, OperativoAlumno.AUSENTE)
                self.n_ausentes += 1
                continue
            self._seccion_escuela(alumno, i)
            self._seccion_paciente(alumno)
            self._carnet_vacunas(alumno)
            self._evaluacion_medica(alumno, completada=True)
            self._evaluacion_odontologica(alumno, completada=True)
            self._marcar_estado(alumno, OperativoAlumno.EVALUADO)
            self.n_evaluados += 1

    def _rellenar_en_curso(self, operativo, alumnos, mixto=False):
        """Mezcla de completos, parciales y ausentes."""
        n = len(alumnos)
        for i, alumno in enumerate(alumnos):
            if i % 7 == 6:
                self._marcar_estado(alumno, OperativoAlumno.AUSENTE)
                self.n_ausentes += 1
                continue
            self._seccion_escuela(alumno, i)
            self._seccion_paciente(alumno)
            self._carnet_vacunas(alumno)
            if i % 3 == 0:
                # Completo.
                self._evaluacion_medica(alumno, completada=True)
                self._evaluacion_odontologica(alumno, completada=True)
                self._marcar_estado(alumno, OperativoAlumno.EVALUADO)
                self.n_evaluados += 1
            elif i % 3 == 1:
                # Sólo médica completa (sin odontológica aún).
                self._evaluacion_medica(alumno, completada=True)
                if self.rng.random() < 0.5:
                    self._evaluacion_odontologica(alumno, completada=False)
                self._marcar_estado(alumno, OperativoAlumno.PRESENTE)
                self.n_parciales += 1
            else:
                # Solo secciones E + A; M parcial (sin completar).
                self._evaluacion_medica(alumno, completada=False)
                self._marcar_estado(alumno, OperativoAlumno.PRESENTE)
                self.n_parciales += 1

    def _rellenar_confirmado(self, operativo, alumnos):
        """Escuela + datos completos, sin evaluaciones."""
        for i, alumno in enumerate(alumnos):
            if i % 10 == 9:
                continue  # queda pendiente, sin secciones.
            self._seccion_escuela(alumno, i)
            self._seccion_paciente(alumno)
            self._marcar_estado(alumno, OperativoAlumno.PRESENTE)
            self.n_parciales += 1

    def _rellenar_cancelado(self, operativo, alumnos):
        """Algunos con secciones cargadas (nunca evaluados)."""
        for i, alumno in enumerate(alumnos):
            if i % 4 == 3:
                continue
            self._seccion_escuela(alumno, i)
            self._seccion_paciente(alumno)
            self._marcar_estado(alumno, OperativoAlumno.PRESENTE)
        self.n_parciales += len(alumnos)

    def _carnet_vacunas(self, alumno):
        paciente = alumno.paciente
        if not paciente or CarnetVacuna.objects.filter(paciente=paciente).exists():
            return
        por_nombre = {v.nombre: v for v in Vacuna.objects.all()}
        if self.rng.random() < 0.85:
            basicas = list(VACUNAS_BASICAS)
            cats = [por_nombre[n] for n in basicas if n in por_nombre]
            for vacuna in cats:
                CarnetVacuna.objects.create(paciente=paciente, vacuna=vacuna)

    def _vacunas_catalogo(self):
        for nombre in VACUNAS_CATALOGO:
            Vacuna.objects.get_or_create(nombre=nombre)


def persona_femenina(paciente):
    return (paciente.persona.sexo or "").lower() == "femenino"

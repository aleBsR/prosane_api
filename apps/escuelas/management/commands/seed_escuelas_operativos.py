"""Seed de desarrollo: escuelas, cursos, operativos, profesionales y alumnos.

Crea varias escuelas con sus cursos, asigna una escuela al usuario
escuela@prosane.test, crea operativos (borrador) con profesionales asignados
y carga la nómina demo (nomina_alumnos_demo.csv) en los operativos.

Solo para desarrollo local (SEEDS_ENABLED).
"""
from datetime import date

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from apps.escuelas.models import Curso, Escuela
from apps.operativos.models import Operativo, OperativoProfesional
from apps.operativos import services
from apps.personas.models import Domicilio
from apps.usuarios.models import Usuario


ESCUELAS = [
    {
        'nombre': 'Escuela Nº 4.501 "General Güemes"',
        'cue': '66004501',
        'ambito': 'urbano',
        'sector_gestion': 'publica',
        'modalidad_educativa': 'comun',
        'domicilio': {'calle': 'Av. Belgrano', 'nro_calle': '1200', 'localidad': 'Salta', 'provincia': 'Salta'},
        'telefono': '4220001',
    },
    {
        'nombre': 'Escuela Nº 4.502 "San Martín"',
        'cue': '66004502',
        'ambito': 'urbano',
        'sector_gestion': 'publica',
        'modalidad_educativa': 'comun',
        'domicilio': {'calle': 'Calle Mitre', 'nro_calle': '340', 'localidad': 'Salta', 'provincia': 'Salta'},
        'telefono': '4220002',
    },
    {
        'nombre': 'Escuela Nº 4.503 "Nuestra Señora del Valle"',
        'cue': '66004503',
        'ambito': 'urbano',
        'sector_gestion': 'privada',
        'modalidad_educativa': 'comun',
        'domicilio': {'calle': 'Ruta 51', 'nro_calle': 'km 8', 'localidad': 'Cerrillos', 'provincia': 'Salta'},
        'telefono': '4220003',
    },
    {
        'nombre': 'Escuela Rural Nº 4.504 "Los Andes"',
        'cue': '66004504',
        'ambito': 'rural',
        'sector_gestion': 'publica',
        'modalidad_educativa': 'plurigrado',
        'plurigrado_rural': True,
        'domicilio': {'calle': 'Camino al Valle', 'nro_calle': 's/n', 'localidad': 'Chicoana', 'provincia': 'Salta'},
        'telefono': '4220004',
    },
]

CURSOS = [
    ('primaria', '1º', 'A'),
    ('primaria', '1º', 'B'),
    ('primaria', '2º', 'A'),
    ('primaria', '2º', 'B'),
    ('primaria', '3º', 'A'),
    ('primaria', '3º', 'B'),
]


class Command(BaseCommand):
    help = "Crea escuelas, cursos, operativos y profesionales demo (solo dev)."

    def handle(self, *args, **options):
        if not getattr(settings, "SEEDS_ENABLED", False):
            raise CommandError(
                "SEEDS_ENABLED no está activo: este comando es SOLO para desarrollo local."
            )

        # 1) Escuelas + domicilios + cursos
        escuelas = []
        for data in ESCUELAS:
            dom_data = data.pop('domicilio')
            dom, _ = Domicilio.objects.get_or_create(**dom_data)
            escuela, created = Escuela.objects.get_or_create(
                cue=data['cue'],
                defaults={**data, 'domicilio': dom},
            )
            if created:
                for nivel, grado, division in CURSOS:
                    Curso.objects.get_or_create(
                        escuela=escuela,
                        sala_grado_anio=grado,
                        division=division,
                        defaults={'nivel': nivel, 'ciclo_lectivo': 2026},
                    )
                self.stdout.write(f'  + escuela: {escuela.nombre}')
            else:
                self.stdout.write(f'  = ya existía: {escuela.nombre}')
            escuelas.append(escuela)

        # 2) Asignar la primera escuela al usuario escuela@prosane.test
        escuela_usuario = Usuario.objects.filter(email='escuela@prosane.test').first()
        if escuela_usuario:
            escuela_usuario.escuela = escuelas[0]
            escuela_usuario.save(update_fields=['escuela'])
            self.stdout.write(f'  > escuela@{escuela_usuario.email} -> {escuelas[0].nombre}')
        else:
            self.stdout.write(self.style.WARNING('  ! no se encontró escuela@prosane.test'))

        # 3) Operativos: uno por escuela (borrador), con profesionales y nómina
        profesionales = {
            'medico': Usuario.objects.filter(email='medico@prosane.test').first(),
            'odontologo': Usuario.objects.filter(email='odontologo@prosane.test').first(),
            'ayudante': Usuario.objects.filter(email='ayudante@prosane.test').first(),
        }

        csv_path = settings.BASE_DIR / 'nomina_alumnos_demo.csv'
        csv_bytes = csv_path.read_bytes()

        for i, escuela in enumerate(escuelas):
            fecha = date(2026, 3, 9 + i)
            operativo, created = Operativo.objects.get_or_create(
                escuela=escuela,
                fecha=fecha,
                defaults={
                    'nombre': f'Operativo PROSANE - {escuela.nombre}',
                    'lugar_realizacion': 'escuela',
                    'estado': Operativo.BORRADOR,
                },
            )
            if created:
                self.stdout.write(f'  + operativo: {operativo}')
            else:
                self.stdout.write(f'  = ya existía: {operativo}')

            for rol, usuario in profesionales.items():
                if not usuario:
                    continue
                try:
                    services.asignar_profesional(operativo.id, usuario.id, rol)
                    self.stdout.write(f'    > profesional {rol}: {usuario.email}')
                except ValueError as e:
                    self.stdout.write(f'    = profesional {rol}: {e}')

            if not operativo.alumnos.exists():
                resultado = services.importar_csv(operativo.id, ContentFile(csv_bytes, name='nomina.csv'))
                self.stdout.write(f'    > CSV: creados={resultado["creados"]} duplicados={resultado["duplicados"]} errores={len(resultado["errores"])}')
            else:
                self.stdout.write(f'    = ya tiene {operativo.alumnos.count()} alumnos')

        self.stdout.write(self.style.SUCCESS('seed_escuelas_operativos completado'))
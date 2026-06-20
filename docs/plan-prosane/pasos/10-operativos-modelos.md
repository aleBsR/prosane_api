# Paso 10: Modelos del operativo

## Objetivo

Crear la app `operativos` con los 3 modelos: Operativo, OperativoProfesional, OperativoAlumno.

## 1. Crear la app

```bash
python manage.py startapp operativos
```

Mover a `apps/operativos/`:

```bash
mv operativos apps/operativos
```

Registrar en `config/settings/base.py` → `INSTALLED_APPS`:
```python
'apps.operativos',
```

## 2. Modelo Operativo

**Archivo:** `apps/operativos/models/operativo.py`
```python
from django.db import models
from common.models import BaseModel


class Operativo(BaseModel):
    BORRADOR = 'borrador'
    CONFIRMADO = 'confirmado'
    EN_CURSO = 'en_curso'
    FINALIZADO = 'finalizado'
    CANCELADO = 'cancelado'

    ESTADO_CHOICES = [
        (BORRADOR, 'Borrador'),
        (CONFIRMADO, 'Confirmado'),
        (EN_CURSO, 'En curso'),
        (FINALIZADO, 'Finalizado'),
        (CANCELADO, 'Cancelado'),
    ]

    LUGAR_CHOICES = [
        ('escuela', 'En la escuela'),
        ('centro_salud', 'En el centro de salud'),
        ('otros', 'Otros'),
    ]

    nombre = models.CharField(max_length=200, blank=True, default='')
    escuela = models.ForeignKey(
        'escuelas.Escuela', on_delete=models.PROTECT, related_name='operativos',
    )
    fecha = models.DateField(db_index=True)
    lugar_realizacion = models.CharField(
        max_length=20, choices=LUGAR_CHOICES, default='escuela',
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=BORRADOR, db_index=True,
    )
    notas = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='operativos_creados',
    )

    class Meta:
        db_table = 'operativos'
        verbose_name = 'operativo'
        verbose_name_plural = 'operativos'
        ordering = ['-fecha', '-created_at']

    def __str__(self):
        return f'{self.nombre or self.escuela.nombre} - {self.fecha} ({self.get_estado_display()})'
```

## 3. Modelo OperativoProfesional

**Archivo:** `apps/operativos/models/profesional.py`
```python
from django.db import models
from common.models import BaseModel


class OperativoProfesional(BaseModel):
    ROL_CHOICES = [
        ('medico', 'Médico'),
        ('odontologo', 'Odontólogo'),
        ('ayudante', 'Ayudante'),
    ]

    operativo = models.ForeignKey(
        'operativos.Operativo', on_delete=models.CASCADE,
        related_name='profesionales_asignados',
    )
    profesional = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.CASCADE,
        related_name='operativos_asignados',
    )
    rol_en_operativo = models.CharField(max_length=20, choices=ROL_CHOICES)
    confirmado = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'operativos_profesionales'
        verbose_name = 'profesional en operativo'
        unique_together = ('operativo', 'profesional')

    def __str__(self):
        return f'{self.profesional.email} → {self.operativo}'
```

## 4. Modelo OperativoAlumno

**Archivo:** `apps/operativos/models/alumno.py`
```python
from django.db import models
from common.models import BaseModel


class OperativoAlumno(BaseModel):
    PENDIENTE = 'pendiente'
    PRESENTE = 'presente'
    AUSENTE = 'ausente'
    EVALUADO = 'evaluado'

    ESTADO_CHOICES = [
        (PENDIENTE, 'Pendiente'),
        (PRESENTE, 'Presente'),
        (AUSENTE, 'Ausente'),
        (EVALUADO, 'Evaluado'),
    ]

    operativo = models.ForeignKey(
        'operativos.Operativo', on_delete=models.CASCADE, related_name='alumnos',
    )
    paciente = models.ForeignKey(
        'pacientes.Paciente', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='operativos_como_alumno',
    )
    curso = models.ForeignKey(
        'escuelas.Curso', on_delete=models.SET_NULL, null=True, blank=True,
    )

    # Snapshots del CSV
    apellido = models.CharField(max_length=200)
    nombre = models.CharField(max_length=200)
    tipo_dni = models.CharField(max_length=10, default='DNI')
    dni = models.CharField(max_length=15, db_index=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=10, blank=True, default='')

    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=PENDIENTE,
    )
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'operativos_alumnos'
        verbose_name = 'alumno en operativo'
        unique_together = ('operativo', 'dni')

    def __str__(self):
        return f'{self.apellido}, {self.nombre} (DNI: {self.dni})'
```

## 5. Migrar

```bash
python manage.py makemigrations operativos
python manage.py migrate operativos
```

## 6. Verificar

```bash
python manage.py shell -c "
from apps.operativos.models import Operativo
print('OK:', Operativo._meta.db_table)
"
```

## Criterio de aceptación

- Migración corre sin errores
- Tablas `operativos`, `operativos_profesionales`, `operativos_alumnos` existen en la DB
- Estado inicial de Operativo es `borrador`
- FK a Escuela, Usuario, Paciente, Curso funcionan

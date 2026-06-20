# Paso 07: Fix Escuela + modelo Curso

## Objetivo

Agregar campos faltantes a Escuela (CUE, domicilio FK, telefono, activa) y crear el modelo Curso.

## 1. Estado actual de Escuela

En `apps/escuelas/models/escuela.py` existe `Escuela` con:
- `nombre_escuela`, `ambito_escuela`, `sector_gestion`, `modalidad_educativa`, `escuela_bilingue`, `rural_plurigrado`
- **Faltan**: `cue`, `domicilio` (FK a `personas.Domicilio`), `telefono`, `activa`
- **Renombrar**: `nombre_escuela → nombre`, `ambito_escuela → ambito`, `escuela_bilingue → intercultural_bilingue`, `rural_plurigrado → plurigrado_rural`

## 2. Modelo Escuela actualizado

**Archivo:** `apps/escuelas/models/escuela.py`
```python
from django.db import models
from common.models import BaseModel


class Escuela(BaseModel):
    nombre = models.CharField(max_length=200)
    cue = models.CharField(max_length=20, unique=True, blank=True, null=True)
    ambito = models.CharField(max_length=20, blank=True, default='')
    sector_gestion = models.CharField(max_length=20, blank=True, default='')
    modalidad_educativa = models.CharField(max_length=10, blank=True, default='')
    intercultural_bilingue = models.BooleanField(default=False)
    plurigrado_rural = models.BooleanField(default=False)
    domicilio = models.ForeignKey(
        'personas.Domicilio', on_delete=models.SET_NULL, null=True, blank=True,
    )
    telefono = models.CharField(max_length=20, blank=True, default='')
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = 'escuelas'
        verbose_name = 'escuela'
        verbose_name_plural = 'escuelas'

    def __str__(self):
        cue_str = f' ({self.cue})' if self.cue else ''
        return f'{self.nombre}{cue_str}'
```

## 3. Modelo Curso

**Archivo:** `apps/escuelas/models/curso.py`
```python
from django.db import models
from common.models import BaseModel


class Curso(BaseModel):
    escuela = models.ForeignKey(
        'escuelas.Escuela', on_delete=models.CASCADE, related_name='cursos',
    )
    nivel = models.CharField(max_length=10, blank=True, default='')
    sala_grado_anio = models.CharField(max_length=20, blank=True, default='')
    division = models.CharField(max_length=10, blank=True, default='')
    ciclo_lectivo = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'cursos'
        verbose_name = 'curso'
        verbose_name_plural = 'cursos'

    def __str__(self):
        return f'{self.sala_grado_anio}{self.division} - {self.ciclo_lectivo or ""}'
```

## 4. Migrar

```bash
python manage.py makemigrations escuelas
python manage.py migrate escuelas
```

## 5. Verificar

```bash
python manage.py shell -c "
from apps.escuelas.models import Escuela, Curso
print('OK: modelos importados correctamente')
"
```

## Criterio de aceptación

- Migración corre sin errores (se va a pedir default para campos nuevos en datos existentes — responder `1` o aceptar default)
- `Escuela` tiene los campos `cue`, `domicilio`, `telefono`, `activa`
- `Curso` se crea con FK a Escuela
- Tablas `escuelas` y `cursos` existen en la DB

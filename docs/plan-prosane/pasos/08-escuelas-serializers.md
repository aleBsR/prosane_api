# Paso 08: Serializers de Escuela y Curso

## Objetivo

Crear serializers específicos para exponer Escuela y Curso vía API.

## 1. Serializers

**Archivo:** `apps/escuelas/serializers.py`

Reemplazar el `EscuelasSerializer` genérico (`fields = '__all__'`) con estos:

```python
from rest_framework import serializers
from apps.personas.serializers import DomicilioSerializer
from .models import Escuela, Curso


class EscuelaSerializer(serializers.ModelSerializer):
    domicilio = DomicilioSerializer(required=False, allow_null=True)

    class Meta:
        model = Escuela
        fields = [
            'id', 'nombre', 'cue', 'ambito', 'sector_gestion',
            'modalidad_educativa', 'intercultural_bilingue', 'plurigrado_rural',
            'domicilio', 'telefono', 'activa',
        ]
        read_only_fields = ['id']


class EscuelaListSerializer(serializers.ModelSerializer):
    localidad = serializers.SerializerMethodField()

    class Meta:
        model = Escuela
        fields = ['id', 'nombre', 'cue', 'ambito', 'activa', 'localidad']

    def get_localidad(self, obj):
        if obj.domicilio:
            return obj.domicilio.localidad
        return ''


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = '__all__'
        read_only_fields = ['id']
```

## 2. Test rápido

```bash
python manage.py shell -c "
from apps.escuelas.serializers import EscuelaSerializer, CursoSerializer
from apps.escuelas.models import Escuela
e = Escuela.objects.create(nombre='Test')
s = EscuelaSerializer(e)
print('OK:', s.data)
"
```

## Criterio de aceptación

- Los serializers se importan sin errores
- `EscuelaSerializer` incluye `DomicilioSerializer` anidado (opcional)
- `EscuelaListSerializer` tiene campo calculado `localidad`
- `CursoSerializer` expone todos los campos del modelo

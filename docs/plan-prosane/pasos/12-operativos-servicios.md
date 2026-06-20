# Paso 12: Servicios del operativo

## Objetivo

Implementar la lógica de negocio: crear, confirmar, cancelar, finalizar, asignar profesional e importar CSV.

## 1. Servicios core

**Archivo:** `apps/operativos/services.py`

Ver archivo completo en `operativo-espec.md` sección 6. Resumen de funciones:

| Función | Descripción |
|---------|-------------|
| `crear_operativo(escuela_id, fecha, ...)` | Crea en estado borrador |
| `tiene_conflicto_fecha(profesional_id, fecha)` | True si ya tiene otro operativo en esa fecha |
| `asignar_profesional(operativo_id, profesional_id, rol)` | Asigna con validación de conflicto |
| `transicionar_estado(operativo_id, nuevo_estado, motivo)` | Valida máquina de estados y cambia |
| `confirmar_operativo(operativo_id)` | Valida condiciones (profesionales + alumnos + sin conflictos) |
| `finalizar_operativo(operativo_id)` | Valida que todos estén evaluados/ausentes |
| `importar_csv(operativo_id, archivo_csv)` | Parsea CSV y crea/vincula alumnos |

## 2. Test

```bash
python manage.py test apps.operativos.tests
```

## Criterio de aceptación

- `crear_operativo` devuelve operativo en `borrador`
- `asignar_profesional` crea la relación
- `tiene_conflicto_fecha` detecta solapamiento
- `confirmar_operativo` valida condiciones y cambia estado
- `finalizar_operativo` solo funciona si todos los alumnos están evaluados/ausentes
- `transicionar_estado` rechaza transiciones inválidas (ej: de borrador a finalizado)
- `importar_csv` procesa correctamente: crea nuevos, vincula existentes, reporta duplicados y errores
- Tests pasan

---
name: prosane-api-conventions
description: Convenciones de API REST para PROSANE — snake_case, DRF, JWT, vistas delgadas, managed False
license: MIT
compatibility: opencode
metadata:
  project: PROSANE API
  stack: Django 6.0.5, DRF 3.17.1, SimpleJWT
---

# PROSANE API Conventions

Skill para mantener consistencia en el desarrollo de la API REST del circuito PROSANE.

## Convención de nombres en JSON (API)

**Todos** los request bodies y response bodies usan **snake_case** — no camelCase.

✅ Correcto:
```json
{
  "fecha_nacimiento": "2015-06-10",
  "tipo_cobertura": "PUBLICA",
  "tiene_cud": "NO"
}
```

❌ Incorrecto:
```json
{
  "fechaNacimiento": "2015-06-10",
  "tipoCobertura": "PUBLICA",
  "tieneCUD": "NO"
}
```

**Razón:**
- La BD existente usa snake_case en todas sus columnas (managed=False)
- DRF ModelSerializer expone los campos del modelo sin transformación
- La app Flutter ya consume snake_case
- Se evita una capa extra de mapeo y posibles bugs

## Estructura de proyecto

```
config/
├── settings/
│   ├── base.py        # Settings comunes (DB default SQLite, INSTALLED_APPS, DRF, JWT)
│   ├── local.py       # Desarrollo: PostgreSQL desde .env, DEBUG=True
│   └── test.py        # Tests: SQLite in-memory, hashing rápido
├── urls.py            # rutas globales: admin/, auth/, api/v1/, docs/
apps/
├── core/              # Modelos base: Personas, Domicilio (managed=False)
├── authentication/    # Usuarios, Roles, JWT, permisos
├── patients/          # Pacientes, Responsables, Antecedentes
├── professionals/     # Profesionales, Matrículas, REFEPS
├── common/            # Mixins de auditoría (timestamps, soft-delete, created_by)
├── apidocs/           # Documentación interactiva de la API (navegable en /docs/)
```

## Reglas de código

### Vistas delgadas
- Lógica de negocio en `services.py`
- Queries complejas en `selectors.py`
- Views son adaptadores HTTP, no contienen reglas de negocio

### Serializers
- Usar para validación y forma de los datos
- `write_only=True` para passwords y campos sensibles
- Listar campos explícitamente (`fields = [...]`), evitar `'__all__'` en datos sensibles
- Los nombres de campo en el serializer **deben** ser snake_case

### Transacciones atómicas
- Operaciones multi-modelo van dentro de `@transaction.atomic`

### Versionado
- API versionada: `/api/v1/...` desde el inicio
- No crear versiones nuevas sin acuerdo del equipo

### Permisos
- Toda vista exige autenticación por defecto (DEFAULT_PERMISSION_CLASSES)
- Validar permisos por rol explícitamente en cada endpoint sensible: `EsMedico`, `EsOdontologo`, `EsTutor`, `EsAdmin`
- Los roles viajan dentro del JWT para autorización stateless

### Modelos managed=False
- Casi todos los modelos tienen `managed = False` y `db_table = 'nombre_tabla'`
- Reflejan un schema de BD preexistente
- No crear ni renombrar tablas de dominio sin acuerdo del equipo
- Ver `docs/reconciliacion-modelo.md` antes de tocar modelos

## Estructura de respuesta JSON

Todas las respuestas usan snake_case y siguen este formato:

**Éxito (GET/PUT/PATCH):**
```json
{
  "id": 1,
  "persona": {
    "nombre": "Juan",
    "apellido": "Pérez",
    "dni": "12345678",
    "tipo_dni": "DNI",
    "sexo": "M",
    "fecha_nacimiento": "2010-05-15"
  },
  "domicilio": {
    "calle": "Av. Ejemplo",
    "nro_calle": "1234",
    "provincia": "Salta",
    "departamento": "Capital",
    "localidad": "Salta"
  },
  "edad": 10,
  "tiene_cud": "NO",
  "tipo_cobertura": "PUBLICA"
}
```

**Éxito (POST):**
```json
{
  "message": "User created succesfully",
  "data": { ... }
}
```

**Error:**
```json
{
  "error": { "campo": ["Mensaje de error"] }
}
```

**No encontrado:**
```json
{
  "detail": "No se encontraron antecedentes familiares para este paciente."
}
```

## Documentación de endpoints

La app `apidocs` sirve documentación navegable en `/docs/`. Al agregar un endpoint nuevo:
1. Crear una vista en `apidocs/views.py`
2. Crear un template en `apidocs/templates/apidocs/` con el formato: card de endpoint, tabla de parámetros, ejemplo curl, ejemplos request/response
3. Agregar la URL en `apidocs/urls.py`
4. Agregar el link en la sidebar de `base.html`

## Flujo para agregar un endpoint nuevo

1. Crear/actualizar modelo (si es managed=False, verificar schema en la BD)
2. Crear serializer (campos explícitos en snake_case)
3. Crear service (si hay lógica de negocio) o selector (si es query compleja)
4. Crear view (APIView, delgada, con permission_classes)
5. Agregar URL en el urls.py de la app
6. Documentar en apidocs
7. Correr tests

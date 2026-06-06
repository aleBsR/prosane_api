# Informe de Implementación — Sistema de Registros PROSANE

> Fecha: 06/06/2026  
> Rama: autenticación y registro de usuarios (tutores y profesionales)

---

## Índice

1. [Resumen de cambios](#1-resumen-de-cambios)
2. [Flujo lógico de cada registro](#2-flujo-lógico-de-cada-registro)
3. [Patrones de diseño utilizados](#3-patrones-de-diseño-utilizados)
4. [Cómo seguir el patrón para futuros endpoints](#4-cómo-seguir-el-patrón-para-futuros-endpoints)
5. [Arquitectura final de archivos](#5-arquitectura-final-de-archivos)

---

## 1. Resumen de cambios

### Archivos modificados

| Archivo | Cambio | Motivo |
|---|---|---|
| `config/settings/base.py` | Agregado `REFEPS_MOCK = True` | Feature toggle para MVP que usa datos mock en vez de API REFEPS real |
| `config/urls.py` | Eliminada ruta `patients/` (no existe `patients/urls.py`) y duplicado de import | `python manage.py check` fallaba |
| `authentication/serializers.py` | `UserSerializer.create()`: rol por `self.context.get('rol', 'usuario')` | Permite que cada vista decida el rol sin modificar el serializer |
| `authentication/serializers.py` | Creado `RegisterTutorSerializer` | Encapsula Persona + Usuario + Responsables + rol `tutor` en una transacción |
| `authentication/serializers.py` | Creado `RegisterProfesionalSerializer` | Valida matrícula con REFEPS mock + crea Persona con datos externos + Usuario + Profesionales + rol |
| `authentication/serializers.py` | Eliminado `RegistroProfesionalesSerializer` (incompleto) | Reemplazado por el nuevo |
| `authentication/views.py` | `register`: usa `UserSerializer` sin context → rol `usuario` | Registro genérico |
| `authentication/views.py` | `register_tutor`: usa `RegisterTutorSerializer` | Thinnest possible view: 5 líneas |
| `authentication/views.py` | `register_profesional`: usa `RegisterProfesionalSerializer` | Thinnest possible view: 5 líneas |
| `authentication/views.py` | `login`: agregado `@authentication_classes([])` | Evita que JWTAuthentication rechace requests con token inválido |
| `authentication/views.py` | Agregado `solo_medicos` (GET, `EsMedico`) | Endpoint de prueba para permisos |
| `authentication/permissions.py` | Agregados `EsTutor` y `EsAyudante` | Permisos para roles futuros |
| `patients/models.py` | `Responsables`: eliminado FK `persona` (columna `id_persona` no existe en DB) | Sincronizar modelo con DB real |
| `patients/serializers.py` | `ResponsablesSerializer`: eliminado `persona` del serializer y `create()` que creaba Persona | Modelo ya no tiene ese FK |
| `patients/serializers.py` | `PacientesSerializer.to_representation()`: `id_persona` → `usuario.persona` | El responsable ahora accede a Persona vía usuario |
| `professionals/services/services_refeps.py` | `getattr(settings, 'REFEPS_MOCK', False)` en vez de `settings.REFEPS_MOCK` | No rompe si la variable no está definida |
| `professionals/services/services_refeps.py` | `_consultar_real()` implementado con `NotImplementedError` | Antes era una referencia a un método inexistente |

### DB (cambios manuales)

| Tabla | Cambio |
|---|---|
| `roles` | Insertado `ayudante` (`/home/ayudante`) |

---

## 2. Flujo lógico de cada registro

### 2.1 `POST /auth/register/` — Registro genérico

```
HTTP POST
  │
  ▼
register(request)
  │
  ├── UserSerializer(data=request.data)
  │     │
  │     ├── validate → email único, password, persona (nombre, apellido, dni, tipo_dni, sexo, fecha_nac)
  │     │
  │     └── create() @transaction.atomic:
  │           1. Personas.objects.create(nombre, apellido, dni, tipo_dni, sexo, fecha_nac)
  │           2. Usuarios.objects.create_user(email, password, persona)
  │              └── set_password(password)  # AbstractBaseUser hashea automáticamente
  │           3. UserRole.objects.create(rol=self.context.get('rol', 'usuario'), user)
  │              └── rol por defecto: 'usuario'
  │
  └── Response(201, usuario.data)
```

**Body de ejemplo:**
```json
{
  "email": "gen@test.com",
  "password": "test123",
  "persona": {
    "nombre": "Juan",
    "apellido": "Perez",
    "dni": "11111111",
    "tipo_dni": "DNI",
    "sexo": "male",
    "fecha_nacimiento": "2000-01-01"
  }
}
```

### 2.2 `POST /auth/register-tutor/` — Registro de tutor

```
HTTP POST
  │
  ▼
register_tutor(request)
  │
  ├── RegisterTutorSerializer(data=request.data)
  │     │
  │     ├── validate:
  │     │   ├── usuario → UserSerializer.validate (igual que register genérico)
  │     │   └── parentesco → CharField(max_length=50)
  │     │
  │     └── create() @transaction.atomic:
  │           1. UserSerializer(data=usuario_data, context={'rol': 'tutor'}).save()
  │              └── Crea Persona + Usuario + UserRole(rol='tutor')
  │           2. Responsables.objects.create(usuario=user, parentesco=parentesco)
  │
  └── Response(201)
```

**Body de ejemplo:**
```json
{
  "parentesco": "madre",
  "usuario": {
    "email": "maria@test.com",
    "password": "test123",
    "persona": {
      "nombre": "Maria",
      "apellido": "Lopez",
      "dni": "99999991",
      "tipo_dni": "DNI",
      "sexo": "female",
      "fecha_nacimiento": "1985-05-15"
    }
  }
}
```

### 2.3 `POST /auth/register-profesional/` — Registro de profesional

```
HTTP POST
  │
  ▼
register_profesional(request)
  │
  ├── RegisterProfesionalSerializer(data=request.data)
  │     │
  │     ├── validate_matricula(matricula):
  │     │   └── RefepsService.consultar(matricula)
  │     │         │
  │     │         ├── REFEPS_MOCK=True  → busca en MATRICULAS_MOCK (dict Python)
  │     │         └── REFEPS_MOCK=False → llama API REFEPS real (NotImplementedError)
  │     │              │
  │     │              ├── None → ValidationError('Matrícula no válida')
  │     │              └── dict → guarda en self.context['datos_refeps']
  │     │
  │     └── create() @transaction.atomic:
  │           1. Personas.objects.create(
  │                nombre, apellido, dni, tipo_dni='DNI',
  │                sexo, fecha_nacimiento
  │              )
  │              └── Datos vienen del mock REFEPS, no del body
  │           2. Usuarios.objects.create_user(email, password, persona)
  │           3. UserRole.objects.create(
  │                rol='medico' si profesion=='Médico' else 'odontologo',
  │                user
  │              )
  │              └── Rol derivado del tipo de matrícula
  │           4. Profesionales.objects.create(matricula, id_usuario=user)
  │
  └── Response(201)
```

**Body de ejemplo:**
```json
{
  "email": "dra.acevedo@test.com",
  "password": "test123",
  "matricula": "541012497922"
}
```

**Matrículas mock disponibles:**
| Matrícula | Nombre | Profesión | Rol asignado |
|---|---|---|---|
| `541012497922` | Estela Rosa Acevedo | Médico | `medico` |
| `123456789` | Carlos López | Odontólogo | `odontologo` |

---

## 3. Patrones de diseño utilizados

### 3.1 Patrón Strategy — `RefepsService`

```
                     ┌─────────────────────┐
                     │   RefepsService      │
                     │                     │
                     │  + consultar(matr)   │──→ ¿REFEPS_MOCK?
                     └─────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     ┌────────────────┐            ┌────────────────────┐
     │ MATRICULAS_MOCK│            │ _consultar_real()  │
     │ (dict Python)  │            │ (API HTTP REFEPS)  │
     └────────────────┘            └────────────────────┘
```

**Qué hace:** El método `consultar()` decide en runtime qué estrategia usar (mock vs API real) mediante un feature toggle (`settings.REFEPS_MOCK`). Quien llama al servicio no sabe ni le importa de dónde vienen los datos.

**Cómo se cumple:** La interfaz es siempre `consultar(matricula: str) -> dict | None`. El serializer solo llama a ese método. Cuando se active REFEPS real, solo se modifica `_consultar_real()`, cero cambios en serializers o vistas.

---

### 3.2 Patrón Template Method — `UserSerializer.create()` con `context['rol']`

```
UserSerializer.create()
    │
    ├── 1. Personas.objects.create()          ← FIJO (siempre igual)
    ├── 2. Usuarios.objects.create_user()     ← FIJO (siempre igual)
    └── 3. UserRole.objects.create(           ← VARIABLE (rol por contexto)
              rol=self.context.get('rol', 'usuario')
          )
```

**Qué hace:** El esqueleto del algoritmo es fijo (crear persona → crear usuario → asignar rol). El paso 3 varía según quién invoca el serializer. El valor por defecto es `'usuario'` (para `register` genérico). Las vistas de `register_tutor` y `register_profesional` pasan `context={'rol': 'tutor'}` o `context={'rol': rol_matricula}`.

**Ventaja:** Un solo `UserSerializer` para todos los registros. Sin `if` ni herencia.

---

### 3.3 Patrón Composite — `RegisterTutorSerializer` anida `UserSerializer`

```
RegisterTutorSerializer (Serializer)
    │
    ├── usuario: UserSerializer()    ← sub-serializer anidado
    └── parentesco: CharField()
```

**Qué hace:** `RegisterTutorSerializer` es un `Serializer` (no `ModelSerializer`) que contiene otro serializer como campo. Cuando se valida, DRF valida recursivamente el `UserSerializer` interno. En `create()`, el serializer padre orquesta la creación: primero llama a `UserSerializer.save()` para crear Persona + Usuario + rol, luego crea `Responsables`.

**Body esperado:**
```json
{
  "parentesco": "madre",
  "usuario": {
    "email": "...",
    "password": "...",
    "persona": { ... }
  }
}
```

---

### 3.4 Patrón Thin View (Vista delgada)

```
Vista          → solo valida y responde (5 líneas)
Serializer     → toda la lógica de negocio y persistencia
```

**Qué hace:** Las vistas `register`, `register_tutor`, `register_profesional` y `login` siguen exactamente la misma estructura:

```python
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def algun_register(request):
    serializer = AlgunSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': '...'}, status=status.HTTP_201_CREATED)
    return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
```

**Ventajas:**
- La vista no conoce los modelos (`Personas`, `Usuarios`, `Responsables`). Solo conoce el serializer.
- Testeable: mockeás el serializer y probás la vista.
- Reutilizable: si mañana cambiás la lógica de creación, solo tocás el serializer.
- Consistente: todas las vistas de registro son idénticas en estructura.

---

### 3.5 Patrón Decorator — `@authentication_classes([])` + `@permission_classes([AllowAny])`

```
Request → 1. Authentication  →  2. Permission  →  3. View
              │                      │
    @authentication_classes([])   @permission_classes([AllowAny])
    (no ejecuta JWT)              (no exige autenticación)
```

**Qué hace:** Las vistas públicas anulan ambas etapas globales:
- `@authentication_classes([])` → ignora cualquier token (válido o inválido) en el header `Authorization`
- `@permission_classes([AllowAny])` → anula el `IsAuthenticated` global

**Por qué ambos:** Si solo ponés `AllowAny`, `JWTAuthentication` global igual corre y rechaza requests con token inválido *antes* de llegar al permiso.

---

### 3.6 Transaction Script — `@transaction.atomic` en los `create()` de serializers

```python
@transaction.atomic
def create(self, validated_data):
    persona = Personas.objects.create(...)     # paso 1
    user = Usuarios.objects.create_user(...)   # paso 2
    UserRole.objects.create(...)               # paso 3
    Responsables.objects.create(...)           # paso 4
    return user
```

**Qué hace:** Si cualquier paso falla, todos los anteriores se revierten. No quedan registros huérfanos. Ejemplo: si `Responsables.objects.create()` falla, la `Persona`, el `Usuario` y el `UserRole` creados se deshacen automáticamente.

---

## 4. Cómo seguir el patrón para futuros endpoints

### Regla 1 — Vista delgada

Toda vista de creación/modificación debe verse así:

```python
@api_view(['POST'])
@permission_classes([AlgunPermiso])
def mi_endpoint(request, ...):
    serializer = MiSerializer(data=request.data, context={...})
    if serializer.is_valid():
        resultado = serializer.save()
        return Response({'message': '...', 'data': ...}, status=201)
    return Response({'error': serializer.errors}, status=400)
```

**No** pongas `Model.objects.create()` ni `get_object_or_404()` de modelos de negocio en la vista.

### Regla 2 — Serializadores planos para flujos compuestos

Cuando un endpoint crea múltiples entidades (ej: Persona + Usuario + Responsables), usá un `serializers.Serializer` (no `ModelSerializer`) que orqueste la creación:

```python
class MiSerializerCompuesto(serializers.Serializer):
    campo_a = OtroSerializer()       # sub-serializer anidado
    campo_b = serializers.CharField()

    @transaction.atomic
    def create(self, validated_data):
        # 1. crear entidad A
        # 2. crear entidad B
        # 3. relacionarlas
        return resultado
```

### Regla 3 — `ModelSerializer` solo para CRUD simple

Usá `ModelSerializer` cuando el endpoint mapea 1:1 con un modelo (ej: `UserSerializer` → `Usuarios`, `PersonasSerializer` → `Personas`). Para flujos multi-tabla, usá `Serializer` compuesto.

### Regla 4 — Servicios externos con feature toggle

Siempre que integres una API externa (REFEPS, RENAPER, etc.), seguí el patrón de `RefepsService`:

```python
class ServicioExterno:
    @classmethod
    def consultar(cls, parametro):
        if getattr(settings, 'MOCK_SERVICIO', False):
            return cls._mock(parametro)
        return cls._real(parametro)
```

Nunca llames APIs externas desde serializers o vistas directamente.

### Regla 5 — Roles por contexto, no hardcodeados

El `UserSerializer` acepta `self.context.get('rol', 'usuario')`. Al usarlo desde otro serializer o vista, siempre pasá `context={'rol': '...'}`.

### Regla 6 — Vistas públicas con doble decorador

```python
@permission_classes([AllowAny])
@authentication_classes([])
```

Los dos. Siempre. Sin excepción.

---

## 5. Arquitectura final de archivos

```
authentication/
├── serializers.py
│   ├── UserSerializer              ← Persona + Usuario + rol (por context)
│   ├── RolesSerializer             ← solo ['rol', 'ruta']
│   ├── UserRoleSerializer          ← asignación de rol (admin)
│   ├── LoginSerializer             ← validate() con authenticate()
│   ├── RegisterTutorSerializer     ← compuesto: UserSerializer + Responsables
│   └── RegisterProfesionalSerializer ← compuesto: REFEPS + Persona + Usuario + Profesionales
│
├── views.py
│   ├── register()                  → UserSerializer
│   ├── register_tutor()            → RegisterTutorSerializer
│   ├── register_profesional()      → RegisterProfesionalSerializer
│   ├── login()                     → LoginSerializer + getCustomToken()
│   ├── asignar_rol()               → UserRoleSerializer (EsAdmin)
│   └── solo_medicos()              → test endpoint (EsMedico)
│
├── permissions.py
│   ├── TieneRol (base)
│   ├── EsMedico, EsOdontologo, EsTutor, EsAyudante
│   └── EsAdmin (usa is_superuser)
│
├── models.py                       ← Usuarios, Roles, UserRole, UserManager
└── urls.py                         ← todas las rutas

professionals/
├── models.py                       ← Profesionales, Matriculas
└── services/
    └── services_refeps.py          ← RefepsService (mock + real)

patients/
├── models.py                       ← Responsables, Pacientes, Antecedentes...
└── serializers.py                  ← ResponsablesSerializer, PacientesSerializer
```

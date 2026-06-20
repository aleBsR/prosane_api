# Flujo completo del sistema PROSANE

> Documento formal del flujo de trabajo, basado en la descripción del producto.

---

## 1. Roles del sistema

| Rol | Descripción |
|-----|-------------|
| **Tutor** | Padre/madre/tutor del alumno. Se registra y carga los datos del alumno. |
| **Ayudante** | Coordinador del operativo. Crea el operativo, asigna escuela y profesionales, sube la nómina de alumnos, y lo envía a los profesionales. |
| **Médico** | Profesional de la medicina asignado al operativo. Recibe los operativos pendientes, accede al listado de alumnos y completa el CIS (Control Integral de Salud). |
| **Odontólogo** | Profesional de la odontología asignado al operativo. Mismo flujo que el médico. |

---

## 2. Flujo de trabajo

### 2.1 Tutor — Registro

```
[App Flutter]                      [API]                           [DB]
     │                               │                              │
     ├─ POST /auth/register/tutor ──►│                              │
     │  {datos del tutor}            │                              │
     │                               ├─ Crea Persona ──────────────►│
     │                               ├─ Crea Usuario ──────────────►│
     │                               ├─ Crea Tutor ────────────────►│
     │◄──── 201 + JWT ───────────────┤                              │
     │                               │                              │
     ├─ POST /tutor/alumnos ─────────►                              │
     │  {datos del alumno}           │                              │
     │                               ├─ Crea Persona ──────────────►│
     │                               ├─ Crea Paciente (vinculado   │
     │                               │   al tutor) ────────────────►│
     │◄──── 201 + datos del alumno ──┤                              │
```

**Pantallas (Flutter):**
1. Registro del tutor (nombre, apellido, DNI, email, teléfono, password)
2. Carga del alumno (nombre, apellido, DNI, fecha_nac, sexo, obra social)

### 2.2 Ayudante — Creación del operativo

```
Ayudante                           API                              DB
  │                                 │                               │
  ├─ POST /operativos ─────────────►│                               │
  │  {escuela, fecha, lugar}        │                               │
  │                                 ├─ Crea Operativo (borrador) ► │
  │◄──── 201 + datos ───────────────┤                               │
  │                                 │                               │
  ├─ POST /operativos/{id}/        │                               │
  │   profesionales/asignar ───────►│                               │
  │  {profesional_id, rol}         │                               │
  │                                 ├─ Crea OperativoProfesional ► │
  │                                 │  (valida conflicto de fecha)  │
  │◄──── 201 o 409 ─────────────────┤                               │
  │                                 │                               │
  ├─ POST /operativos/{id}/        │                               │
  │   alumnos/importar-csv ────────►│                               │
  │  [archivo CSV]                  │                               │
  │                                 ├─ Parsea CSV                  │
  │                                 ├─ Crea Persona/Paciente (si   │
  │                                 │   no existe)                  │
  │                                 ├─ Crea OperativoAlumno ──────►│
  │◄──── 200 + resumen ─────────────┤                               │
  │                                 │                               │
  ├─ POST /operativos/{id}/        │                               │
  │   confirmar ───────────────────►│                               │
  │                                 ├─ Valida:                     │
  │                                 │  • estado = borrador          │
  │                                 │  • ≥ 1 profesional asignado   │
  │                                 │  • ≥ 1 alumno en nómina      │
  │                                 │  • sin conflictos de fecha    │
  │                                 ├─ Estado → confirmado ───────►│
  │◄──── 200 ───────────────────────┤                               │
```

**Pantallas (Flutter):**
1. Listado de operativos (creados por el ayudante)
2. Formulario: escuela + fecha + lugar
3. Asignar profesionales (buscador por email/rol)
4. Subir archivo CSV
5. Confirmar operativo (resumen + botón confirmar)
6. Detalle del operativo (alumnos importados, profesionales asignados)

### 2.3 Médico / Odontólogo — Ejecución del operativo

```
Médico/Odontólogo                  API                              DB
  │                                 │                               │
  ├─ GET /operativos?              │                               │
  │   estado=confirmado ───────────►│                               │
  │                                 ├─ Filtra operativos donde     │
  │                                 │   el profesional está asignado│
  │◄──── [{operativos}] ────────────┤                               │
  │                                 │                               │
  ├─ GET /operativos/{id}/         │                               │
  │   alumnos ─────────────────────►│                               │
  │                                 ├─ Lista alumnos del operativo │
  │◄──── [{alumnos}] ───────────────┤                               │
  │                                 │                               │
  ├─ PATCH /operativos/{id}/       │                               │
  │   alumnos/{id} ────────────────►│                               │
  │  {estado: "presente"}          │                               │
  │                                 ├─ Marca asistencia ──────────►│
  │◄──── 200 ───────────────────────┤                               │
  │                                 │                               │
  ├─ POST /cis ─────────────────────►  (SEGUNDA ETAPA)             │
  │  {alumno, datos del control}   │                               │
```

**Pantallas (Flutter):**
1. **Inicio**: Listado de operativos asignados (pendientes/en_curso/finalizados)
2. **Operativo**: Listado de alumnos con su estado (pendiente/presente/ausente/evaluado)
3. **Alumno**: Marcar presente/ausente + cargar datos del CIS (segunda etapa)

---

## 3. Primera etapa — Alcance

### 3.1 Backend (API — lo que construimos ahora)

| Módulo | Endpoints | Estado |
|--------|-----------|--------|
| **Auth** | `POST /auth/login/`, `POST /auth/register/tutor/` | 🔜 Hacer |
| | `POST /auth/refresh/`, `POST /auth/logout/` | 🔜 Hacer |
| | `GET /auth/me/` | 🔜 Hacer |
| **Tutor (registro)** | `POST /tutores/registrar/` (crea Persona + Usuario + Tutor + JWT) | 🔜 Hacer |
| **Alumno** | `POST /tutores/{id}/alumnos/` (crea Persona + Paciente vinculado al tutor) | 🔜 Hacer |
| | `GET /tutores/{id}/alumnos/` (lista alumnos del tutor) | 🔜 Hacer |
| **Escuelas** | `GET /escuelas/`, `POST /escuelas/` | 🔜 Hacer |
| | `GET /escuelas/{id}/`, `PUT/PATCH /escuelas/{id}/` | 🔜 Hacer |
| | `DELETE /escuelas/{id}/` (soft delete) | 🔜 Hacer |
| | `GET /escuelas/{id}/cursos/`, `POST /escuelas/{id}/cursos/` | 🔜 Hacer |
| **Operativos** | `GET /operativos/`, `POST /operativos/` | 🔜 Hacer |
| | `GET /operativos/{id}/`, `PUT/PATCH /operativos/{id}/` | 🔜 Hacer |
| | `DELETE /operativos/{id}/` (cancelar) | 🔜 Hacer |
| | `POST /operativos/{id}/confirmar/` | 🔜 Hacer |
| | `POST /operativos/{id}/cancelar/` | 🔜 Hacer |
| | `POST /operativos/{id}/finalizar/` | 🔜 Hacer |
| **Profesionales en operativo** | `GET /operativos/{id}/profesionales/` | 🔜 Hacer |
| | `POST /operativos/{id}/profesionales/asignar/` | 🔜 Hacer |
| | `DELETE /operativos/{id}/profesionales/{id}/remover/` | 🔜 Hacer |
| **Alumnos en operativo** | `GET /operativos/{id}/alumnos/` (filtro por estado) | 🔜 Hacer |
| | `POST /operativos/{id}/alumnos/importar-csv/` | 🔜 Hacer |
| | `PATCH /operativos/{id}/alumnos/{id}/` (marcar presente/ausente) | 🔜 Hacer |

**Nota sobre permisos:** Todos los endpoints usan `require_action('nombreAccion')` — sistema **data-driven**. Las acciones se definen en fixtures JSON y se cargan con `seed_all`. No hay permisos hardcodeados.

### 3.2 Lo que queda para segunda etapa

| Módulo | Endpoints |
|--------|-----------|
| **CIS** | `POST /cis/` (crear control integral de salud) |
| | `GET /cis/{paciente_id}/` (historial del alumno) |
| | `PUT/PATCH /cis/{id}/` (actualizar datos del control) |
| **Dashboard médico/odontólogo** | `GET /dashboard/profesional/` (resumen de operativos pendientes) |
| **Notificaciones** | Notificar al médico/odontólogo cuando se le asigna un operativo |
| **Reportes** | Exportar resultados del operativo |

---

## 4. Modelo de datos — Etapa 1

### Modelos existentes (no tocamos)
- `Persona` (apps.personas) — datos personales base
- `Usuario` (apps.usuarios) — login + roles
- `Tutor` (apps.tutores) — parentesco + FK a Persona + FK a Usuario
- `Paciente` (apps.pacientes) — FK a Persona + FK a Tutor + obra social
- `Escuela` (apps.escuelas) — datos de la escuela
- `Curso` (apps.escuelas) — curso dentro de una escuela

### Modelos nuevos
- `Action` + `RoleAction` (apps.usuarios) — sistema de permisos data-driven
- `Operativo` — escuela, fecha, lugar, estado, notas, created_by
- `OperativoProfesional` — operativo, profesional, rol, confirmado
- `OperativoAlumno` — operativo, paciente, curso, snapshots del CSV, estado

### Diagrama de relaciones

```
Persona ──1:1── Usuario ────M:N── Rol ────M:N── Action (via RoleAction)
   │
   │──1:1── Tutor
   │
   └──1:1── Paciente
              │
              └──1:N── OperativoAlumno ──N:1── Operativo ──N:1── Escuela
                          │                              │
                          │                              └──1:N── OperativoProfesional ──N:1── Usuario (profesional)
                          │
                          └──1:1── Curso
```

---

## 5. Prioridad de implementación

```
Orden             Depende de
─────             ──────────
1. Auth + Registro Tutor    —
   (login, register tutor)
2. Escuelas + Curso         —
4. Operativos               3 (escuela existe)
5. Servicios operativo      4 (operativo existe)
   (confirmar, CSV, etc.)
6. Endpoints operativos     5 (servicios existen)
```

---

## 6. Pantallas Flutter (referencia)

### Pantalla 1: Login
- Email + password
- Botón "Registrarse como tutor"

### Pantalla 2: Registro de tutor
- Nombre, apellido, DNI, email, teléfono, password
- Al registrarse, obtiene JWT y redirige al dashboard del tutor

### Pantalla 3: Dashboard del tutor
- Listado de sus alumnos registrados
- Botón "Agregar alumno"

### Pantalla 4: Cargar alumno
- Nombre, apellido, DNI, fecha de nacimiento, sexo, obra social

### Pantalla 5: Dashboard del ayudante
- Listado de operativos (creados por él)
- Botón "Nuevo operativo"
- Filtros por estado y fecha

### Pantalla 6: Crear operativo
- Seleccionar escuela (buscador)
- Fecha del operativo
- Lugar (escuela / centro de salud / otros)

### Pantalla 7: Detalle del operativo
- Datos del operativo (escuela, fecha, lugar, estado)
- Sección: Profesionales asignados (agregar/remover)
- Sección: Alumnos (subir CSV, ver listado, filtrar por estado)
- Botones: Confirmar / Cancelar / Finalizar (según estado)

### Pantalla 8: Dashboard del médico / odontólogo
- Listado de operativos asignados (pendientes / en curso / finalizados)
- Al entrar a uno, ve el listado de alumnos con su estado
- Puede marcar presente/ausente a cada alumno
- (Segunda etapa: completar CIS)

# Especificación: Operativo (agendamiento de visitas)

> Basado en el flujo descrito para el rol **Ayudante**.
> Los nombres de apps/modelos usan los reales de la rama `ale-base`.

---

## 1. Resumen del flujo

```
Ayudante                       Escuela                        Profesional(es)
   │                              │                              │
   ├─ Crea Operativo ─────────────┤                              │
   │  (escuela, fecha, lugar)     │                              │
   │                              │                              │
   ├─ Carga profesionales ────────┤                              │
   │  (médico, odontólogo, etc.)  │                              │
   │                              │                              │
   ├─ Sube nómina CSV ────────────┤                              │
   │  (alumnos de la escuela)     │                              │
   │                              │                              │
   ├─ Confirma operativo ─────────┼─────────────────────────────►│
   │                              │          Reciben notificación│
   │                              │                              │
   │                              │          Cada profesional    │
   │                              │◄─────────────────────────────┤
   │                              │  Carga resultados del examen │
   │                              │  (por cada alumno)           │
   │                              │                              │
   ├─ Cierra operativo ───────────┤                              │
   │  (cuando todos los          │                              │
   │   alumnos están evaluados)   │                              │
```

---

## 2. Modelos de datos

### 2.1 Catálogos

#### `Escuela` (`apps.escuelas.models.Escuela`)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID (PK) | BaseModel |
| nombre | varchar(200) | |
| cue | varchar(20) UNIQUE | nullable |
| ambito | varchar(20) | rural / urbana |
| sector_gestion | varchar(20) | estatal / privado / social_cooperativa |
| modalidad_educativa | varchar(10) | comun / especial |
| intercultural_bilingue | bool | default false |
| plurigrado_rural | bool | default false |
| domicilio | FK `personas.Domicilio` | nullable |
| telefono | varchar(20) | nullable |
| activa | bool | default true |

> `managed = True` — Django controla el schema.

#### `Curso` (`apps.escuelas.models.Curso`)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID (PK) | BaseModel |
| escuela | FK `Escuela` | |
| nivel | varchar(10) | inicial / primario / secundario |
| sala_grado_anio | varchar(20) | "Sala 5", "1°", "6°", "3° año" |
| division | varchar(10) | "A", "B" — nullable |
| ciclo_lectivo | int | ej: 2026 |

---

### 2.2 Núcleo operativo

#### `Operativo` (`apps.operativos.models.Operativo`)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID (PK) | BaseModel |
| nombre | varchar(200) | ej: "Operativo Escuela N° 4531 - Abril 2026" |
| escuela | FK `Escuela` | escuela donde se realiza |
| fecha | date | día del operativo |
| lugar_realizacion | varchar(20) | escuela / centro_salud / otros |
| estado | varchar(20) | borrador / confirmado / en_curso / finalizado / cancelado |
| notas | text | nullable |
| created_by | FK `usuarios.Usuario` | quien creó el operativo (el ayudante) |

**Máquina de estados:**

```
borrador ──► confirmado ──► en_curso ──► finalizado
                │                              ▲
                └── cancelado ──────────────────┘
```

#### `OperativoProfesional` (`apps.operativos.models.OperativoProfesional`)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID (PK) | BaseModel |
| operativo | FK `Operativo` | |
| profesional | FK `usuarios.Usuario` | el usuario profesional |
| rol_en_operativo | varchar(20) | medico / odontologo / ayudante |
| confirmado | bool | si el profesional confirmó asistencia |
| observaciones | text | nullable |

> `unique_together = (operativo, profesional)`

#### `OperativoAlumno` (`apps.operativos.models.OperativoAlumno`)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | UUID (PK) | BaseModel |
| operativo | FK `Operativo` | |
| paciente | FK `pacientes.Paciente` | nullable — se crea al procesar CSV |
| curso | FK `escuelas.Curso` | nullable |
| apellido | varchar(200) | snapshot del CSV |
| nombre | varchar(200) | snapshot del CSV |
| tipo_dni | varchar(10) | snapshot del CSV |
| dni | varchar(15) | snapshot del CSV |
| fecha_nacimiento | date | nullable |
| sexo | varchar(10) | nullable |
| estado | varchar(20) | pendiente / presente / ausente / evaluado |
| observaciones | text | nullable |

> `unique_together = (operativo, dni)`

**Flujo del alumno:**
```
pendiente ──► presente ──► evaluado
                  │
                  └── ausente
```

---

## 3. Endpoints

### Auth
| Método | URL | Acción |
|--------|-----|--------|
| POST | `/api/v1/auth/login/` | Obtener JWT |
| POST | `/api/v1/auth/refresh/` | Refrescar token |
| POST | `/api/v1/auth/logout/` | Cerrar sesión |
| GET | `/api/v1/auth/me/` | Perfil del usuario autenticado |

### Escuelas
| Método | URL | Permiso | Descripción |
|--------|-----|---------|-------------|
| GET | `/api/v1/escuelas/` | verEscuelas | Listar (filtro: ?activa, ?q) |
| POST | `/api/v1/escuelas/` | crearEscuela | Crear |
| GET | `/api/v1/escuelas/{id}/` | verEscuelas | Detalle |
| PUT/PATCH | `/api/v1/escuelas/{id}/` | editarEscuela | Actualizar |
| DELETE | `/api/v1/escuelas/{id}/` | eliminarEscuela | Soft delete |
| GET | `/api/v1/escuelas/{id}/cursos/` | verEscuelas | Listar cursos |
| POST | `/api/v1/escuelas/{id}/cursos/` | editarEscuela | Crear curso |

### Operativos
| Método | URL | Permiso | Descripción |
|--------|-----|---------|-------------|
| GET | `/api/v1/operativos/` | verOperativo | Listar (filtros) |
| POST | `/api/v1/operativos/` | crearOperativo | Crear |
| GET | `/api/v1/operativos/{id}/` | verOperativo | Detalle |
| PUT/PATCH | `/api/v1/operativos/{id}/` | editarOperativo | Actualizar |
| DELETE | `/api/v1/operativos/{id}/` | cancelarOperativo | Cancelar |
| POST | `/api/v1/operativos/{id}/confirmar/` | confirmarOperativo | Confirmar |
| POST | `/api/v1/operativos/{id}/finalizar/` | finalizarOperativo | Finalizar |
| POST | `/api/v1/operativos/{id}/cancelar/` | cancelarOperativo | Cancelar |
| GET | `/api/v1/operativos/{id}/profesionales/` | verOperativo | Listar profesionales |
| POST | `/api/v1/operativos/{id}/profesionales/asignar/` | gestionarProfesionalesEnOperativo | Asignar |
| DELETE | `/api/v1/operativos/{id}/profesionales/{id}/remover/` | gestionarProfesionalesEnOperativo | Remover |
| GET | `/api/v1/operativos/{id}/alumnos/` | verOperativo | Listar alumnos |
| POST | `/api/v1/operativos/{id}/alumnos/` | importarNominaOperativo | Agregar manual |
| PATCH | `/api/v1/operativos/{id}/alumnos/{id}/` | gestionarEstadoAlumnoEnOperativo | Cambiar estado |
| DELETE | `/api/v1/operativos/{id}/alumnos/{id}/` | editarOperativo | Remover alumno |
| POST | `/api/v1/operativos/{id}/alumnos/importar-csv/` | importarNominaOperativo | Subir CSV |

---

## 4. Permisos

| Acción | Roles |
|--------|-------|
| CRUD Escuela | ayudante, admin |
| CRUD Operativo | ayudante (solo propios), admin |
| Confirmar/Cancelar operativo | ayudante (solo propios), admin |
| Asignar/remover profesionales | ayudante (solo propios), admin |
| Importar CSV | ayudante (solo propios), admin |
| Ver operativo | ayudante (propios), médico (asignados), odontólogo (asignados), admin |
| Estado alumno | ayudante, médico (del operativo), odontólogo (del operativo) |

---

## 5. CSV — Formato esperado

```csv
apellido,nombre,tipo_dni,dni,fecha_nacimiento,sexo,curso
García,Juan,DNI,12345678,15/03/2015,M,1° A
Pérez,María,DNI,23456789,22/07/2014,F,1° A
```

- Encoding: UTF-8 o UTF-8-SIG (BOM de Excel)
- Separador: coma
- Fecha: DD/MM/YYYY
- Curso: texto libre, se matchea contra curso de la escuela

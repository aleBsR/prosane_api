# Sistema PROSANE — Propuesta de Diseño
## Documento para análisis y toma de decisiones arquitecturales

---

## Contexto general

Se está desarrollando una API REST con Django + DRF + JWT para el programa PROSANE
(Programa de Salud Escolar), cuyo objetivo es gestionar controles integrales de salud
a estudiantes en edad escolar en la provincia de Salta, Argentina.

El sistema involucra múltiples actores con distintos niveles de acceso y flujos de trabajo
diferenciados. Se necesita tomar decisiones de diseño sobre registro, autenticación,
roles y flujos de datos entre actores.

---

## Actores del sistema

| Actor | Descripción |
|---|---|
| `superusuario` | Administrador técnico del sistema. Gestiona desde el panel `/admin/` de Django |
| `profesional` | Médico u odontólogo que realiza los controles de salud en las escuelas |
| `ayudante` | Secretario o coordinador que agenda visitas y asigna equipos a escuelas |
| `tutor` | Padre, madre o tutor legal del paciente (alumno). Se registra desde la app |
| `paciente` | Alumno que recibe el control. No tiene cuenta propia en el sistema |

---

## Modelo de datos central

```
Tutor ──────────────────────── Paciente (alumno)
                                    │
                          ┌─────────┴──────────┐
                          │                    │
                       Escuela            Profesional
                          │                    │
                       Visita ───────────── Ficha/Control
                                                │
                                           Derivación
```

---

## Decisión 1 — ¿Quién puede registrar pacientes?

### Opción A — El tutor registra a sus hijos

**Flujo:**
1. El tutor se registra en la app con sus datos personales
2. Dentro de la app, el tutor puede agregar uno o más hijos (pacientes) con sus datos personales
3. El médico, al crear una ficha, busca el paciente por DNI
4. Si el paciente existe (cargado por el tutor), lo selecciona y continúa
5. Si el paciente no existe, el médico lo crea ingresando datos personales + DNI del tutor para vincularlo

**Ventajas:**
- El médico no pierde tiempo cargando datos personales de cada paciente
- El tutor tiene control sobre los datos de sus hijos desde el inicio
- La búsqueda por DNI es un punto de encuentro natural entre tutor y profesional

**Desventajas:**
- Requiere que el tutor se registre antes del control
- Si el tutor no se registró, el médico igual tiene que poder crear el paciente
- Validación de relación tutor-hijo queda pendiente para una fase posterior

**Casos borde a resolver:**
- Tutor no registrado al momento del control → el médico crea el paciente con DNI del tutor → cuando el tutor se registre, el sistema lo vincula automáticamente por DNI
- Un paciente puede tener más de un tutor (padre y madre)
- Un tutor puede tener más de un hijo en el sistema

---

### Opción B — Solo el profesional registra pacientes

**Flujo:**
1. El médico crea el paciente con todos sus datos durante el control
2. El tutor espera a que el médico cargue los datos para ver el estado

**Ventajas:**
- Flujo más simple, menos actores involucrados en el registro

**Desventajas:**
- El médico carga datos que el tutor podría haber cargado
- Mayor tiempo por control
- El tutor queda completamente dependiente del profesional

**Recomendación:** Opción A es superior. La Opción B genera cuello de botella en el
profesional y duplica trabajo innecesario.

---

## Decisión 2 — ¿Cómo se registran los profesionales?

### Opción A — Registro público con validación por matrícula

**Flujo:**
1. En la pantalla de registro, el sistema pregunta: ¿Sos tutor o profesional?
2. Si elige profesional → formulario de registro profesional
3. El sistema valida la matrícula ingresada contra una tabla pre-cargada por el superusuario
4. Si la matrícula es válida → se crea la cuenta con rol `profesional`
5. Si la matrícula no existe → registro rechazado

**Estructura de la tabla de matrículas:**
```
matriculas
──────────
id
numero          (único)
tipo            ('medico', 'odontologo')
utilizada       (boolean, default False)
id_profesional  (FK → profesional, null hasta que se use)
```

**Ventajas:**
- El profesional se autogestiona
- El superusuario solo carga matrículas, no crea cuentas una a una
- Control de acceso robusto — solo matrículas válidas pueden registrarse

**Desventajas:**
- El superusuario debe pre-cargar matrículas antes de que los profesionales se registren
- Requiere un endpoint de validación de matrícula

---

### Opción B — El superusuario crea la cuenta del profesional desde el admin

**Flujo:**
1. El superusuario crea la cuenta del profesional desde `/admin/`
2. El sistema genera una contraseña temporal
3. El profesional recibe sus credenciales (email + contraseña temporal)
4. Al primer login, el profesional puede cambiar su contraseña con un flujo de "olvidé mi contraseña"

**Ventajas:**
- Control total sobre quién es profesional
- No requiere tabla de matrículas
- Más simple de implementar

**Desventajas:**
- El superusuario es un cuello de botella — tiene que crear cada cuenta manualmente
- No escala bien si hay muchos profesionales

**Recomendación:** Opción B para la fase inicial (menos complejidad). Opción A para
fases posteriores cuando el sistema escale.

---

## Decisión 3 — ¿Cómo se gestionan las escuelas y visitas?

### Contexto importante

Un control escolar involucra múltiples profesionales simultáneamente
(ej: 3 médicos + 2 odontólogos para 50 alumnos). No hay un solo profesional
por escuela — hay un equipo asignado.

---

### Opción A — El ayudante gestiona escuelas y agenda visitas

**Flujo:**
1. El superusuario crea la cuenta del `ayudante` desde `/admin/`
2. El ayudante carga los datos de la escuela en el sistema
3. El ayudante agenda una visita a esa escuela (fecha + hora)
4. El ayudante asigna un equipo de profesionales a esa visita
5. En la vista del profesional aparece "Escuelas a visitar" con las visitas asignadas
6. El profesional llega a la escuela, busca el paciente por DNI y completa la ficha
7. En la ficha, el profesional solo completa observaciones escolares (del docente/director) y el control médico

**Estructura de datos:**
```
escuelas
────────
id, nombre, direccion, cue, nivel, turno, ...

visitas
───────
id
id_escuela      FK → escuelas
fecha
estado          ('programada', 'en_curso', 'finalizada')

visita_profesionales    (tabla pivot)
────────────────────────
id_visita       FK → visitas
id_profesional  FK → profesionales

fichas
──────
id
id_paciente     FK → pacientes
id_visita       FK → visitas
id_profesional  FK → profesionales  (quién hizo el control)
observacion_escolar
...campos del control médico
```

**Ventajas:**
- El profesional no pierde tiempo con logística — solo hace controles
- La escuela queda como entidad reutilizable — no se repiten datos
- El equipo por visita queda registrado formalmente
- Trazabilidad completa: qué profesional hizo qué control en qué visita

**Desventajas:**
- Requiere el rol `ayudante` y su gestión
- Mayor complejidad inicial

---

### Opción B — El profesional carga los datos de la escuela en cada ficha

**Flujo:**
1. El profesional crea una ficha
2. Carga datos de la escuela en esa ficha
3. Repite para cada paciente de esa escuela

**Problemas:**
- Datos de la escuela se repiten en cada ficha → inconsistencia
- Si se equivoca en un campo, hay que corregir N fichas
- No hay registro formal del equipo que visitó la escuela

**Mejora posible dentro de esta opción:**
Al crear la primera ficha de una escuela, el profesional la registra una vez
y las siguientes fichas la referencian. Pero esto termina siendo similar a la Opción A
sin la planificación previa.

**Recomendación:** Opción A es claramente superior para este dominio.
La logística previa (ayudante agenda) y la ejecución (profesional controla) son
responsabilidades naturalmente separadas.

---

## Decisión 4 — Vista del tutor

**Lo que el tutor puede ver:**

```
Vista del tutor
├── Mis hijos
│   ├── [Nombre del hijo]
│   │   ├── Estado: "Control realizado" / "Pendiente de control"
│   │   ├── Si fue controlado:
│   │   │   ├── Fecha del control
│   │   │   ├── Profesional que lo atendió
│   │   │   ├── Observaciones generales (las que el médico marque como visibles)
│   │   │   └── Derivaciones (si las hay) + estado de cada una
│   │   └── Si no fue controlado:
│   │       └── Mensaje: "Todavía no recibió el control"
```

**Regla de negocio importante:**
El tutor solo ve lo que el profesional marque como visible. No todos los campos
de la ficha médica son accesibles para el tutor — hay campos internos del sistema.

---

## Resumen de decisiones recomendadas

| Decisión | Recomendación | Justificación |
|---|---|---|
| ¿Quién registra pacientes? | Opción A — el tutor | Descomprime al profesional |
| ¿Cómo se registran profesionales? | Opción B en fase 1, Opción A en fases siguientes | Simplicidad inicial |
| ¿Cómo se gestionan escuelas? | Opción A — el ayudante | Separación de responsabilidades |
| Vista del tutor | Solo datos marcados como visibles por el profesional | Privacidad médica |

---

## Roles y permisos del sistema

| Rol | Puede | No puede |
|---|---|---|
| `superusuario` | Todo, desde `/admin/` | — |
| `ayudante` | Crear escuelas, agendar visitas, asignar equipos | Crear fichas, ver datos médicos |
| `profesional` | Crear/ver fichas, buscar pacientes, registrar derivaciones | Gestionar escuelas, ver otros profesionales |
| `tutor` | Ver estado y derivaciones de sus hijos | Ver ficha médica completa, crear fichas |

---

## Flujo completo del sistema — happy path

```
1. Superusuario crea cuentas de ayudantes y profesionales
2. Ayudante carga la escuela en el sistema
3. Ayudante agenda una visita y asigna el equipo de profesionales
4. Tutor se registra en la app y carga los datos de sus hijos
5. Profesional llega a la escuela, ve "Escuelas a visitar" en su vista
6. Profesional busca al paciente por DNI
   → Si existe: selecciona y crea la ficha
   → Si no existe: crea el paciente con DNI del tutor para vincularlo
7. Profesional completa el control: observaciones + datos médicos + derivaciones
8. Tutor abre la app y ve el estado del control de su hijo
9. Si hay derivación, el tutor ve el detalle y estado de la misma
```

---

## Preguntas abiertas para resolver en próximas fases

- ¿Cómo se valida la relación tutor-hijo? (DNI, documento legal, etc.)
- ¿Un paciente puede tener más de un tutor activo?
- ¿Las derivaciones tienen un flujo de seguimiento? (pendiente → en curso → resuelta)
- ¿El profesional puede ver fichas de controles anteriores del mismo paciente?
- ¿Hay notificaciones push para el tutor cuando se carga un control?
- ¿El sistema necesita funcionar offline en las escuelas con mala conectividad?

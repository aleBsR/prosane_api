# Etapa 3 — Modelo preliminar de datos

> **Fuente primaria**: planilla oficial PROSANE 2025 (`PLANILLA PROSANE 2025 FINAL...pdf`).
> Cada tabla de este documento se justifica con un bloque concreto de la planilla.

---

## Resumen ejecutivo

La planilla PROSANE define **4 bloques de carga**:

1. 👨‍👩‍👧 **Familia** (datos del NNA + antecedentes + consentimiento)
2. 🏫 **Escuela** (institución + nivel + observaciones)
3. 🩺 **Equipo de salud** (examen clínico + 12 sistemas + vacunación)
4. 🦷 **Odontólogo** (salud bucal + odontograma)

Más una sección transversal de **derivaciones** (19 especialidades) y la **constancia** final.

Esto se traduce en **~22 entidades** si cubrimos todo. Vamos a marcar cuáles van al **MVP** (Escenario A del proyecto) y cuáles quedan para **versión completa**.

---

## 1. Diagrama conceptual

```
                        ┌────────────────┐
                        │     Usuario    │  (auth + rol)
                        └────────┬───────┘
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
        ┌──────────┐       ┌──────────────┐   ┌─────────┐
        │ Familia  │       │ Profesional  │   │  Admin  │
        └─────┬────┘       └───────┬──────┘   └─────────┘
              │                    │
              │ tiene N            │ realiza N
              ▼                    │
        ┌──────────┐               │
        │   NNA    │ ◄─────────────┘
        └─────┬────┘
              │
              │ pertenece a 1
              ▼
    ┌─────────────────┐         ┌────────────────────┐
    │     Curso       │ ──N→1── │      Escuela       │
    └─────────────────┘         └────────────────────┘

NNA  ──1→N──  ControlIntegralSalud (CIS)  ──realizado_en──  InstitucionSalud
                       │
        ┌──────────────┼──────────────┬─────────────┬───────────┐
        ▼              ▼              ▼             ▼           ▼
   Antropometría  PresionArt.   AgudezaVisual  Audiometría  Vacunación
        │
        ▼
   HallazgoClinico (1-N por sistema)
        │
        ▼
   EvalOdontológica  ─1→N─  OdontogramaPieza
        │
        ▼
   Derivación (1-N)  ──refiere_a──  Especialidad (catálogo)
        │
        ▼
   Constancia (1-1, generada al cierre)
```

---

## 2. Tablas — agrupadas por bloque

### 🔐 2.1 Identidad y roles

#### `Usuario`
Tabla base (extiende `AbstractUser` de Django).

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| email | varchar(254) UNIQUE | login |
| password | varchar(128) | hash Django |
| first_name | varchar(150) | |
| last_name | varchar(150) | |
| rol | enum | `familia` / `profesional` / `escuela` / `admin` |
| is_active | bool | |
| date_joined | datetime | |

> 🟢 **MVP**

---

#### `PerfilFamilia`
Datos del adulto responsable (firma el consentimiento).

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| usuario_id | FK Usuario | 1-1 |
| dni | varchar(15) | |
| tipo_documento | enum | DNI/PAS/CI/LE/LC |
| telefono | varchar(20) | |
| domicilio_id | FK Domicilio | reutilizable |

> 🟢 **MVP**

---

#### `PerfilProfesional`
Médico, odontólogo u otro profesional autorizado.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| usuario_id | FK Usuario | 1-1 |
| dni | varchar(15) | |
| matricula | varchar(50) | |
| especialidad | varchar(100) | médico / odontólogo / pediatra / etc. |
| institucion_salud_id | FK InstitucionSalud | dónde trabaja |

> 🟢 **MVP**

---

#### `PerfilEscuela`
Director/docente que opera el panel desde la escuela.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| usuario_id | FK Usuario | |
| escuela_id | FK Escuela | |
| cargo | varchar(50) | director, docente, etc. |

> 🟢 **MVP**

---

### 🧒 2.2 Sujeto del control: el NNA

#### `NNA` (Niño/Niña/Adolescente)
Bloque "Datos del niño o adolescente" de la planilla.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| nombre | varchar(150) | |
| apellido | varchar(150) | |
| tipo_documento | enum | DNI/PAS/CI/LE/LC |
| dni | varchar(15) UNIQUE | |
| sexo | enum | F / M |
| fecha_nacimiento | date | |
| tiene_cud | bool | Certificado Único de Discapacidad |
| domicilio_id | FK Domicilio | |
| telefono_fijo | varchar(20) | nullable |
| celular | varchar(20) | nullable |
| familia_id | FK PerfilFamilia | |
| curso_actual_id | FK Curso | nullable, último curso registrado |
| created_at | datetime | |

> 🟢 **MVP**

---

#### `Domicilio`
Reutilizable por NNA y PerfilFamilia.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| calle | varchar(200) | |
| numero | varchar(20) | |
| piso | varchar(10) | nullable |
| departamento | varchar(10) | nullable |
| manzana | varchar(20) | nullable |
| casa_numero | varchar(20) | nullable |
| pieza | varchar(10) | nullable |
| provincia | varchar(80) | |
| departamento_provincia | varchar(80) | |
| localidad | varchar(120) | |

> 🟢 **MVP**

---

#### `CoberturaSalud`
Bloque "Cobertura de salud" — checkboxes de la planilla.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| nna_id | FK NNA | 1-1 (la última declarada) |
| tiene_obra_social | bool | incluye PAMI |
| obra_social_nombre | varchar(120) | nullable |
| tiene_programa_estatal | bool | AUH, Sumar+, etc. |
| programa_estatal_nombre | varchar(120) | nullable |
| tiene_plan_privado | bool | prepaga |
| plan_privado_nombre | varchar(120) | nullable |
| sin_cobertura | bool | |

> 🟢 **MVP**

---

### 🏫 2.3 Institucional

#### `Escuela`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| nombre | varchar(200) | |
| cue | varchar(20) UNIQUE | Código Único de Establecimiento |
| ambito | enum | rural / urbana |
| sector_gestion | enum | estatal / privado / social_cooperativa |
| modalidad_educativa | enum | comun / especial |
| intercultural_bilingue | bool | |
| plurigrado_rural | bool | |
| domicilio_id | FK Domicilio | |
| telefono | varchar(20) | nullable |

> 🟢 **MVP**

---

#### `Curso`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| escuela_id | FK Escuela | |
| nivel | enum | inicial / primario / secundario |
| sala_grado_anio | varchar(20) | "Sala 5", "1°", "6°", "3° año" |
| division | varchar(10) | "A", "B" |
| ciclo_lectivo | int | 2026 |

> 🟢 **MVP**

---

#### `InstitucionSalud`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| nombre | varchar(200) | |
| numero_efector | varchar(20) | "N° efector del centro de salud" |
| tipo | enum | caps / hospital / sanatorio / otro |
| domicilio_id | FK Domicilio | |
| telefono | varchar(20) | |

> 🟢 **MVP**

---

### 🩺 2.4 El Control Integral de Salud (CIS)

#### `ControlIntegralSalud` (CIS)
Entidad central — un CIS = una planilla.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| numero_planilla | varchar(50) | "Planilla N°" |
| nna_id | FK NNA | |
| ciclo_lectivo | int | |
| profesional_medico_id | FK PerfilProfesional | nullable |
| profesional_odontologo_id | FK PerfilProfesional | nullable |
| institucion_salud_id | FK InstitucionSalud | dónde se hizo |
| escuela_id | FK Escuela | snapshot de la escuela en este CIS |
| curso_id | FK Curso | snapshot del curso |
| fecha_examen | date | nullable hasta que se realice |
| examen_realizado | bool | |
| lugar_realizacion | enum | escuela / centro_salud |
| motivo_no_realizacion | enum nullable | negativa_familiar / ausente / negativa_nna / otros |
| estado | enum | iniciado / familia_completa / escuela_completa / clinico_completo / odontologico_completo / firmado / cerrado |
| observaciones | text | |
| created_at | datetime | |
| updated_at | datetime | |

> 🟢 **MVP**

---

### 👨‍👩‍👧 2.5 Bloque Familia (antecedentes y consentimiento)

#### `AntecedentesNNA`
Las ~16 preguntas Sí/No/No sabe del bloque familia.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| nacio_prematuro | enum | si / no / no_sabe |
| peso_nacimiento_kg | decimal(4,2) | nullable |
| convulsiones_epilepsia | enum | si / no / no_sabe |
| episodios_cardiorresp | enum | mareos, desmayos, dolor pecho |
| infecciones_urinarias | enum | |
| asma_espasmos | enum | |
| tuberculosis | enum | |
| diabetes | enum | |
| presion_arterial_alta | enum | |
| cardiopatia | enum | |
| traumatismo_internacion | enum | |
| diarrea_repeticion | enum | |
| problemas_oido | enum | |
| internado_alguna_vez | enum | |
| internado_causa | text | nullable |
| recibe_tratamiento | enum | |
| tratamiento_cual | text | nullable |
| algo_le_preocupa | enum | |
| que_le_preocupa | text | nullable |
| ultimo_control_medico | enum | menos_1_anio / mas_1_anio / no_recuerda |
| otros_problemas_salud | enum | |
| otros_problemas_cual | text | nullable |
| primera_menstruacion | enum | si/no/no_sabe (solo si sexo=F) |
| primera_menstruacion_fecha | date | nullable |
| primera_menstruacion_edad | int | nullable |

> 🟡 **MVP** parcial (con un subset de preguntas críticas: prematuro, asma, cardiopatía, diabetes, presión alta, tratamiento actual). El resto va a versión completa. **Decisión técnica**: como son muchos enums binarios, una alternativa pragmática es guardar en un solo campo JSON (`respuestas: {prematuro: "no", asma: "si", ...}`) y validar en serializer. Más flexible, menos columnas.

---

#### `AntecedentesFamiliares`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| problema_salud_familiar | enum | si / no / no_sabe |
| problema_salud_descripcion | text | nullable |
| muerte_subita_menor_50 | enum | si / no / no_sabe |

> 🟢 **MVP** (es chica, vale la pena)

---

#### `Consentimiento`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| adulto_nombre | varchar(200) | |
| adulto_apellido | varchar(200) | |
| adulto_tipo_documento | enum | |
| adulto_dni | varchar(15) | |
| firma_tipo | enum | adulto_responsable / nna_mayor_13 |
| firma_hash | varchar(128) | hash + timestamp para trazabilidad |
| fecha_firma | datetime | |

> 🟢 **MVP**

---

### 🏫 2.6 Bloque Escuela (datos del CIS)

#### `DatosEscuelaCIS`
Campos que la escuela completa por cada CIS.

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| algo_preocupa_nna | enum | si / no |
| que_preocupa_descripcion | text | nullable |
| dificultad_lenguaje | enum | si / no |
| bajo_tratamiento_lenguaje | enum | si / no / no_sabe |

> 🟢 **MVP**

> 💡 Los datos generales de la escuela (ámbito, sector, modalidad) ya están en la entidad `Escuela`, no se duplican acá.

---

### 🩺 2.7 Bloque clínico (equipo de salud)

#### `Antropometria`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| evaluado | bool | |
| peso_kg | decimal(5,2) | nullable |
| talla_cm | decimal(5,2) | nullable |
| imc | decimal(4,2) | calculado |
| percentil_talla | enum | menor_3 / mayor_igual_3 |
| percentil_imc | enum | menor_3 / 3_a_9 / 10_a_84 / 85_a_97 / mayor_97 |

> 🟢 **MVP**

---

#### `PresionArterial`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| evaluado | bool | |
| grupo_edad | enum | menor_16 / mayor_igual_16 |
| pas_mmhg | int | nullable |
| pad_mmhg | int | nullable |
| pas_categoria | enum | depende del grupo de edad |
| pad_categoria | enum | depende del grupo de edad |

> 🟢 **MVP**

---

#### `AgudezaVisual`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| evaluado | bool | |
| usa_lentes | bool | |
| ojo_derecho | enum | 1/10 a 10/10 |
| ojo_izquierdo | enum | 1/10 a 10/10 |

> 🟢 **MVP**

---

#### `Audiometria`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| realizado | bool | |
| resultado | enum | pasa / no_pasa |

> 🟢 **MVP**

---

#### `HallazgoClinico`
**Una fila por sistema evaluado**. La planilla tiene 12 sistemas:

```
1. Piel y faneras
2. Partes blandas
3. Cardiovascular
4. Respiratorio
5. Abdominal
6. Genitourinario (niños)
7. Genitourinario (niñas)
8. Osteoarticular
9. Neurológico
10. Salud visual (clínica)
11. Salud fonoaudiológica
12. I.C.V. (Índice Cintura/Talla u otro — verificar con experto)
```

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | |
| sistema | enum | uno de los 12 listados |
| estado | enum | con_hallazgos / sin_hallazgos / no_evaluado |
| hallazgos_especificos | varchar[] (Postgres ARRAY) o JSON | ["adenomegalia", "soplo"], etc. |
| otros_descripcion | text | nullable |

> 🟢 **MVP** (sin checklist de hallazgos específicos por sistema, eso va a versión completa).

---

#### `Vacunacion`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| trajo_carnet | bool | |
| carnet_completo | bool | |
| vacunas_aplicadas_in_situ | varchar[] | nombres de vacunas |
| vacunas_indicadas | varchar[] | si no se aplicaron |
| estado_general | enum | completas / en_curso / debe_completar |

> 🟢 **MVP**

---

### 🦷 2.8 Bloque Odontológico

#### `EvaluacionOdontologica`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| evaluado | bool | |
| salud_bucal_estado | enum | con_hallazgos / sin_hallazgos / no_evaluado |
| lesiones_tejidos_blandos | bool | |
| maloclusion | bool | |
| fluorosis | bool | |
| caries | bool | |
| otros_descripcion | text | nullable |
| topicacion_fluor | bool | |
| ensenanza_cepillado | bool | |
| alta_basica_odontologica | bool | |

> 🟢 **MVP**

---

#### `OdontogramaPieza`
Una fila por pieza dental evaluada (32 piezas adultas + 20 temporales).

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| evaluacion_odontologica_id | FK | |
| pieza_numero | int | numeración FDI (11-48 permanentes, 51-85 temporales) |
| componente | enum | C/c=cariada, P/p=perdida, O/o=obturada |
| tratamiento_tipo | enum | a_realizar (azul) / realizado (rojo) |

> 🔴 **No MVP** — es un componente complejo de UI. Va a versión completa.

---

### 🚑 2.9 Derivaciones

#### `Especialidad` (catálogo)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| nombre | varchar(80) UNIQUE | "Odontología", "Oftalmología", etc. |
| activo | bool | |

**Seed inicial** (19 especialidades de la planilla):
Odontología, Oftalmología, Nutrición, Vacunatorio, Pediatría, Fonoaudiología, Cardiología, Traumatología, Cirugía, Urología, ORL, Dermatología, Neurología, Trabajo Social, Psicología, Psicopedagogía, Agente Sanitario, Otros.

> 🟢 **MVP**

---

#### `Derivacion`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | |
| especialidad_id | FK Especialidad | |
| motivo | text | |
| centro_asistencial | varchar(200) | nullable |
| estado | enum | indicada / agendada / realizada / no_concretada |
| fecha_seguimiento | date | nullable |
| observaciones | text | nullable |

> 🟢 **MVP**

---

### 📜 2.10 Constancia (entregable de la app)

#### `Constancia`

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cis_id | FK CIS | 1-1 |
| nna_dni | varchar(15) | snapshot |
| nna_nombre_completo | varchar(200) | snapshot |
| nna_edad | int | snapshot |
| fecha_emision | date | |
| validez_hasta | date | +1 año desde emisión |
| peso_kg | decimal(5,2) | snapshot |
| altura_cm | decimal(5,2) | snapshot |
| vacunas_estado | enum | completas / en_curso / debe_completar |
| observaciones | text | |
| matricula_firmante | varchar(50) | |
| profesional_nombre | varchar(200) | snapshot |
| firma_hash | varchar(128) | SHA-256 del payload + timestamp |
| timestamp_firma | datetime | |
| pdf_url | varchar(500) | path en storage |

> 🟢 **MVP**

> ⚠️ **Importante**: la constancia guarda **snapshots** de los datos del NNA y profesional al momento de la emisión, **no FKs vivas**. Si después se cambia el nombre del NNA en la app, la constancia emitida hace 6 meses no se modifica retroactivamente.

---

## 3. Resumen — qué va al MVP

| Categoría | Tablas |
|-----------|--------|
| 🟢 **MVP completo** | Usuario, PerfilFamilia, PerfilProfesional, PerfilEscuela, NNA, Domicilio, CoberturaSalud, Escuela, Curso, InstitucionSalud, ControlIntegralSalud, AntecedentesFamiliares, Consentimiento, DatosEscuelaCIS, Antropometria, PresionArterial, AgudezaVisual, Audiometria, HallazgoClinico, Vacunacion, EvaluacionOdontologica, Especialidad, Derivacion, Constancia |
| 🟡 **MVP parcial** | AntecedentesNNA (subset de preguntas, resto en JSON) |
| 🔴 **No MVP** | OdontogramaPieza (UI compleja, va en versión completa) |

**Total para MVP**: **24 tablas** (21 entidades de negocio + 3 de identidad/auth).

---

## 4. Decisiones de diseño relevantes

1. **Snapshot vs FK viva en `Constancia`**:
   La constancia es un documento legal con validez 1 año. Los datos se "congelan" al momento de la firma. Si el NNA cambia de escuela 3 meses después, la constancia sigue diciendo la escuela anterior.

2. **JSON vs columnas en `AntecedentesNNA`**:
   Hay 16+ preguntas Sí/No/No sabe. Modelarlas como columnas explota el schema. Recomiendo **JSONField** de Django + validación en serializer DRF. Se mantiene queryable en Postgres con `->>` y JSONB.

3. **Catálogo `Especialidad` separado**:
   Las 19 especialidades de la planilla pueden cambiar. Si las dejamos hardcodeadas en un enum, cada cambio = migración. Mejor catálogo con seeds.

4. **Estado del CIS (máquina de estados)**:
   El campo `estado` en `CIS` modela un workflow real:
   `iniciado → familia_completa → escuela_completa → clinico_completo → odontologico_completo → firmado → cerrado`
   En código Django se valida con `django-fsm` o transiciones manuales en `services.py`.

5. **Domicilio reutilizable**:
   NNA, PerfilFamilia, Escuela e InstitucionSalud comparten el mismo schema de domicilio. Una sola tabla `Domicilio` con FK desde cada uno evita duplicar 9 columnas.

6. **`HallazgoClinico` es 1-N con CIS, no 1-1**:
   Cada uno de los 12 sistemas evaluados es una fila. Permite agregar sistemas nuevos sin tocar el schema.

7. **Trazabilidad en `Constancia`**:
   El `firma_hash` es SHA-256 del JSON serializado del CIS al momento de la firma + timestamp + matrícula. Sirve como "prueba" de no alteración para el Escenario A (sin AC, ver `resumen-validacion-para-socio.md`).

---

## 5. Preguntas abiertas (a validar con experto / socio)

1. **I.C.V.** en hallazgos clínicos — ¿qué es exactamente? ¿Índice Cintura/Talla? Hay que confirmar con un médico.
2. **Numeración del odontograma** — ¿FDI o universal? (FDI es estándar internacional, mayoritario en Argentina).
3. **`numero_planilla`** — ¿lo asigna el efector o lo genera la app? Si lo asigna el efector hay que dejar el campo opcional al inicio del CIS.
4. **`numero_efector`** — ¿es el número SISA del CAPS? Hay que cruzar con la documentación de SISA.
5. **Vacunas indicadas / aplicadas** — ¿usamos catálogo cerrado de vacunas (calendario nacional) o texto libre?
6. **Multi-año del NNA**: si un alumno se controla en 1° y después en 6°, son **2 CIS distintos** del **mismo NNA**. ¿Borramos los datos viejos? No: histórico completo.

---

## 6. Próximos pasos sobre este modelo

Cuando aprobemos esta versión:

1. **Generar las migraciones Django** (`apps/salud/models.py` + `apps/users/models.py` + `apps/escuelas/models.py`).
2. **Diagrama ER visual** (`django-extensions` con `graph_models` lo genera automático en PNG).
3. **Crear seeds** de prueba (1 escuela + 5 NNA + 1 profesional + 1 CIS de cada estado).
4. **Definir endpoints DRF** correspondientes a cada entidad — iría en `05-endpoints-api.md`.

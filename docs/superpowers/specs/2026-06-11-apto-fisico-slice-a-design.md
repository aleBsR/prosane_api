# Diseño: Apto Físico — Slice A ("apto mínimo firmable")

- **Fecha:** 2026-06-11
- **Estado:** Diseño aprobado en brainstorming. Pendiente: revisión del spec → plan → implementación.
- **Primera feature de DOMINIO** del backend (las anteriores fueron el cimiento auth/permisos).

---

## 1. Contexto y alcance

El **"apto físico"** del front (`crearApto`/`firmarApto`) mapea a la **`Constancia`** del
dominio (`docs/modelo-de-datos.md` §2.10): el certificado firmado que sale de un Control
Integral de Salud (CIS). El flujo completo es:

```
FAMILIA: datos del niño + antecedentes + consentimiento  →  PROFESIONAL: examen → crearApto → firmarApto → APTO (Constancia firmada)
```

El panel de la familia (datos del niño, antecedentes) **ya está modelado** en `patients`
(`Pacientes`, `Antecedentesfamiliares`, `Antecedentespersonales`). Lo que falta es el
**apto/deliverable del profesional**.

**Slice A = apto mínimo firmable, STANDALONE** (desacoplado del CIS completo y del bloque
clínico, que vienen en slices posteriores). Objetivo: encender los botones
`crearApto`/`firmarApto` del menú con un flujo real, y reconciliar `pacientes` de paso.

**Fuera de Slice A** (slices siguientes): Consentimiento (B); CIS + bloque clínico
antropometría/presión/etc. (C). Cuando exista el CIS, el apto se deriva de él (`cis_id`).

---

## 2. App y modelo

- **Nueva app Django `health`** (del mapa de `docs/arquitectura.md`). Sus modelos son
  `managed=True` (tablas propias, sin desfasaje).
- **Modelo `Apto`** (tabla `aptos`, `managed=True`, hereda `common.BaseModel`).
  `Apto` es el vocabulario del front/feature; es la versión standalone de la `Constancia`
  del dominio.

```
Apto
  # --- relaciones vivas (para el borrador) ---
  paciente        FK → patients.Pacientes       NOT NULL   # NNA del apto
  profesional     FK → authentication.Usuarios  NOT NULL   # quién lo crea/firma
  estado          CharField  'borrador' | 'firmado'   default 'borrador'

  # --- editable mientras está en borrador ---
  peso_kg         Decimal(5,2)  null
  altura_cm       Decimal(5,2)  null
  observaciones   Text          blank, default ''

  # --- SNAPSHOTS: se congelan al firmar (no FKs vivas) ---
  nna_dni              CharField  null
  nna_nombre_completo  CharField  null
  nna_edad             Integer    null
  profesional_nombre   CharField  null
  matricula_firmante   CharField  null

  # --- firma ---
  fecha_emision    Date      null
  validez_hasta    Date      null          # fecha_emision + 1 año
  firma_hash       CharField(128)  null    # SHA-256 del payload de snapshots + timestamp
  timestamp_firma  DateTime  null

  (+ id/created_at/updated_at/... de BaseModel)
```

**Diferido** (slices siguientes): `cis_id` (Slice C), `pdf_url` (generación de PDF),
`vacunas_estado` (bloque Vacunación).

---

## 3. Ciclo de vida (máquina de estados)

```
crearApto   → crea Apto en 'borrador'; peso/altura/observaciones editables
PATCH apto  → edita el borrador (SOLO si estado='borrador')
firmarApto  → congela snapshots (NNA + profesional) + calcula firma_hash
              + fecha_emision/validez_hasta + timestamp_firma → estado='firmado'
              → INMUTABLE: cualquier PATCH posterior responde 409 Conflict
```

- **Snapshots al firmar:** al `firmarApto`, se copian del Paciente/Persona vivos
  (`nna_dni`, `nna_nombre_completo`, `nna_edad`) y del profesional (`profesional_nombre`,
  `matricula_firmante`), y se congelan. Si después cambian los datos vivos, el apto
  firmado **no muta** (documento legal).
- **Inmutabilidad:** una vez `firmado`, no se edita ni se re-firma.

---

## 4. `firma_hash` (alcance honesto)

`firma_hash` = **SHA-256** de un string canónico de los campos snapshot + `timestamp_firma`.
Es **integridad / tamper-evidence**: si alguien altera la fila firmada, el hash deja de
coincidir. **NO es una firma digital criptográfica** (no hay clave privada / PKI). Una
firma digital real (con certificado del profesional) queda para una etapa posterior. Se
documenta así para no dar una garantía que no provee.

---

## 5. Endpoints (`health.urls`, montado en `/api/v1/aptos/`)

| Método | Ruta | `require_action` | Notas |
|---|---|---|---|
| POST | `/api/v1/aptos/` | `crearApto` | crea borrador para un `paciente` |
| GET | `/api/v1/aptos/` y `/<id>/` | `verApto` | listar / ver (acción nueva, abajo) |
| PATCH | `/api/v1/aptos/<id>/` | `crearApto` | editar borrador (409 si firmado) |
| POST | `/api/v1/aptos/<id>/firmar/` | `firmarApto` | firma + congela + inmutable |

Vistas **delgadas**; la lógica (`crear_apto`, `editar_apto`, `firmar_apto`) en
`health/services.py`.

### Acción nueva `verApto` (se crea siguiendo `docs/reglas/crear-accion.md`)
- En `authentication/fixtures/actions.json` (UUID fijo nuevo `a0000000-...-09`):
  ```
  name: "verApto", label: "Ver apto físico", icon: "fact_check", color: "#2E7D32",
  type: "list", category: "salud", is_sensitive: true, sort_order: 45
  ```
- En `role_actions.json`: vincular a **medico (2)** y **odontologo (3)** (el superadmin la
  ve automáticamente). Recargar con `reset_permissions_data`.

---

## 6. Reconciliación #12 que dispara

Slice A toca `pacientes` (lee `paciente` y `paciente.persona` para snapshots). Antes de
implementar:
- **Verificar las columnas reales de `pacientes`** (como hicimos con Personas: ¿`id` int?
  ¿tiene columnas de auditoría de BaseModel?) y **reconciliar el modelo `Pacientes`** a la
  realidad (id correcto + solo las columnas reales / sin heredar de más).
- `persona` ya está reconciliada ✅. `responsables`/`domicilio` **no** las toca Slice A.

---

## 7. Testing (TDD)

- Pure/servicios: `crear_apto` → estado borrador; `editar_apto` en borrador OK; en firmado → error; `firmar_apto` congela snapshots + setea firma_hash/fecha/validez/timestamp + estado firmado; `firma_hash` cambia si cambia el payload (integridad).
- Endpoints: `crearApto` (médico crea, tutor 403); `firmarApto`; PATCH a firmado → 409; GET con `verApto`.
- Equivalencia/contrato no aplica acá (es feature nueva, no el /me).

---

## 8. Decisiones cerradas (Roberto)
- Slice A (apto mínimo firmable standalone), no el CIS completo.
- Ciclo: **borrador editable → firmado inmutable**.
- Nombre del modelo: **`Apto`**.
- Lectura: acción nueva **`verApto`** (estrena el playbook).

## 9. Pendiente de confirmar al implementar
- Columnas reales de `pacientes` (condiciona la reconciliación).
- Montaje de `health.urls` en `config/urls.py` (prefijo `/api/v1/aptos/`).

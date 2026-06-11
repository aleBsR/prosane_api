# Diseño: Consentimiento — Slice B

- **Fecha:** 2026-06-11
- **Estado:** Diseño aprobado en brainstorming. Pendiente: revisión del spec → plan → implementación.
- **Segunda feature de dominio** (después del apto, Slice A). Completa el panel de la familia.

---

## 1. Contexto y alcance

El **consentimiento** es obligatorio antes de cualquier control (Ley 26.529). Los
adolescentes **≥13 pueden consentir por sí mismos** (autonomía progresiva) — de ahí el
`firma_tipo`. La acción `darConsentimiento` ya está sembrada (rol **tutor**).

Es la etapa que falta del **panel de la familia** (datos del niño + antecedentes ya
existen en `patients`). Paralelo simple del apto: como `Consentimiento` depende de
`cis_id` (CIS, que aún no existe), va **standalone, linkeado al Paciente**; cuando exista
el CIS se enganchará (`cis_id`) sin romper el contrato.

**Slice B = registrar el consentimiento.** Vive en la app **`patients`** (decisión previa:
"consent dentro de patients").

**Fuera de Slice B:** la regla cross-cutting "no se puede crear un apto/control sin
consentimiento previo" queda **desacoplada** por ahora (se implementa cuando esté el CIS).
Revocación de consentimiento: futuro.

---

## 2. Modelo `Consentimiento` (app `patients`, `managed=True`, hereda `BaseModel`)

```
Consentimiento
  paciente              FK → patients.Pacientes   NOT NULL   # el NNA (standalone; luego cis_id)
  firma_tipo            CharField  'adulto_responsable' | 'nna_mayor_13'

  # identidad de quien consiente (la manda el front explícita, se snapshotea)
  adulto_nombre         CharField(200)
  adulto_apellido       CharField(200)
  adulto_tipo_documento CharField(20)
  adulto_dni            CharField(15)   # write_only: se acepta al crear, NO se devuelve

  # firma / trazabilidad
  firma_hash            CharField(128)  # SHA-256 de identidad + timestamp
  fecha_firma           DateTimeField

  (+ id UUID / created_at / created_by=quién lo registró / ... de BaseModel)
```

> Se mantienen los nombres `adulto_*` del dominio (`modelo-de-datos.md` §2.5) aunque en
> `firma_tipo='nna_mayor_13'` guarden los datos del propio NNA. Fidelidad con la fuente de
> verdad; no se inventa vocabulario nuevo.

`adulto_dni` es `write_only` (mismo criterio que el `dni` del NNA en #15: dato sensible,
no se filtra en respuestas; la integridad la da `firma_hash`).

---

## 3. Ciclo de vida: un paso (crear = consentir)

```
darConsentimiento → POST crea el Consentimiento YA firmado:
   - snapshot de la identidad (firma_tipo + nombre/apellido/tipo_doc/dni del request)
   - fecha_firma = now
   - firma_hash = SHA-256(payload de identidad + timestamp)
   → INMUTABLE (un consentimiento dado es un acto legal; no se edita ni se re-firma)
```

No hay estado borrador. No hay PATCH.

---

## 4. `firma_hash` (alcance honesto)

SHA-256 de un string canónico de `firma_tipo + adulto_nombre/apellido/tipo_documento/dni +
fecha_firma`. Es **integridad / trazabilidad** (si se altera la fila, el hash no coincide),
**no** una firma criptográfica con clave. Igual criterio que el apto.

---

## 5. Endpoints (`patients`, montados en `/api/v1/consentimientos/`)

| Método | Ruta | `require_action` | Notas |
|---|---|---|---|
| POST | `/api/v1/consentimientos/` | `darConsentimiento` | crea el consentimiento (tutor) |
| GET | `/api/v1/consentimientos/` y `/<uuid>/` | `verConsentimiento` | listar / ver (acción nueva) |

Body del POST: `{ paciente, firma_tipo, adulto_nombre, adulto_apellido, adulto_tipo_documento, adulto_dni }`.
Vistas delgadas; la lógica (`crear_consentimiento`) en `patients/services.py`.

### Acción nueva `verConsentimiento` (vía `docs/reglas/crear-accion.md`)
- En `authentication/fixtures/actions.json` (UUID fijo nuevo `a0000000-...-10`):
  ```
  name: "verConsentimiento", label: "Ver consentimiento", icon: "fact_check",
  color: "#455A64", type: "list", category: "consentimiento", is_sensitive: true, sort_order: 25
  ```
- En `role_actions.json`: vincular a **medico (2)**, **odontologo (3)** y **tutor (4)**
  (el profesional verifica que haya consentimiento antes del control; el tutor ve el suyo).
- ⚠️ **Espejar en `authentication/actions_map.py`** (`ROLE_ACTIONS` de medico/odontologo/tutor)
  o se rompe el test de equivalencia Fase1≡Fase2 (paso ya documentado en el playbook).
- Recargar con `reset_permissions_data`.

---

## 6. Reconciliación #12

**Ninguna nueva.** `pacientes` ya quedó reconciliada en Slice A. `Consentimiento` es
`managed=True` (tabla propia nueva).

> Nota: `patients` aún no tiene migraciones (sus modelos eran `managed=False`).
> `makemigrations patients` creará `patients/migrations/0001_initial.py` con **solo**
> `Consentimiento` (los modelos `managed=False` se excluyen de las migraciones).

---

## 7. Testing (TDD)

- Servicio `crear_consentimiento`: crea el registro con `firma_hash` + `fecha_firma`
  seteados; el hash cambia si cambia el payload (integridad).
- Endpoints: `POST darConsentimiento` (tutor → 201; medico sin la acción → 403; sin auth → 401);
  `GET verConsentimiento` (medico/tutor → 200; un rol sin la acción → 403).
- `adulto_dni` **no** aparece en la salida (write_only).
- Patrón de cleanup `tearDown` para las tablas `managed=False` (como en los tests del apto:
  `TransactionTestCase` no trunca pacientes/personas/domicilio entre tests).

---

## 8. Decisiones cerradas (Roberto)
- Ciclo: **un paso (crear = consentir)**, inmutable.
- Identidad: **el front la manda explícita** (no auto-snapshot).
- App: **`patients`**.
- `verConsentimiento`: **acción nueva** (medico/odontologo/tutor).
- `adulto_dni`: **write_only** (no se devuelve).
- Enforcement "no apto sin consentimiento": **desacoplado**, para cuando exista el CIS.

## 9. Pendiente de confirmar al implementar
- `Consentimiento.paciente` FK a `Pacientes` (`managed=False`) — igual que `Apto.paciente`, funciona.
- Montaje de las rutas: agregar a `patients/urls.py` o un include nuevo en `config/urls.py`
  bajo `/api/v1/consentimientos/`.

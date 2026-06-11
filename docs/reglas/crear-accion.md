# Regla: crear una acción nueva (y que aparezca en prosane_app)

> **Objetivo:** agregar una acción al sistema de permisos data-driven para que un rol la
> reciba en `/api/v1/auth/me` y `prosane_app` pueda gatearla (`can('...')`) y mostrarla en
> el menú. **Todo en el backend; el front es otro repo (handoff en el paso 5).**

Las acciones son **datos** (tabla `actions`), no clases hardcodeadas. La fuente canónica
son los **fixtures** en `authentication/fixtures/`.

---

## 0. Invariante innegociable: `name` en camelCase

El `name` de toda acción es **camelCase**, siempre, idéntico en backend y front:
`crearApto`, `firmarApto`, `verFichaClinica`. **Nunca** snake_case (`firmar_apto`) — el
front hace `can('firmarApto')` y un mismatch deja la función deshabilitada en silencio.

---

## 1. Definir la acción: las 8 claves del contrato congelado

Cada acción tiene **exactamente estas 8 claves** (no se agregan ni quitan):

| Clave | Qué es | Valores |
|---|---|---|
| `name` | clave única, **camelCase** | ej. `crearApto` |
| `label` | texto visible | "Crear apto físico" |
| `icon` | nombre lógico de ícono (no ruta) | `stethoscope` |
| `color` | hex | `#2E7D32` |
| `type` | hint de interacción | `form` \| `list` \| `map` |
| `category` | dominio para agrupar el menú | `salud` \| `administrativo` \| `consentimiento` |
| `is_sensitive` | dato sensible (menor) → confirmación + auditoría | `true` / `false` |
| `sort_order` | orden en el menú (asc) | entero |

(`type`/`category` se validan en la app, no en la DB: para sumar un valor nuevo,
documentalo acá, no hace falta migración.)

---

## 2. Agregar la acción a los fixtures

### 2.1 `authentication/fixtures/actions.json` — la acción
Agregá una fila con un **UUID fijo nuevo** (seguí el patrón `a0000000-...-00NN`):

```jsonc
{ "model": "authentication.action", "pk": "a0000000-0000-0000-0000-000000000009",
  "fields": {
    "name": "nuevaAccion", "label": "Nueva acción", "icon": "bolt", "color": "#455A64",
    "type": "form", "category": "salud", "is_sensitive": false, "sort_order": 50,
    "is_active": true,
    "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"
  } }
```
> ⚠️ **Incluí `created_at`/`updated_at`**: `loaddata` no dispara `auto_now_add`, y la
> columna es NOT NULL. Sin esos campos, el fixture falla.

### 2.2 `authentication/fixtures/role_actions.json` — qué roles la otorgan
Una fila por (rol, acción). El `role` es el **pk integer** del rol; el `action` es el
**UUID** de la acción.

```jsonc
{ "model": "authentication.roleaction", "pk": "b0000000-0000-0000-0000-000000000013",
  "fields": { "role": 2, "action": "a0000000-0000-0000-0000-000000000009",
              "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" } }
```
**pks de rol:** `usuario=1, medico=2, odontologo=3, tutor=4, ayudante=5`.
(El **superadmin** ve **todas** las acciones automáticamente; no hace falta vincularlo.)

### 2.3 ⚠️ Espejar en `authentication/actions_map.py` (mientras `ROLE_ACTIONS` exista)
`ROLE_ACTIONS` es el **mapa de Fase 1** que el test de equivalencia
(`test_me_identico_byte_por_byte`) compara contra la DB. **Hasta que se retire**, agregá
la MISMA acción ahí, con las mismas 8 claves y a los mismos roles del fixture, o la suite
se rompe (el `/me` por DB y el mapa de código divergen):

```python
_VER_APTO = _a("verApto", "Ver apto físico", icon="fact_check", color="#2E7D32",
               type="list", category="salud", is_sensitive=True, sort_order=45)
# y sumarla a ROLE_ACTIONS["medico"], ROLE_ACTIONS["odontologo"] (los mismos roles del fixture)
```

---

## 3. Cargar a la DB

```bash
python manage.py reset_permissions_data          # recarga fixtures (limpia solo las 4 de permisos)
# o con usuarios de prueba:
python manage.py reset_permissions_data --with-users
```

---

## 4. Verificar en `/me`

Logueá como un usuario con ese rol (o el superadmin) y pegale a `GET /api/v1/auth/me/`.
La acción nueva debe aparecer en `actions` con sus 8 claves. Con el server de dev, el
log redactado te muestra la respuesta indentada.

También hay un test que blinda el contrato (`test_me_identico_byte_por_byte`): corré la
suite (`python manage.py test authentication`) y que quede verde.

---

## 5. 🤝 Handoff a prosane_app (qué recibe el front)

**No se edita el front desde acá.** Pero el agente de `prosane_app` necesita saber qué
le llega. El backend emite, en `actions[]` de `/me`, objetos con las **8 claves** de
arriba. El front:

- Gatea con `can('nuevaAccion')` (= `permisos.contains('nuevaAccion')`, parseado de
  `actions[].name`).
- Renderiza el ítem de menú con `label`, `icon`, `color`, y agrupa por `category`.
- Marca `is_sensitive` para confirmación/auditoría.

**Contrato congelado** (no cambia): la lista plana de `actions` y sus 8 claves. Detalle en
`docs/superpowers/specs/2026-06-09-permisos-data-driven-design.md` (§3).

---

## ✅ Checklist
- [ ] `name` en **camelCase**.
- [ ] Las **8 claves** exactas en `actions.json` (+ `is_active`, `created_at`, `updated_at`).
- [ ] UUID fijo nuevo, sin colisionar.
- [ ] Vinculada a los roles correctos en `role_actions.json`.
- [ ] `reset_permissions_data` corrido; aparece en `/me`.
- [ ] Suite de `authentication` verde (test de equivalencia incluido).

## 🚫 No hacer
- snake_case en `name`.
- Agregar/quitar claves del objeto de acción (rompe el contrato y el menú del front).
- Crear la acción "a mano" en la DB en vez de en el fixture (los fixtures son la fuente canónica).

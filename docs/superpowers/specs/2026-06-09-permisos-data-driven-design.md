# Diseño: Sistema de permisos data-driven (acciones)

- **Fecha:** 2026-06-09
- **Rama:** `feat/permisos-data-driven` (base: `dev`)
- **Estado:** Diseño aprobado en brainstorming. **Pendiente de revisión del spec por Roberto antes de cualquier migración.**
- **Autores:** Agustín / Roberto (guía y dueño del schema)

---

## 1. Problema y objetivo

Hoy prosane_api resuelve permisos **en código**: cada permiso es una clase Python
(`EsMedico`, `EsOndontologo`, `EsTutor`, …) que compara contra un nombre de rol
hardcodeado (`authentication/permissions.py`). Agregar un permiso nuevo = escribir una
clase + deploy. Es **rol monolítico**, no granular, y no editable sin tocar código.

**Objetivo:** pasar a **autorización data-driven granular** — la unidad de permiso es
una **acción** (`crearApto`, `firmarApto`, …), editable como dato, asignada vía roles
o manualmente, **resuelta a través del motor nativo de Django (`has_perm`)** para que
DRF, los decoradores y el admin sigan funcionando sin reinventar nada.

### Qué SÍ (frontera estricta — Opción B)

El backend define, como **datos editables**:
- **Qué** puede hacer cada usuario (autorización data-driven).
- La **metadata visual liviana** de cada acción: `name`, `label`, `icon`, `color`,
  `type`, `category`, `is_sensitive`, `sort_order`.

La app Flutter usa esa metadata para: decidir `can('crearApto')`, renderizar
menús/listas (label/icon/color/category), y marcar acciones sensibles.

### Qué NO (fuera de scope — no cruzar)

- El backend **NO** define campos de formularios, layout, `colSpan`, `savePath`, ni
  specs de pantalla. Las pantallas se construyen en Flutter como app normal.
- **NO** hay motor de renderizado server-driven de UI. Descartamos el `config` gigante
  de snapping con la definición de formularios. Tomamos solo la idea de "acción como
  dato con metadata visual liviana".

### Restricciones acordadas

- Prosane **no es multi-tenant** (un solo programa, Salta). Sin `organization_id`, sin
  tablas `global_*` vs `tenant`. Mínimo de tablas.
- Integración vía **motor de permisos nativo de Django** (`PermissionsMixin.has_perm`)
  con un **authentication backend propio**.
- **Offline-first:** las acciones del usuario viajan en `/me` y se cachean en Drift.
- `is_sensitive` + **log de auditoría** de uso, integrado en serio con el tratamiento
  de datos de menores (Ley 25.326).
- **Trazabilidad de origen** (por rol vs manual), pero **computada** (ver §5), no
  materializada.

---

## 2. Faseo (contrato único, sin reescribir el front)

La app debe andar de punta a punta cuanto antes. Faseamos, pero **el contrato `/me`
se congela una sola vez** y no cambia entre fases.

- **Fase 1 — mapa rol→acciones en código (descartable).** `/me` devuelve user + roles
  + lista de acciones, donde las acciones se derivan de un diccionario Python
  `ROLE_ACTIONS` a partir de los roles que el usuario ya tiene en `user_role`.
  **Cero tablas nuevas.** La app integra y anda ya.
- **Fase 2 — data-driven.** El diccionario se reemplaza por las tablas nuevas (§4) y la
  resolución computada (§5). **La respuesta de `/me` es idéntica.** El front no se entera.

> El mapa `ROLE_ACTIONS` de Fase 1 es **un detalle de implementación de Fase 1**,
> reemplazable en Fase 2 sin tocar el contrato.

---

## 3. Contrato CONGELADO: `GET /api/v1/me`

Requiere `Authorization: Bearer <access_token>`.

```jsonc
{
  "user": {
    "id": "9b2c…-uuid",
    "email": "medico@prosane.gob.ar",
    "nombre": "Ana",          // de Personas (display)
    "apellido": "García",
    "is_staff": false
  },
  "roles": [                  // SIEMPRE lista (user_role ya es N-a-N)
    { "name": "medico", "label": "Médico/a" }
  ],
  "actions": [                // ⭐ NÚCLEO CONGELADO — lista plana de lo permitido
    {
      "name": "crearApto",        // clave única, camelCase SIEMPRE
      "label": "Crear apto físico",
      "icon": "stethoscope",      // nombre lógico de ícono (NO ruta de asset)
      "color": "#2E7D32",         // hex
      "type": "form",             // hint de interacción: form | list | map
      "category": "salud",        // dominio para agrupar menús: salud | administrativo | consentimiento
      "is_sensitive": true,       // dato clínico de menor → confirmación + auditoría
      "sort_order": 10            // orden de menú (ascendente)
    }
  ],
  "meta": {
    "permissions_synced_at": "2026-06-09T12:00:00Z",  // invalidación de cache Drift
    "version": "a1b2c3d4"                              // cambia sii cambian los permisos del user
  }
}
```

### Invariantes del contrato

1. 🔒 **`actions` es una lista plana** y **cada acción tiene exactamente estas 8 claves**
   (`name, label, icon, color, type, category, is_sensitive, sort_order`). **No se
   quitan ni renombran nunca.** Es lo que el front cachea en Drift.
2. ➕ **Additive:** `user`, `roles`, `meta` pueden ganar claves nuevas sin romper al
   front. Quitar/renombrar las 8 de `actions`, **sí** rompe.
3. 🔠 **`name` siempre camelCase**, idéntico en front y back (ver §8).
4. `meta.version` = hash corto y determinístico del **conjunto ordenado de `name`
   efectivos** del usuario (stateless: cambia sii cambian sus permisos).
   `meta.permissions_synced_at` = timestamp de la respuesta. Sirven para que la app
   sepa si su cache offline está vieja.

### Vocabularios (validados en la app, no en la DB)

- `type`: `form | list | map` (extensible; convención, no enum de DB).
- `category`: `salud | administrativo | consentimiento` (extensible).

Se guardan como `CharField` con vocabulario documentado para que sumar un valor no
requiera migración.

---

## 4. Schema mínimo (Fase 2)

**Reutiliza (ya existen, `managed=False`):** `roles`, `user_role`, `usuarios`.

**Agrega (nuevas, `managed=True`, migraciones Django, heredan de `common.BaseModel`):**

```
┌──────────────────────────────────────────────────────────────────┐
│ actions                  (registro de acciones + metadata visual)  │
│   id (UUID, BaseModel)                                             │
│   name        CharField(64) UNIQUE   ← camelCase, clave de permiso  │
│   label       CharField(191)                                       │
│   icon        CharField(64)  null                                  │
│   color       CharField(9)   null    ← hex                         │
│   type        CharField(32)          ← form|list|map               │
│   category    CharField(32)  null    ← salud|administrativo|…       │
│   is_sensitive Boolean default False                               │
│   sort_order  Integer default 0                                    │
│   is_active   Boolean default True                                 │
│   (+ created_at/updated_at/created_by/updated_by/deleted_at por    │
│      BaseModel — soft delete incluido)                             │
└───────────────┬──────────────────────────────┬────────────────────┘
                │                              │
   ┌────────────▼────────────┐    ┌────────────▼───────────────────────┐
   │ role_actions            │    │ user_action_overrides              │
   │   id (UUID)             │    │   id (UUID)                        │
   │   role   FK→roles       │    │   user   FK→usuarios                │
   │   action FK→actions      │    │   action FK→actions                 │
   │   unique(role, action)   │    │   effect CharField: grant | deny    │
   │   "qué da cada rol"      │    │   unique(user, action)              │
   └─────────────────────────┘    │   "excepciones manuales"            │
                                  └────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────┐
   │ action_logs   (auditoría de uso de acciones is_sensitive)         │
   │   id (UUID)                                                        │
   │   user        FK→usuarios (SET_NULL)                               │
   │   action_name CharField(64)   ← snapshot, NO FK (sobrevive borrado)│
   │   used_at     DateTimeField db_index                              │
   │   context     JSONField null  ← sin DNI/diagnósticos en texto plano│
   └──────────────────────────────────────────────────────────────────┘
```

Notas:
- `action_logs.action_name` es **snapshot** (string), no FK: un log de auditoría no debe
  romperse ni mutar si después se borra/renombra la acción (mismo criterio que las
  `Constancia` del dominio).
- `role_actions.role` apunta a la tabla `roles` existente (`managed=False`); la FK
  cruza a una tabla no gestionada, lo cual es válido en Django (tipos UUID compatibles).
- **3 tablas core + 1 de auditoría.** Sin `user_actions` materializada ni
  `user_action_sources` (ver §5).

⚠️ **Desvío del patrón del repo:** las tablas actuales son `managed=False` (vienen de
`inspectdb`). Estas nuevas serían `managed=True` con migraciones Django reales. Acordado
en principio, pero **requiere el OK de Roberto como dueño del schema** antes de migrar.

---

## 5. El corazón: resolución computada en vivo (mejora sobre snapping)

snapping **materializa** `user_actions` + `user_action_sources` y corre un *sync
service* cada vez que cambia un rol (más tablas, más código, riesgo de desincronización).
En prosane (single-DB, joins baratos) lo hacemos **computado**, sin materializar:

```
acciones_efectivas(user) =
      ( ⋃ role_actions de todos los roles del user )   ← base de los roles
    ∪ { overrides con effect = 'grant' }                ← sumas manuales
    − { overrides con effect = 'deny' }                 ← restas manuales
```

**Trazabilidad de origen — computada, sin tabla extra:**

```
origen(user, accion):
    fuentes = [ 'rol:' + r.rol  for r in roles_del_user  if (r, accion) ∈ role_actions ]
    if override(user, accion) == 'grant': fuentes += ['manual']
    return fuentes            # si la acción es efectiva, fuentes nunca es vacío
```

Ventajas vs materializar:
- Si se saca un rol, la acción desaparece sola salvo que la dé otro rol o un `grant`
  manual. **Imposible que se desincronice** (no hay copia que mantener).
- Menos tablas, sin sync service, sin migraciones de datos al cambiar roles.

Trade-off aceptado: se recalcula por request (una query, cacheada por request — §6.4).
Para el volumen de prosane es despreciable.

---

## 6. Integración con Django (el núcleo del híbrido)

> Esta sección es la razón de ser del enfoque híbrido: si la integración con
> `has_perm()` no engancha limpio, perdemos el beneficio. Se documenta explícita.

### 6.1 Authentication backends

```python
# settings
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",            # login admin + superuser
    "authentication.backends.ActionPermissionBackend",      # acciones data-driven
]
```

- `ModelBackend` se mantiene: cubre login del admin y el **short-circuit de superuser**.
- `ActionPermissionBackend` resuelve **solo autorización** de acciones (no participa en
  el login; la autenticación de la API la hace simplejwt vía JWT).

### 6.2 El backend propio

```python
from django.contrib.auth.backends import BaseBackend

class ActionPermissionBackend(BaseBackend):
    def authenticate(self, request, **kwargs):
        return None  # no autentica; solo autoriza

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous:
            return set()
        cache = getattr(user_obj, "_action_perm_cache", None)
        if cache is None:
            cache = resolver_acciones_efectivas(user_obj)   # §5 → set de names
            user_obj._action_perm_cache = cache
        return cache

    def has_perm(self, user_obj, perm, obj=None):
        return perm in self.get_all_permissions(user_obj, obj)
```

- `get_all_permissions` devuelve un **set de strings** = los `name` de las acciones
  efectivas (camelCase, ej. `{"crearApto", "firmarApto"}`).
- `has_perm(user, "crearApto")` = pertenencia en ese set.

### 6.3 Por qué NO choca con `content_types`

El sistema de `content_types` y el formato `app_label.codename` aplican **solo** a
`auth.Permission` + `ModelBackend`. Nuestro backend devuelve **strings simples**
(`"crearApto"`), así que:

- Django **no consulta `content_types`** para resolver `has_perm("crearApto")`: se lo
  pregunta a cada backend y hace **OR** de los resultados.
- `ModelBackend.has_perm(user, "crearApto")` devuelve `False` (no existe esa `Permission`)
  → sin error. `ActionPermissionBackend` lo resuelve por datos → `True/False`.
- **Superuser:** `PermissionsMixin.has_perm` corta antes (`is_active and is_superuser →
  True`) para *cualquier* perm, incluido `"crearApto"`. Consistente con el `EsAdmin`
  actual.

Resultado: **cero choque**. Usamos el mecanismo nativo de resolución
(`has_perm`/`get_all_permissions`) pero con nuestra fuente de datos.

### 6.4 Qué funciona "gratis" gracias a esto

- **DRF** — permission class por acción:
  ```python
  def require_action(name):
      class _HasAction(BasePermission):
          def has_permission(self, request, view):
              return bool(request.user and request.user.has_perm(name))
      return _HasAction

  # uso:  permission_classes = [require_action("crearApto")]
  ```
- **Decoradores Django** — `@permission_required("crearApto", raise_exception=True)`
  funciona sin nada extra (llama a `user.has_perm`).
- **Admin** — registramos `actions`, `role_actions`, `user_action_overrides` para
  gestionarlos por UI.
- **Cache por request** — `_action_perm_cache` evita repetir la query si se chequean
  varias acciones en la misma request.

### 6.5 Por qué descartamos `auth.Permission` y `auth.Group` (decisión consciente)

Esto **se aparta** del híbrido "puro" (usar `Permission`/`Group` nativos). Se descarta
a propósito, no por ignorar el sistema de Django:

- **`auth.Permission` no guarda nuestra metadata** (`icon`, `color`, `type`, `category`,
  `is_sensitive`, `sort_order`). Tendríamos igual que crear una tabla paralela de
  metadata keyed por codename → duplicación.
- **`auth.Permission` exige `content_type`** (un permiso está atado a un modelo). Nuestras
  acciones son **abstractas** (`firmarApto`, `verFichaClinica`) y no mapean 1:1 a un
  modelo. Forzarlo es antinatural.
- **`auth.Group` duplicaría `roles`.** Ya existe el modelo de rol del dominio
  (`roles` + `user_role`), ligado a `Usuarios`/`Personas` y al flujo PROSANE/SISA.
- **No perdemos el espíritu híbrido:** conservamos la integración vía
  `PermissionsMixin.has_perm()` + backend propio. La tabla `actions` **es** nuestro
  registro de permisos; el backend **es** el resolutor. Seguimos dentro del motor de
  Django, solo cambiamos la fuente de datos.

---

## 7. `meta.version` y offline-first

- `meta.version = hash_corto(sorted(acciones_efectivas(user)))` — determinístico y
  stateless; cambia **sii** cambia el conjunto de permisos del usuario.
- `meta.permissions_synced_at = now()` en la respuesta.
- La app Drift compara `version`: si difiere de la cacheada, re-sincroniza permisos;
  si no hay conexión, sigue operando con el último estado conocido.

---

## 8. Invariante de naming: camelCase, sin excepción

- Todo `name` de acción es **camelCase** (`crearApto`, `firmarApto`, `verFichaClinica`),
  **idéntico en front y back**. Es contrato, no preferencia.
- Test automatizado: validar que todo `name` matchea `^[a-z][a-zA-Z0-9]*$`.

### 🔁 Seguimiento en `prosane_app` (no perder)

En el spec del front conviven `can('crearApto')` y `can('firmar_apto')`. **Tarea
pendiente en el repo `prosane_app`:** unificar `firmar_apto → firmarApto` y barrer
cualquier `snake_case` en claves de acción. Queda anotado acá para que no se pierda al
volver al front. (No se toca desde este repo.)

---

## 9. Testing (pytest, por feature)

- **Resolución (§5):** roles ∪ grant − deny; sacar un rol; `deny` que pisa un rol;
  `grant` manual; usuario sin roles.
- **Backend (§6):** `has_perm` True/False; superuser bypassa; usuario inactivo → sin
  permisos; cache por request.
- **Contrato `/me` (§3):** estructura exacta; `actions` con **exactamente** las 8 claves;
  `meta` presente; lista vacía bien formada.
- **Invariante camelCase (§8):** regex sobre todos los `name`.
- **DRF (§6.4):** endpoint protegido con `require_action` → 403 sin la acción, 200 con ella.
- **Fase 1 == Fase 2:** misma respuesta de `/me` con el mapa en código y con las tablas
  (test de equivalencia del contrato).

---

## 10. Seguridad y datos de menores

- Acciones `is_sensitive` → se registran en `action_logs` al ejecutarse.
- **Nunca** loguear DNI/diagnósticos/emails en texto plano (ni en `action_logs.context`).
- Acceso mínimo por rol; el backend no expone acciones que el usuario no tiene.
- `action_logs` con snapshot de `action_name` para auditoría estable.

---

## 11. Decisiones abiertas / a confirmar por Roberto

1. **OK del schema** (§4) para pasar a migraciones (`managed=True`, desvío del patrón
   `managed=False`).
2. `roles` no tiene columna `label`; en Fase 1 el `label` de rol sale de un mapa en
   código. ¿Agregar `label` a `roles` en Fase 2 o dejarlo en código? (additive)
3. Path final del endpoint: `/api/v1/me` (propuesto) vs `/api/v1/auth/me`.

---

## 12. Plan de fases (resumen)

- **Fase 1:** serializer `/me` + `ROLE_ACTIONS` en código + endpoint. Sin tablas nuevas.
  Desbloquea la app. **Solo provee el contrato `/me` para el gating del front; la
  enforcement server-side (`ActionPermissionBackend` + `require_action`) llega en Fase 2.**
- **Fase 2:** tablas (§4) + `ActionPermissionBackend` (§6) + resolución (§5) + admin +
  seeds de acciones + reemplazo del mapa. Contrato idéntico.
- **Fase 2b (opcional):** `action_logs` + integración con el flujo de consentimiento.

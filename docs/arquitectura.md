# Arquitectura de prosane_api — guía de apps por dominio

> **Para quién es esto:** el equipo (Roberto, Ramiro, Ale) **y las IAs que usamos**.
> Si sos una IA asistiendo en este repo, leé esto primero: define cómo está organizado
> el proyecto y dónde va cada cosa. No inventes estructura nueva; seguí este mapa.

---

## 1. Qué es prosane_api (y qué NO es)

Backend REST del circuito **PROSANE** (salud escolar, Salta). Es una **capa digital
intermedia** que digitaliza la planilla CIS — alimenta SISA, no lo reemplaza. Lo consume
una app Flutter (`prosane_app`) y un panel web.

**Es un backend para UN programa, un cliente.** NO es un SaaS distribuido. Esto importa
para las decisiones de arquitectura:

| | snapping-api (referencia) | prosane_api (nosotros) |
|---|---|---|
| Escala | SaaS multi-tenant, ~35 módulos, ~12 repos/servicios | 1 backend, 1 cliente, 1 DB |
| Modularidad | Módulos propios (Node) | **Django apps** (gratis del framework) |

👉 **Copiamos de snapping los *principios* (modularidad por dominio, seeders limpios),
NO la *maquinaria* distribuida** (multi-tenant, multi-DB, split global/tenant, servicios
separados). Eso resolvería escala que no tenemos.

---

## 2. Principios

1. **Monolito modular por dominio.** Una **Django app por bloque de dominio**, no una app
   por tabla. La app es la unidad de modularidad (= los "módulos" de snapping, pero
   idiomático de Django).
2. **La estructura sigue al dominio**, y el dominio está en
   [`docs/modelo-de-datos.md`](modelo-de-datos.md) (los "bloques" de la planilla CIS).
3. **Repos separados.** `prosane_api` (backend) y `prosane_app` (Flutter) **no se pisan**.
   El contrato entre ambos (ej. `/me`) es la frontera; se respeta de los dos lados.
4. **Sin big-bang.** No reorganizamos todo de golpe: **cada app nace cuando se construye
   su feature.** El mapa de abajo es el norte, no una tarea de hoy.
5. **Schema en reconciliación.** Varias tablas son `managed=False` (de `inspectdb`) y se
   están alineando incremental (ver [`reconciliacion-modelo.md`](reconciliacion-modelo.md)
   y la tarea de reconciliación). No asumir que el modelo == la tabla sin verificar.

---

## 3. 🗺️ Mapa de apps por dominio

Cruzado con los bloques de `modelo-de-datos.md`. **Este es el norte de organización.**

| App | Bloque de dominio | Modelos (hoy → futuro MVP) | Estado |
|---|---|---|---|
| **`authentication`** | 2.1 Identidad, roles y **acciones/permisos** | Usuarios, Roles, UserRole, Action, RoleAction, UserActionOverride, ActionLog | ✅ existe |
| **`people`** | (compartido) datos de persona | Personas, Domicilio | 🔁 hoy en `core` → renombrar a `people` |
| **`patients`** | 2.2 NNA + 2.5 familia/**consentimiento** | Pacientes (NNA), Responsables, Antecedentes (familiares/personales), Consentimientos | ✅ existe → ampliar |
| **`professionals`** | 2.7 equipo de salud | Profesionales, Matriculas | ✅ existe |
| **`schools`** | 2.3 / 2.6 institucional y escuela | Escuela, InstitucionSalud | 🆕 futuro |
| **`health`** | 2.4 **CIS** + 2.7 clínico + 2.8 odontológico + 2.9 derivaciones | CIS, controles clínico/odontológico, derivaciones | 🆕 futuro (corazón del MVP) |
| **`documents`** | 2.10 entregable | Constancia (snapshots, no FKs vivas) | 🆕 futuro |
| **`common`** | — (no es dominio) | BaseModel, mixins, managers, dev tooling | ✅ existe |

Notas:
- **`consent` NO es app propia**: los consentimientos viven en `patients` (bloque familia).
- **`core` se renombra a `people`** — `core` es un cajón vago; `people` es un bloque claro.
  Es un refactor chico (la tabla no se mueve, sigue `db_table='personas'`); ver la regla
  de refactor cuando se haga.
- `common` no es dominio: es infraestructura compartida (base de modelos, logging de dev,
  managers de soft-delete).

---

## 4. Estructura interna de una app

Cada app de dominio tiende a esta forma (creá solo lo que necesites):

```
<app>/
  models.py          # modelos del dominio (heredan common.BaseModel salvo legacy managed=False)
  serializers.py     # forma/validación de datos (campos explícitos; write_only para sensibles)
  services.py        # lógica de negocio (operaciones multi-modelo en @transaction.atomic)
  selectors.py       # queries complejas (lectura)
  views.py           # adaptadores HTTP DELGADOS (sin reglas de negocio)
  urls.py            # rutas, siempre versionadas /api/v1/...
  fixtures/          # seeds de ESTA app (formato Django: {model, pk, fields})
  tests/             # tests por feature (pytest/Django test)
  admin.py           # gestión por el admin de Django
```

**Regla de oro:** vistas delgadas. La lógica va en `services.py`; las queries en
`selectors.py`. La view solo traduce HTTP ↔ servicio.

---

## 5. Convenciones transversales

- **Vocabulario en español**, consistente con `modelo-de-datos.md` (no mezclar NNA/Paciente/Tutor sin criterio).
- **API versionada**: todo bajo `/api/v1/...` desde el inicio.
- **Datos sensibles (menores, Ley 25.326):** acceso mínimo por rol; nunca loguear DNI/diagnósticos/emails en claro; serializers con campos explícitos (evitar `fields='__all__'` en datos sensibles).
- **Seeds/fixtures por app**, idempotentes, cargables con `loaddata` (ejemplo concreto en [`reglas/crear-accion.md`](reglas/crear-accion.md)).
- **Permisos data-driven:** las acciones son datos (tabla `actions`), no clases hardcodeadas. Para crear una acción nueva → [`reglas/crear-accion.md`](reglas/crear-accion.md).
- **TDD** por feature; no dar algo por andando sin correrlo.

---

## 6. Reglas / playbooks

Tareas comunes documentadas paso a paso (para que cualquiera —y su IA— las haga igual):

- [`reglas/crear-accion.md`](reglas/crear-accion.md) — crear una acción nueva y que aparezca en `prosane_app`.
- _(se irán sumando: crear un modelo de dominio, crear un endpoint, renombrar `core→people`, etc.)_

---

## 7. Referencias

- [`modelo-de-datos.md`](modelo-de-datos.md) — fuente de verdad del dominio.
- [`reconciliacion-modelo.md`](reconciliacion-modelo.md) — el desfasaje modelo↔tabla.
- [`stack-backend.md`](stack-backend.md) — stack, seguridad, deployment.
- `superpowers/specs/2026-06-09-permisos-data-driven-design.md` — diseño del sistema de permisos.

# AGENTS.md — prosane_api

Guía para **agentes de IA** que trabajan en este repo (Cursor, Codex, Gemini, Copilot,
etc.). La fuente de verdad de las convenciones vive en `docs/`. Empezá por ahí:

- **`docs/arquitectura.md`** — mapa de apps por dominio + convenciones: cómo está
  organizado el proyecto y dónde va cada cosa. **Leelo antes de tocar estructura.**
- **`docs/reglas/`** — playbooks paso a paso para tareas comunes:
  - `docs/reglas/crear-accion.md` — crear una acción nueva y que aparezca en `prosane_app`.

## Reglas clave (resumen)
- **Django app por BLOQUE de dominio** (no por tabla). La estructura sigue a
  `docs/modelo-de-datos.md`. Sin reorganizaciones big-bang.
- **Repos separados:** `prosane_api` (backend) y `prosane_app` (Flutter) **no se pisan**.
  El contrato entre ambos (ej. `/me`) es la frontera.
- **Acciones/permisos son data-driven**; el `name` es **camelCase SIEMPRE**.
- **Datos de menores (Ley 25.326):** acceso mínimo por rol; nunca loguear
  DNI/diagnósticos/emails en claro; serializers con campos explícitos.
- **Vistas delgadas:** negocio en `services.py`, queries en `selectors.py`.
- **Schema en reconciliación** (`managed=False` legacy): no asumas modelo == tabla sin
  verificar (ver `docs/reconciliacion-modelo.md`).

> Para Claude Code, lo mismo está en `CLAUDE.md` y `.claude/rules/`.

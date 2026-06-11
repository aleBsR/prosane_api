# Regla: crear una acción

Para crear una acción nueva (y que aparezca en `prosane_app`), seguí el playbook completo:
**`docs/reglas/crear-accion.md`**.

Invariantes:
- El `name` de la acción es **camelCase SIEMPRE** (`crearApto`), nunca snake_case — un
  mismatch deja la función deshabilitada en silencio en el front.
- Las acciones son **datos**: la fuente canónica son los fixtures
  (`authentication/fixtures/actions.json` + `role_actions.json`), no la DB a mano.
- El objeto de acción tiene **8 claves exactas** (contrato congelado); no agregar ni quitar.

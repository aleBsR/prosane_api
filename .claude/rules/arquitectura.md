# Regla: arquitectura

Antes de tocar estructura (crear apps, decidir dónde va un modelo/servicio/seed), leé la
guía completa: **`docs/arquitectura.md`** (fuente única).

Resumen rápido:
- **Django app por BLOQUE de dominio**, no por tabla. La app es la unidad de modularidad.
- La estructura **sigue al dominio** de `docs/modelo-de-datos.md`.
- prosane_api (backend) y prosane_app (Flutter) son **repos separados, no se pisan**.
- **Sin big-bang**: cada app nace cuando se construye su feature.
- Copiamos de snapping los *principios* (modularidad, seeders), NO la *maquinaria*
  distribuida (multi-tenant, multi-DB).

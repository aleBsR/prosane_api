# ⚠️ users.json — USUARIOS DE JUGUETE, SOLO DESARROLLO LOCAL

**JAMÁS usar ni cargar en producción.**

`users.json` (y `core/fixtures/people.json`) contienen usuarios de prueba **ficticios**
con **contraseñas de juguete**, pensados solo para desarrollo local.

- Los hashes son PBKDF2 de Django (`make_password`), generados a partir de una
  contraseña de juguete. **No son secretos reales.**
- La contraseña actual de los fixtures es **`prosane-dev-2026`** (dev local).
- Emails: `superadmin@prosane.test`, `medico@prosane.test`, `odontologo@prosane.test`,
  `ayudante@prosane.test`, `tutor@prosane.test`.

## Salvaguardas
- La carga (`reset_permissions_data --with-users`) y la regeneración
  (`generate_users_fixture`) **abortan si `SEEDS_ENABLED` no está activo** — y
  `SEEDS_ENABLED` vive SOLO en `config/settings/local.py`. En prod no corren.

## Regenerar con otra contraseña
```bash
SEED_USER_PASSWORD='otra-pass' python manage.py generate_users_fixture
```

## Cargar en local
```bash
python manage.py reset_permissions_data --with-users
```

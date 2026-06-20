# Usuarios de prueba — SOLO desarrollo local

**JAMÁS usar ni cargar en producción.**

`users.json` y `roles.json` contienen usuarios y roles de prueba **ficticios**
con contraseñas de juguete, pensados solo para desarrollo local.

## Contraseña

La contraseña actual de los fixtures es **`prosane-dev-2026`**.

## Emails de prueba

- `superadmin@prosane.test` (superusuario)
- `medico@prosane.test` → rol **medico**
- `odontologo@prosane.test` → rol **odontologo**
- `ayudante@prosane.test` → rol **ayudante**
- `tutor@prosane.test` → rol **tutor**

## Cargar en local

```bash
python manage.py seed_all
```

`seed_all` carga roles, usuarios y permisos. Requiere `SEEDS_ENABLED=True`
(configurado en `config/settings/local.py`).

## Regenerar con otra contraseña

```bash
SEED_USER_PASSWORD='otra-pass' python manage.py generate_users_fixture
```

Esto regenera `users.json` con hashes de Django (PBKDF2) a partir de la
contraseña indicada.

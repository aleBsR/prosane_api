# Usuarios de prueba — SOLO desarrollo local

**JAMÁS usar ni cargar en producción.**

`users.json` y `roles.json` contienen usuarios y roles de prueba **ficticios**
con contraseñas de juguete, pensados solo para desarrollo local.

## Contraseña

La contraseña de los fixtures es **`prosane123`** para todos los usuarios.

## Emails de prueba

- `superadmin@prosane.test` → rol **superadmin** (superusuario, acceso total)
- `medico@prosane.test` → rol **medico**
- `medico1@prosane.test` → rol **medico**
- `odontologo@prosane.test` → rol **odontologo**
- `odontologo1@prosane.test` → rol **odontologo**
- `ayudante@prosane.test` → rol **ayudante**
- `tutor@prosane.test` → rol **tutor**
- `escuela@prosane.test` → rol **escuela**

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

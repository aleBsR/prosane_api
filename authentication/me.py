"""Armador del payload de `GET /api/v1/auth/me` (contrato congelado, spec §3).

Puro: recibe el usuario, los nombres de rol y `now`; devuelve el dict del contrato.
La vista (views.py) sólo extrae los roles del token y delega acá. En Fase 2 cambia
de dónde salen las acciones, NO la forma de este payload.
"""
from datetime import timezone

from authentication.actions_map import actions_for_roles, permissions_version, role_label


def _iso_z(dt):
    """Formatea un datetime aware en UTC con sufijo `Z` (como el contrato)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_me_payload(user, role_names, *, now):
    actions = actions_for_roles(role_names)
    persona = getattr(user, "persona", None)
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "nombre": getattr(persona, "nombre", None) if persona else None,
            "apellido": getattr(persona, "apellido", None) if persona else None,
            "is_staff": bool(user.is_staff),
        },
        "roles": [{"name": r, "label": role_label(r)} for r in role_names],
        "actions": actions,
        "meta": {
            "permissions_synced_at": _iso_z(now),
            "version": permissions_version(actions),
        },
    }

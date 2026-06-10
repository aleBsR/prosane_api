"""Formateador del payload de `GET /api/v1/auth/me` (contrato congelado, spec §3).

PURO: recibe el usuario, los nombres de rol y las acciones YA RESUELTAS, y arma el
dict del contrato. La resolución de acciones (mapa de código en Fase 1 / tablas en
Slice 2) vive afuera; así el contrato es idéntico independientemente de la fuente,
y el test de equivalencia puede comparar ambas resoluciones con el mismo formateador.
"""
from datetime import timezone

from authentication.actions_map import permissions_version, role_label


def _iso_z(dt):
    """Formatea un datetime aware en UTC con sufijo `Z` (como el contrato)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_me_payload(user, role_names, actions, *, now):
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

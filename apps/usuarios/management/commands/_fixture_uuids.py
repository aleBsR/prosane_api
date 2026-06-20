"""UUIDs determinísticos para fixtures de usuarios/roles.

Permite que users.json referencie roles por UUID sin depender de la base de datos.
"""
import uuid


NAMESPACE_ROLES = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def role_uuid(rol_name):
    """UUID determinístico para un rol dado su nombre."""
    return uuid.uuid5(NAMESPACE_ROLES, f"role:{rol_name}")

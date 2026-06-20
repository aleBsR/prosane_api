"""Servicio de registro de tutores.

Separa la lógica de negocio de la capa de presentación (views/serializers).
"""
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from apps.personas.models import Persona
from apps.tutores.models import Tutor
from apps.usuarios.models import Rol, Usuario


class TutorRegistrationError(Exception):
    """Error controlado durante el registro de un tutor."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def _validar_unicidad(email, dni):
    """Valida que email y DNI no estén en uso antes de crear nada."""
    if Usuario.objects.filter(email=email).exists():
        raise TutorRegistrationError("Ya existe un usuario con este email.", field="email")
    if Persona.objects.filter(dni=dni).exists():
        raise TutorRegistrationError("Ya existe una persona con este DNI.", field="dni")


def _asignar_rol_tutor(usuario):
    """Asigna automáticamente el rol 'tutor' al usuario recién creado."""
    rol_tutor, _ = Rol.objects.get_or_create(rol="tutor")
    usuario.roles.add(rol_tutor)


def registrar_tutor(email, password, persona_data, parentesco=None):
    """Registra un nuevo tutor: Persona + Usuario + Tutor + JWT.

    Args:
        email: Email del tutor (único).
        password: Contraseña en texto plano.
        persona_data: Dict con datos de Persona (nombre, apellido, dni, tipo_dni, sexo, fecha_nacimiento).
        parentesco: Relación con el menor (opcional).

    Returns:
        Dict con {user, access, refresh}.

    Raises:
        TutorRegistrationError: Si hay problemas de validación.
    """
    _validar_unicidad(email, persona_data.get("dni"))

    with transaction.atomic():
        persona = Persona.objects.create(**persona_data)
        usuario = Usuario.objects.create_user(
            email=email,
            password=password,
            persona=persona,
        )
        Tutor.objects.create(
            persona=persona,
            usuario=usuario,
            parentesco=parentesco or "",
        )
        _asignar_rol_tutor(usuario)

    refresh = RefreshToken.for_user(usuario)
    return {
        "user": {
            "id": str(usuario.id),
            "email": usuario.email,
            "nombre": persona.nombre,
            "apellido": persona.apellido,
        },
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }

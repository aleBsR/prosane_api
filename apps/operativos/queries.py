"""Consultas de operativos con reglas de visibilidad por rol.

Separa la lógica de "qué operativos puede ver/usar el usuario" de las views
y services, siguiendo el patrón repository/query.
"""
from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.operativos.models import Operativo


def _roles_usuario(user):
    return set(user.roles.values_list('rol', flat=True))


def operativos_visibles_para_usuario(user):
    """Devuelve el queryset de operativos que el usuario puede listar.

    - superuser / superadmin: todos.
    - ayudante / escuela: los que creó, los de su escuela, o los creados por superadmin.
    - medico / odontologo: los donde está asignado.
    - otros: ninguno.
    """
    roles = _roles_usuario(user)

    if user.is_superuser or 'superadmin' in roles:
        return Operativo.objects.all()

    if roles & {'ayudante', 'escuela'}:
        from django.db.models import Q
        filtro = Q(created_by=user)
        filtro |= Q(created_by__is_superuser=True)
        if getattr(user, 'escuela_id', None):
            filtro |= Q(escuela_id=user.escuela_id)
        return Operativo.objects.filter(filtro).distinct()

    if roles & {'medico', 'odontologo'}:
        return Operativo.objects.filter(profesionales_asignados__profesional=user)

    return Operativo.objects.none()


def obtener_operativo_visible(user, operativo_id):
    """Obtiene un operativo específico si el usuario puede verlo.

    Levanta Http404 si el operativo no existe o el usuario no tiene acceso.
    """
    operativo = get_object_or_404(Operativo, pk=operativo_id)

    roles = _roles_usuario(user)

    if user.is_superuser or 'superadmin' in roles:
        return operativo

    if roles & {'ayudante', 'escuela'}:
        if (
            operativo.created_by == user
            or (operativo.created_by and operativo.created_by.is_superuser)
            or (getattr(user, 'escuela_id', None) and user.escuela_id == operativo.escuela_id)
        ):
            return operativo

    if roles & {'medico', 'odontologo'}:
        asignado = operativo.profesionales_asignados.filter(profesional=user).exists()
        if asignado:
            return operativo

    raise Http404

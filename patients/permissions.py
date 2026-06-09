from rest_framework.permissions import IsAuthenticated


def _get_roles(request):
    if request.user.is_superuser:
        return {'admin'}
    return {r['rol'] for r in request.auth.get('roles', [])}


class PuedeListarPacientes(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        roles = _get_roles(request)
        return bool(roles & {'admin', 'medico', 'odontologo', 'ayudante', 'tutor'})


class PuedeCrearPaciente(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        roles = _get_roles(request)
        return bool(roles & {'admin', 'medico', 'tutor'})


class PuedeGestionarPaciente(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        roles = _get_roles(request)
        return bool(roles & {'admin', 'medico', 'tutor'})


class PuedeGestionarAntecedentes(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        roles = _get_roles(request)
        return bool(roles & {'admin', 'medico', 'tutor'})


class SoloPropioTutor(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        roles = _get_roles(request)
        return bool(roles & {'admin', 'tutor'})

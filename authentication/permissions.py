
from rest_framework.permissions import IsAuthenticated


class TieneRol(IsAuthenticated):
    nombre_rol = None

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        roles = request.auth.get('roles', [])
        return any(rol['rol'] == self.nombre_rol for rol in roles)


class EsMedico(TieneRol):
    nombre_rol = 'medico'


class EsOdontologo(TieneRol):
    nombre_rol = 'odontologo'


class EsTutor(TieneRol):
    nombre_rol = 'tutor'


class EsAyudante(TieneRol):
    nombre_rol = 'ayudante'


class EsAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.is_superuser











































 
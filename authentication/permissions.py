
from rest_framework.permissions import IsAuthenticated


class  TieneRol(IsAuthenticated):

    nombre_rol = None

    #django utiliza el decorador @permission_classes([tieneRol]) 
    #donde automaticamente llama a has_permission para verificar si el usuario tiene el rol

    def has_permission(self,request,view):
        #verificar que primero este autenticado
        if not super().has_permission(request,view):
            return False
        #despues verifica el rol

        #busca los roles, sino encuentra devuelve una lista vacia
        roles = request.auth.get('roles', [])
        #any() devuelve True si al menos uno de los roles tiene 'rol' igual a self.nombre_rol
        return any(rol['rol'] == self.nombre_rol for rol in roles)

#vamos a heredar de tieneRol

class EsMedico(TieneRol):
    nombre_rol = 'medico'

class EsOndontologo(TieneRol):
    nombre_rol = 'odontologo'

class EsTutor(TieneRol):
    nombre_rol = 'tutor'

class EsAyudante(TieneRol):
    nombre_rol = 'ayudante'

class EsAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request,view):
            return False
        return request.user.is_superuser


def require_action(action_name):
    """Enforcement server-side por acción (data-driven).

    Permission class de DRF que exige que el usuario TENGA la acción, resuelta vía
    `request.user.has_perm(action_name)` → ActionPermissionBackend (lee de la DB).
    - Sin autenticar → 401.
    - Autenticado sin la acción → 403.
    - Superuser → pasa (short-circuit de Django).

    Uso:  permission_classes = [require_action('verFichaClinica')]
    """
    class _RequireAction(IsAuthenticated):
        def has_permission(self, request, view):
            if not super().has_permission(request, view):
                return False
            return bool(request.user.has_perm(action_name))

    return _RequireAction











































 
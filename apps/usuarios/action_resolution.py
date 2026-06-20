from apps.usuarios.models.action import Action, ActionRole

from django.contrib.auth.backends import BaseBackend


#Devuelve el menú completo de acciones que el frontend va a mostrar
def effective_actions(user):
    if getattr(user, 'is_superuser', False):
        #si es superusuario devuelve todas las acciones activas
        actions = Action.objects.filter(is_active=True)
    else:
        #Obtenemos los roles del usuario
        role_ids = list(user.roles.values_list('id', flat=True))
        action_ids = set(
            ActionRole.objects.filter(role_id__in=role_ids)
            .values_list('action_id', flat=True)
        )
        actions = Action.objects.filter(id__in=action_ids, is_active=True)

    return list(actions.values(
        'name', 'label', 'icon', 'color', 'type',
        'category', 'is_sensitive', 'sort_order',
    ).order_by('sort_order', 'name'))



class ActionPermissionBackend(BaseBackend):
    """Resuelve permisos por nombre de acción desde la DB."""

    def authenticate(self, request, **kwargs):
        return None

    def get_all_permissions(self, user_obj, obj=None):
        if not getattr(user_obj, 'is_active', False) or getattr(user_obj, 'is_anonymous', True):
            return set()
        if getattr(user_obj, 'is_superuser', False):
            return set(Action.objects.filter(is_active=True).values_list('name', flat=True))
        return set(
            ActionRole.objects.filter(
                role__roleusuario__id_user=user_obj,
                action__is_active=True,
            ).values_list('action__name', flat=True)
        )

    def has_perm(self, user_obj, perm, obj=None):
        return perm in self.get_all_permissions(user_obj, obj)
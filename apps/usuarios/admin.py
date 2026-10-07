from django.contrib import admin

from apps.usuarios.models import Action, ActionRole, AuditoriaUsuario, Usuario


@admin.register(AuditoriaUsuario)
class AuditoriaUsuarioAdmin(admin.ModelAdmin):
    list_display = ("created_at", "accion", "actor", "objetivo", "ip")
    list_filter = ("accion",)
    search_fields = ("actor__email", "objetivo__email")
    readonly_fields = ("actor", "objetivo", "accion", "ip", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Usuario)
admin.site.register(Action)
admin.site.register(ActionRole)

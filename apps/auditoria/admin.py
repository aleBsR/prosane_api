from django.contrib import admin

from apps.auditoria.models import AuditoriaCambio


@admin.register(AuditoriaCambio)
class AuditoriaCambioAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'entidad', 'accion', 'actor', 'entidad_id', 'ip']
    list_filter = ['entidad', 'accion']
    search_fields = ['actor__email']
    readonly_fields = ['actor', 'entidad', 'entidad_id', 'accion', 'detalle', 'ip', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

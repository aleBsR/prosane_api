from django.contrib import admin

from health.models import Apto


@admin.register(Apto)
class AptoAdmin(admin.ModelAdmin):
    list_display = ('id', 'paciente', 'profesional', 'estado', 'fecha_emision')
    list_filter = ('estado',)
    readonly_fields = ('firma_hash', 'timestamp_firma')

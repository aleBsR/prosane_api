from django.contrib import admin
from .models import Escuela, Curso, ObservacionEscuela


@admin.register(Escuela)
class EscuelaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cue', 'ambito', 'activa')
    list_filter = ('activa', 'ambito', 'sector_gestion')
    search_fields = ('nombre', 'cue')


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('escuela', 'sala_grado_anio', 'division', 'ciclo_lectivo')
    list_filter = ('nivel', 'ciclo_lectivo')
    search_fields = ('escuela__nombre',)


admin.site.register(ObservacionEscuela)

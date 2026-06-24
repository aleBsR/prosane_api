from django.contrib import admin
from .models import Operativo, OperativoProfesional, OperativoAlumno


class OperativoProfesionalInline(admin.TabularInline):
    model = OperativoProfesional
    extra = 1


class OperativoAlumnoInline(admin.TabularInline):
    model = OperativoAlumno
    extra = 0
    readonly_fields = ['apellido', 'nombre', 'dni', 'tipo_dni']
    can_delete = True


@admin.register(Operativo)
class OperativoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'escuela', 'fecha', 'estado']
    list_filter = ['estado', 'fecha']
    search_fields = ['nombre', 'escuela__nombre', 'notas']
    date_hierarchy = 'fecha'
    inlines = [OperativoProfesionalInline, OperativoAlumnoInline]
    readonly_fields = ['created_by']


@admin.register(OperativoProfesional)
class OperativoProfesionalAdmin(admin.ModelAdmin):
    list_display = ['operativo', 'profesional', 'rol_en_operativo', 'confirmado']
    list_filter = ['rol_en_operativo', 'confirmado']


@admin.register(OperativoAlumno)
class OperativoAlumnoAdmin(admin.ModelAdmin):
    list_display = ['apellido', 'nombre', 'dni', 'operativo', 'estado']
    list_filter = ['estado']
    search_fields = ['apellido', 'nombre', 'dni']

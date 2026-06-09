from django.urls import path
from . import views

app_name = 'apidocs'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('autenticacion/', views.autenticacion, name='autenticacion'),
    path('auth/register/', views.auth_register, name='auth_register'),
    path('auth/register-tutor/', views.auth_register_tutor, name='auth_register_tutor'),
    path('auth/register-profesional/', views.auth_register_profesional, name='auth_register_profesional'),
    path('auth/login/', views.auth_login, name='auth_login'),
    path('auth/asignar-rol/', views.auth_asignar_rol, name='auth_asignar_rol'),
    path('pacientes/list/', views.pacientes_list, name='pacientes_list'),
    path('pacientes/create/', views.pacientes_create, name='pacientes_create'),
    path('pacientes/detail/', views.pacientes_detail, name='pacientes_detail'),
    path('pacientes/update/', views.pacientes_update, name='pacientes_update'),
    path('pacientes/delete/', views.pacientes_delete, name='pacientes_delete'),
    path('antecedentes/familiares/', views.antecedentes_familiares, name='antecedentes_familiares'),
    path('antecedentes/familiares/put/', views.antecedentes_familiares_put, name='antecedentes_familiares_put'),
    path('antecedentes/personales/', views.antecedentes_personales, name='antecedentes_personales'),
    path('antecedentes/personales/put/', views.antecedentes_personales_put, name='antecedentes_personales_put'),
    path('responsable/perfil/', views.responsable_perfil, name='responsable_perfil'),
    path('responsable/perfil/put/', views.responsable_perfil_put, name='responsable_perfil_put'),
    path('profesionales/perfil/', views.profesionales_perfil, name='profesionales_perfil'),
    path('profesionales/perfil/put/', views.profesionales_perfil_put, name='profesionales_perfil_put'),
    path('profesionales/validar-matricula/', views.profesionales_validar_matricula, name='profesionales_validar_matricula'),
    path('profesionales/buscar-paciente/', views.profesionales_buscar_paciente, name='profesionales_buscar_paciente'),
]

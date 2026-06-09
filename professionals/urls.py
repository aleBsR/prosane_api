from django.urls import path
from .views import ProfesionalPerfilAPIView, validar_matricula, BuscarPacienteAPIView

urlpatterns = [
    path('perfil/', ProfesionalPerfilAPIView.as_view(), name='profesional-perfil'),
    path('validar-matricula/', validar_matricula, name='validar-matricula'),
    path('pacientes/buscar/', BuscarPacienteAPIView.as_view(), name='profesionales-buscar-paciente'),
]

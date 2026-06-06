from django.urls import path
from .views import (
    PacienteListCreateAPIView,
    PacienteDetailAPIView,
    AntecedentesFamiliaresAPIView,
    AntecedentesPersonalesAPIView,
    ResponsableProfileAPIView,
    crear_paciente
)

urlpatterns = [
    path('pacientes/', crear_paciente),
    path('', PacienteListCreateAPIView.as_view(), name='paciente-list-create'),
    path('<int:pk>/', PacienteDetailAPIView.as_view(), name='paciente-detail'),
    path('<int:patient_id>/antecedentes-familiares/', AntecedentesFamiliaresAPIView.as_view(), name='antecedentes-familiares'),
    path('<int:patient_id>/antecedentes-personales/', AntecedentesPersonalesAPIView.as_view(), name='antecedentes-personales'),
    path('responsable/', ResponsableProfileAPIView.as_view(), name='responsable-profile'),
]
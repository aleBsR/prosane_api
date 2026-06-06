

from django.urls import path
from .views import crear_paciente

urlpatterns = [

    path('pacientes/', crear_paciente)

]
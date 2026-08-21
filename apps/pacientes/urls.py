from django.urls import path

from .views import EscuelaAlumnosListCreateView


urlpatterns = [
    path('alumnos/', EscuelaAlumnosListCreateView.as_view(), name='escuela-alumnos-list-create'),
]

from django.urls import path

from .views import AlumnoAntecedentesView, EscuelaAlumnosListCreateView


urlpatterns = [
    path('alumnos/', EscuelaAlumnosListCreateView.as_view(), name='escuela-alumnos-list-create'),
    path('alumnos/<uuid:pk>/antecedentes/', AlumnoAntecedentesView.as_view(), name='alumno-antecedentes'),
]

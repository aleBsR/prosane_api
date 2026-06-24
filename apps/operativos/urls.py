from django.urls import path
from . import views

urlpatterns = [
    path('', views.OperativoListCreateView.as_view(), name='operativo-list-create'),
    path('profesionales-disponibles/', views.ProfesionalesDisponiblesView.as_view(), name='profesionales-disponibles'),
    path('<uuid:pk>/', views.OperativoDetailView.as_view(), name='operativo-detail'),
    path('<uuid:pk>/confirmar/', views.OperativoConfirmarView.as_view(), name='operativo-confirmar'),
    path('<uuid:pk>/iniciar/', views.OperativoIniciarView.as_view(), name='operativo-iniciar'),
    path('<uuid:pk>/finalizar/', views.OperativoFinalizarView.as_view(), name='operativo-finalizar'),
    path('<uuid:pk>/cancelar/', views.OperativoCancelarView.as_view(), name='operativo-cancelar'),
    path('<uuid:pk>/completitud/', views.OperativoCompletitudView.as_view(), name='operativo-completitud'),
    path('<uuid:pk>/profesionales/', views.OperativoProfesionalListView.as_view(), name='operativo-profesional-list'),
    path('<uuid:pk>/profesionales/asignar/', views.OperativoProfesionalAssignView.as_view(), name='operativo-profesional-assign'),
    path('<uuid:pk>/profesionales/<uuid:prof_pk>/remover/', views.OperativoProfesionalRemoveView.as_view(), name='operativo-profesional-remove'),
    path('<uuid:pk>/alumnos/', views.OperativoAlumnoListCreateView.as_view(), name='operativo-alumno-list-create'),
    path('<uuid:pk>/alumnos/importar-csv/', views.OperativoAlumnoImportCSVView.as_view(), name='operativo-alumno-import-csv'),
    path('<uuid:pk>/alumnos/<uuid:alumno_pk>/', views.OperativoAlumnoDetailView.as_view(), name='operativo-alumno-detail'),
    path('<uuid:pk>/alumnos/<uuid:alumno_pk>/evaluacion-medica/', views.EvaluacionMedicaView.as_view(), name='operativo-alumno-evaluacion-medica'),
    path('<uuid:pk>/alumnos/<uuid:alumno_pk>/evaluacion-odontologica/', views.EvaluacionOdontologicaView.as_view(), name='operativo-alumno-evaluacion-odontologica'),
    path('<uuid:pk>/alumnos/<uuid:alumno_pk>/seccion-escuela/', views.SeccionEscuelaView.as_view(), name='operativo-alumno-seccion-escuela'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.OperativoListCreateView.as_view(), name='operativo-list-create'),
    path('<uuid:pk>/', views.OperativoDetailView.as_view(), name='operativo-detail'),
    path('<uuid:pk>/confirmar/', views.OperativoConfirmarView.as_view(), name='operativo-confirmar'),
    path('<uuid:pk>/finalizar/', views.OperativoFinalizarView.as_view(), name='operativo-finalizar'),
    path('<uuid:pk>/cancelar/', views.OperativoCancelarView.as_view(), name='operativo-cancelar'),
    path('<uuid:pk>/profesionales/', views.OperativoProfesionalListView.as_view(), name='operativo-profesional-list'),
    path('<uuid:pk>/profesionales/asignar/', views.OperativoProfesionalAssignView.as_view(), name='operativo-profesional-assign'),
    path('<uuid:pk>/profesionales/<uuid:prof_pk>/remover/', views.OperativoProfesionalRemoveView.as_view(), name='operativo-profesional-remove'),
    path('<uuid:pk>/alumnos/', views.OperativoAlumnoListCreateView.as_view(), name='operativo-alumno-list-create'),
    path('<uuid:pk>/alumnos/importar-csv/', views.OperativoAlumnoImportCSVView.as_view(), name='operativo-alumno-import-csv'),
    path('<uuid:pk>/alumnos/<uuid:alumno_pk>/', views.OperativoAlumnoDetailView.as_view(), name='operativo-alumno-detail'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('mi-escuela/', views.MiEscuelaView.as_view(), name='mi-escuela'),
    path('', views.EscuelaListCreateView.as_view(), name='escuela-list-create'),
    path('<uuid:pk>/', views.EscuelaDetailView.as_view(), name='escuela-detail'),
    path('<uuid:escuela_pk>/cursos/', views.CursoListCreateView.as_view(), name='curso-list-create'),
    path('<uuid:escuela_pk>/cursos/<uuid:pk>/', views.CursoDetailView.as_view(), name='curso-detail'),
]

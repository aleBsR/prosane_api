from django.urls import path

from apps.profesionales import views


urlpatterns = [
    path(
        "profesionales/validar-matricula/",
        views.ValidarMatriculaView.as_view(),
        name="profesionales-validar-matricula",
    ),
    path(
        "profesionales/",
        views.ProfesionalesListCreateView.as_view(),
        name="profesionales-list-create",
    ),
    path(
        "profesionales/<uuid:pk>/",
        views.ProfesionalDetailView.as_view(),
        name="profesional-detail",
    ),
    path(
        "profesionales/<uuid:pk>/resend-temp/",
        views.ProfesionalResendTempView.as_view(),
        name="profesional-resend-temp",
    ),
]
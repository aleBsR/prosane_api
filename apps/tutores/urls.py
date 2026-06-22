from django.urls import path

from apps.tutores import views


urlpatterns = [
    path("auth/register/tutor/", views.RegisterTutorView.as_view(), name="register-tutor"),
    path("tutores/<uuid:pk>/hijos/", views.TutorHijosView.as_view(), name="tutor-hijos"),
    path("tutores/<uuid:pk>/consentimiento/", views.TutorConsentimientoView.as_view(), name="tutor-consentimiento"),
    path("tutores/<uuid:pk>/antecedentes-familiares/", views.TutorAntecedentesFamiliaresView.as_view(), name="tutor-antecedentes-familiares"),
]

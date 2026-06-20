from django.urls import path

from apps.tutores import views


urlpatterns = [
    path("auth/register/tutor/", views.RegisterTutorView.as_view(), name="register-tutor"),
    path("tutores/<uuid:pk>/hijos/", views.TutorHijosView.as_view(), name="tutor-hijos"),
]

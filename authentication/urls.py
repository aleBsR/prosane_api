


from django.urls import path
from .views import register, login, register_tutor, register_profesional, asignar_rol, solo_medicos


urlpatterns = [
    path('register/', register),
    path('register-tutor/', register_tutor),
    path('register-profesional/', register_profesional),
    path('login/', login),
    path('rol/<id>', asignar_rol),
    path('medico/', solo_medicos),
]
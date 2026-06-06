


from django.urls import path
from .views import register,login , asignar_rol , solo_medicos


urlpatterns = [
    path('register/', register),
    path('login/', login),
    path('rol/<id>', asignar_rol),
    path('medico/', solo_medicos)
]
from django.urls import path

from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    register, login, register_tutor, register_profesional,
    asignar_rol, solo_medicos, me, logout,
)
from .tokens import RolesTokenObtainPairView


urlpatterns = [
    path('register/', register),
    path('register-tutor/', register_tutor),
    path('register-profesional/', register_profesional),
    path('login/', login),
    path('rol/<id>', asignar_rol),
    path('medico/', solo_medicos),

    # Sesión — paths congelados del spec
    path('me/', me),
    path('token/', RolesTokenObtainPairView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('logout/', logout),
]

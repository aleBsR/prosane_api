"""URLconf para tests: incluye rutas de autenticación y tutores."""
from django.urls import path, include

urlpatterns = [
    path("api/v1/", include("apps.usuarios.urls")),
    path("api/v1/", include("apps.tutores.urls")),
]

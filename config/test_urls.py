"""URLconf para tests: incluye las rutas de autenticación data-driven."""
from django.urls import path, include

urlpatterns = [
    path("api/v1/", include("apps.usuarios.urls")),
]

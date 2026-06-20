"""URLconf para tests: incluye las rutas de autenticación data-driven."""
from django.urls import path, include

urlpatterns = [
    path("api/v1/", include("apps.usuarios.urls")),
    path("api/v1/escuelas/", include("apps.escuelas.urls")),
]

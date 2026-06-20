"""URLconf para tests: incluye rutas de autenticación, tutores y escuelas."""
from django.urls import path, include

urlpatterns = [
    path("api/v1/", include("apps.usuarios.urls")),
    path("api/v1/", include("apps.tutores.urls")),
    path("api/v1/escuelas/", include("apps.escuelas.urls")),
]

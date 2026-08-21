"""URLconf para tests: incluye rutas de autenticación, tutores, profesionales, escuelas y operativos."""
from django.urls import path, include

urlpatterns = [
    path("api/v1/", include("apps.usuarios.urls")),
    path("api/v1/", include("apps.tutores.urls")),
    path("api/v1/", include("apps.profesionales.urls")),
    path("api/v1/escuelas/", include("apps.escuelas.urls")),
    path("api/v1/operativos/", include("apps.operativos.urls")),
]

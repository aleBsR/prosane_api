"""
URL configuration for config project.

Rama `rama-base`: admin + endpoints de autenticación (A1) + tutores (A2).
Los endpoints de cada app se agregarán progresivamente.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.usuarios.urls")),
    path("api/v1/", include("apps.tutores.urls")),
]

"""
URL configuration for config project.

La rama `base` solo expone el admin de Django. Los endpoints de cada app se
agregarán progresivamente en ramas de features.
"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]

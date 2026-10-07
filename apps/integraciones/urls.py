from django.urls import path

from .views import ValidarDniView


urlpatterns = [
    path("validar-dni/", ValidarDniView.as_view(), name="validar-dni"),
]

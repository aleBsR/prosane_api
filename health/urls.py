from django.urls import path

from health.views import AptoListCreateView, AptoDetailView, AptoFirmarView

urlpatterns = [
    path('', AptoListCreateView.as_view(), name='apto-list-create'),
    path('<uuid:pk>/', AptoDetailView.as_view(), name='apto-detail'),
    path('<uuid:pk>/firmar/', AptoFirmarView.as_view(), name='apto-firmar'),
]

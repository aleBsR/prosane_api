from django.urls import path

from apps.auditoria import views


urlpatterns = [
    path('auditoria/cambios/', views.AuditoriaCambiosListView.as_view(), name='auditoria-cambios-list'),
]

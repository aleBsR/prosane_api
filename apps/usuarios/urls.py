from django.urls import path

from apps.usuarios import views


urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', views.RefreshView.as_view(), name='auth-refresh'),
path('auth/logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', views.MeView.as_view(), name='auth-me'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),
    path('auth/reset-password/', views.PasswordResetRequestView.as_view(), name='auth-reset-password'),
    path('auth/reset-password/confirm/', views.PasswordResetConfirmView.as_view(), name='auth-reset-password-confirm'),
    path('auth/token/', views.LoginView.as_view(), name='auth-token'),
    path('auth/token/refresh/', views.RefreshView.as_view(), name='auth-token-refresh'),
    path('usuarios/escuelas/', views.UsuariosEscuelaListCreateView.as_view(), name='usuarios-escuela-list-create'),
    path('usuarios/escuelas/<uuid:pk>/', views.UsuarioEscuelaDetailView.as_view(), name='usuario-escuela-detail'),
    path('usuarios/ayudantes/', views.UsuariosAyudantesListCreateView.as_view(), name='usuarios-ayudantes-list-create'),
    path('usuarios/ayudantes/<uuid:pk>/', views.UsuarioAyudanteDetailView.as_view(), name='usuario-ayudante-detail'),
]

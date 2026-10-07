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
    path('usuarios/escuelas/<uuid:pk>/resend-temp/', views.UsuarioEscuelaResendTempView.as_view(), name='usuario-escuela-resend-temp'),
    path('usuarios/administrativos/', views.UsuariosAdministrativosListCreateView.as_view(), name='usuarios-administrativos-list-create'),
    path('usuarios/administrativos/<uuid:pk>/', views.UsuarioAdministrativoDetailView.as_view(), name='usuario-administrativo-detail'),
    path('usuarios/administrativos/<uuid:pk>/resend-temp/', views.UsuarioAdministrativoResendTempView.as_view(), name='usuario-administrativo-resend-temp'),
    path('usuarios/superadmins/', views.UsuariosSuperadminListCreateView.as_view(), name='usuarios-superadmin-list-create'),
    path('usuarios/superadmins/<uuid:pk>/', views.UsuarioSuperadminDetailView.as_view(), name='usuario-superadmin-detail'),
    path('usuarios/superadmins/<uuid:pk>/resend-temp/', views.UsuarioSuperadminResendTempView.as_view(), name='usuario-superadmin-resend-temp'),
]

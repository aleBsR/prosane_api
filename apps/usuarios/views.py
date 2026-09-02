import secrets
from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.shortcuts import get_object_or_404

from apps.antecedentes.models import AntecedenteFamiliarTutor
from apps.tutores.models import Tutor
from apps.usuarios.action_resolution import effective_actions
from apps.usuarios.models import PasswordResetCode, Usuario
from apps.usuarios.permissions import require_action
from apps.personas.models import Persona
from apps.usuarios.serializers import (
    ChangePasswordSerializer,
    MePatchSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UsuarioAyudanteSerializer,
    UsuarioEscuelaSerializer,
)


class LoginView(TokenObtainPairView):
    """POST /auth/login/ — devuelve access + refresh tokens."""
    permission_classes = [AllowAny]


class RefreshView(TokenRefreshView):
    """POST /auth/refresh/ — devuelve un nuevo access token."""
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """POST /auth/logout/ — invalida el refresh token (blacklist)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


def _me_payload(user):
    persona = getattr(user, "persona", None)
    tutor = Tutor.objects.filter(usuario=user).first()
    antecedentes_completos = False
    if tutor:
        antecedentes_completos = AntecedenteFamiliarTutor.objects.filter(tutor=tutor).exists()
    roles = [
        {"name": r.rol, "label": r.rol.capitalize()}
        for r in user.roles.all()
    ]
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "nombre": getattr(persona, "nombre", "") or "",
            "apellido": getattr(persona, "apellido", "") or "",
            "is_staff": user.is_staff,
            "tutor_id": str(tutor.id) if tutor else None,
            "consentimiento_aceptado": tutor.consentimiento_aceptado if tutor else False,
            "antecedentes_familiares_completos": antecedentes_completos,
            "escuela_id": str(user.escuela_id) if user.escuela_id else None,
            "escuela_nombre": user.escuela.nombre if user.escuela_id else None,
        },
        "roles": roles,
        "actions": effective_actions(user),
        "meta": {
            "version": "1",
            "permissions_synced_at": timezone.now().isoformat(),
        },
    }


class MeView(APIView):
    """GET /auth/me/ — contrato congelado: user + roles + actions + meta."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_me_payload(request.user))

    def patch(self, request):
        serializer = MePatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        persona = getattr(user, "persona", None)
        data = serializer.validated_data
        # Si no tiene Persona, la creamos con dni temporal (se completa luego)
        if persona is None:
            persona = Persona.objects.create(
                nombre=data.get("nombre", ""),
                apellido=data.get("apellido", ""),
                dni=f"tmp-{user.id}",
                sexo="otro",
                fecha_nacimiento="2000-01-01",
            )
            user.persona = persona
            user.save(update_fields=["persona"])
        else:
            if "nombre" in data:
                persona.nombre = data["nombre"]
            if "apellido" in data:
                persona.apellido = data["apellido"]
            persona.save(update_fields=["nombre", "apellido", "updated_at"])
        return Response(_me_payload(user))


class ChangePasswordView(APIView):
    """POST /auth/change-password/ — cambio con old_password."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": ["La contraseña actual es incorrecta."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Contraseña actualizada correctamente."})


def _enviar_codigo_reset(email):
    """Invalida códigos previos, genera uno nuevo de 6 dígitos y lo manda por email."""
    now = timezone.now()
    PasswordResetCode.objects.filter(email=email, used_at__isnull=True).update(used_at=now)
    code = f'{secrets.randbelow(1_000_000):06d}'
    PasswordResetCode.objects.create(
        email=email,
        code=code,
        expires_at=now + timedelta(minutes=30),
    )
    send_mail(
        subject='Código para restablecer tu contraseña - PROSANE',
        message=(
            'Recibiste este correo porque pediste restablecer tu contraseña en PROSANE.\n\n'
            f'Tu código es: {code}\n\n'
            'Vence en 30 minutos. Si no lo pediste, ignorá este mensaje.'
        ),
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )


class PasswordResetRequestView(APIView):
    """POST /auth/reset-password/ — envía un código por email.

    Respuesta genérica SIEMPRE 200 (no revela si el correo está registrado,
    evita enumeración de cuentas).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower().strip()
        if Usuario.objects.filter(email__iexact=email).exists():
            _enviar_codigo_reset(email)
        return Response({
            'detail': 'Si el correo está registrado, vas a recibir un código '
                      'para restablecer tu contraseña.',
        })


class PasswordResetConfirmView(APIView):
    """POST /auth/reset-password/confirm/ — valida código y setea la password."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = Usuario.objects.filter(email__iexact=serializer.validated_data['email']).first()
        if user is None:
            return Response(
                {'detail': 'El correo no está registrado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        serializer.code_obj.used_at = timezone.now()
        serializer.code_obj.save(update_fields=['used_at', 'updated_at'])
        return Response({'detail': 'Tu contraseña fue restablecida correctamente.'})


class UsuariosAyudantesListCreateView(APIView):
    """GET/POST /usuarios/ayudantes/ — cuentas de ayudante (solo superadmin).

    El ayudante NO puede crear otros ayudantes: la acción `gestionarAyudantes`
    no está asignada a ningún rol; solo la resuelve el superuser.
    """
    permission_classes = [require_action('gestionarAyudantes')]

    def get(self, request):
        usuarios = (
            Usuario.objects
            .filter(roles__rol='ayudante')
            .distinct()
            .order_by('email')
        )
        serializer = UsuarioAyudanteSerializer(usuarios, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UsuarioAyudanteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UsuarioAyudanteDetailView(APIView):
    """GET/PATCH/DELETE /usuarios/ayudantes/<pk>/ — detalle de una cuenta ayudante."""
    permission_classes = [require_action('gestionarAyudantes')]

    def get_object(self, pk):
        return get_object_or_404(
            Usuario.objects.filter(roles__rol='ayudante').distinct(), pk=pk,
        )

    def get(self, request, pk):
        serializer = UsuarioAyudanteSerializer(self.get_object(pk))
        return Response(serializer.data)

    def patch(self, request, pk):
        usuario = self.get_object(pk)
        serializer = UsuarioAyudanteSerializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        usuario = self.get_object(pk)
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsuariosEscuelaListCreateView(APIView):
    """GET/POST /usuarios/escuelas/ — cuentas de acceso de las escuelas.

    Alta de un usuario con rol `escuela` vinculado a una escuela, y listado
    de las cuentas existentes. Solo con la acción `gestionarUsuariosEscuela`.
    """
    permission_classes = [require_action('gestionarUsuariosEscuela')]

    def get(self, request):
        usuarios = (
            Usuario.objects
            .filter(roles__rol='escuela')
            .select_related('escuela')
            .distinct()
            .order_by('email')
        )
        serializer = UsuarioEscuelaSerializer(usuarios, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UsuarioEscuelaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UsuarioEscuelaDetailView(APIView):
    """GET/PATCH/DELETE /usuarios/escuelas/<pk>/ — detalle de una cuenta escuela.

    PATCH permite reasignar la escuela, cambiar email/password y activar o
    desactivar la cuenta (`is_active`). DELETE desactiva la cuenta.
    """
    permission_classes = [require_action('gestionarUsuariosEscuela')]

    def get_object(self, pk):
        return get_object_or_404(
            Usuario.objects.filter(roles__rol='escuela').distinct(), pk=pk,
        )

    def get(self, request, pk):
        serializer = UsuarioEscuelaSerializer(self.get_object(pk))
        return Response(serializer.data)

    def patch(self, request, pk):
        usuario = self.get_object(pk)
        serializer = UsuarioEscuelaSerializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        usuario = self.get_object(pk)
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

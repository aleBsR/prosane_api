import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.shortcuts import get_object_or_404

from apps.antecedentes.models import AntecedenteFamiliarTutor
from apps.escuelas.models import Escuela
from apps.tutores.models import Tutor
from apps.usuarios.action_resolution import effective_actions
from apps.usuarios.models import AuditoriaUsuario, PasswordResetCode, Usuario
from apps.usuarios.permissions import EsAdmin, require_action
from common.mails import TEMP_EXPIRY_HOURS, enviar_codigo_reset, enviar_temporal, generar_temporal
from apps.personas.models import Persona
from apps.usuarios.serializers import (
    ChangePasswordSerializer,
    MePatchSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UsuarioAdministrativoSerializer,
    UsuarioEscuelaSerializer,
    UsuarioSuperadminSerializer,
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
    # Resolución resiliente: si la escuela fue eliminada por otra vía
    # (FK colgada), se informa sin escuela en vez de explotar con 500.
    escuela = (
        Escuela.objects.filter(pk=user.escuela_id).first()
        if user.escuela_id else None
    )
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
            "escuela_id": str(escuela.id) if escuela else None,
            "escuela_nombre": escuela.nombre if escuela else None,
            "must_change_password": bool(getattr(user, 'must_change_password', False)),
            "temporal_password_expires_at": user.temporal_password_expires_at.isoformat() if getattr(user, 'temporal_password_expires_at', None) else None,
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
    """POST /auth/change-password/ — cambio con old_password. Desbloquea must_change_password."""
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
        user.must_change_password = False
        user.temporal_password_expires_at = None
        user.save(update_fields=["password", "must_change_password", "temporal_password_expires_at"])
        return Response({"detail": "Contraseña actualizada correctamente."})


def _enviar_codigo_reset(email):
    """Invalida códigos previos, genera uno nuevo de 6 dígitos y lo manda por email (branding PROSANE)."""
    from common.mails import RESET_EXPIRY_MINUTES

    now = timezone.now()
    PasswordResetCode.objects.filter(email=email, used_at__isnull=True).update(used_at=now)
    code = f'{secrets.randbelow(1_000_000):06d}'
    PasswordResetCode.objects.create(
        email=email,
        code=code,
        expires_at=now + timedelta(minutes=RESET_EXPIRY_MINUTES),
    )
    enviar_codigo_reset(email, code)


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
        user.must_change_password = False
        user.temporal_password_expires_at = None
        user.save(update_fields=['password', 'must_change_password', 'temporal_password_expires_at'])
        serializer.code_obj.used_at = timezone.now()
        serializer.code_obj.save(update_fields=['used_at'])
        return Response({'detail': 'Tu contraseña fue restablecida correctamente.'})


class UsuarioEscuelaResendTempView(APIView):
    """POST /usuarios/escuelas/<pk>/resend-temp/ — reenvía contraseña temporal (72h)."""
    permission_classes = [require_action('gestionarUsuariosEscuela')]

    def post(self, request, pk):
        usuario = get_object_or_404(
            Usuario.objects.filter(roles__rol='escuela').distinct(), pk=pk,
        )
        temp = generar_temporal(usuario)
        usuario.set_password(temp)
        usuario.must_change_password = True
        usuario.temporal_password_expires_at = timezone.now() + timedelta(hours=TEMP_EXPIRY_HOURS)
        usuario.save(update_fields=['password', 'must_change_password', 'temporal_password_expires_at'])
        enviar_temporal(usuario.email, temp, es_reenvio=True)
        return Response({'detail': 'Contraseña temporal reenviada.'})


class UsuariosAdministrativosListCreateView(APIView):
    """GET/POST /usuarios/administrativos/ — cuentas de administrativo (solo superadmin).

    El administrativo NO puede crear otros administrativos: la acción `gestionarAdministrativos`
    no está asignada a ningún rol; solo la resuelve el superuser.
    """
    permission_classes = [require_action('gestionarAdministrativos')]

    def get(self, request):
        usuarios = (
            Usuario.objects
            .filter(roles__rol='administrativo')
            .distinct()
            .order_by('email')
        )
        serializer = UsuarioAdministrativoSerializer(usuarios, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UsuarioAdministrativoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UsuarioAdministrativoDetailView(APIView):
    """GET/PATCH/DELETE /usuarios/administrativos/<pk>/ — detalle de una cuenta administrativo."""
    permission_classes = [require_action('gestionarAdministrativos')]

    def get_object(self, pk):
        return get_object_or_404(
            Usuario.objects.filter(roles__rol='administrativo').distinct(), pk=pk,
        )

    def get(self, request, pk):
        serializer = UsuarioAdministrativoSerializer(self.get_object(pk))
        return Response(serializer.data)

    def patch(self, request, pk):
        usuario = self.get_object(pk)
        serializer = UsuarioAdministrativoSerializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        usuario = self.get_object(pk)
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsuarioAdministrativoResendTempView(APIView):
    """POST /usuarios/administrativos/<pk>/resend-temp/ — reenvía temporal (72h)."""
    permission_classes = [require_action('gestionarAdministrativos')]

    def post(self, request, pk):
        usuario = get_object_or_404(
            Usuario.objects.filter(roles__rol='administrativo').distinct(), pk=pk,
        )
        temp = generar_temporal(usuario)
        usuario.set_password(temp)
        usuario.must_change_password = True
        usuario.temporal_password_expires_at = timezone.now() + timedelta(hours=TEMP_EXPIRY_HOURS)
        usuario.save(update_fields=['password', 'must_change_password', 'temporal_password_expires_at'])
        enviar_temporal(usuario.email, temp, es_reenvio=True)
        return Response({'detail': 'Contraseña temporal reenviada.'})


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


def _ip_cliente(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '') or ''
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _auditar_gestion_superadmin(actor, objetivo, accion, request):
    AuditoriaUsuario.objects.create(
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        objetivo=objetivo,
        accion=accion,
        ip=_ip_cliente(request),
    )


def _es_ultimo_superadmin_activo(excluir_pk=None):
    qs = (
        Usuario.objects
        .filter(roles__rol='superadmin', is_active=True)
        .distinct()
    )
    if excluir_pk is not None:
        qs = qs.exclude(pk=excluir_pk)
    return not qs.exists()


def _bloqueo_desactivacion(request, usuario):
    """409 si intenta desactivarse a sí mismo o al último superadmin activo."""
    if str(request.user.pk) == str(usuario.pk):
        return Response(
            {'detail': 'No podés desactivar tu propia cuenta de superadmin.'},
            status=status.HTTP_409_CONFLICT,
        )
    if _es_ultimo_superadmin_activo(excluir_pk=usuario.pk):
        return Response(
            {'detail': 'No se puede desactivar: es el último superadmin activo.'},
            status=status.HTTP_409_CONFLICT,
        )
    return None


class UsuariosSuperadminListCreateView(APIView):
    """GET/POST /usuarios/superadmins/ — cuentas de superadmin (solo superadmin).

    El gate es `EsAdmin` (is_superuser): ningún rol por acciones puede crear
    superadmins, ni siquiera el administrativo.
    """
    permission_classes = [EsAdmin]

    def get(self, request):
        usuarios = (
            Usuario.objects
            .filter(roles__rol='superadmin')
            .distinct()
            .order_by('email')
        )
        serializer = UsuarioSuperadminSerializer(usuarios, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UsuarioSuperadminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        _auditar_gestion_superadmin(
            request.user, usuario, AuditoriaUsuario.CREAR, request,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UsuarioSuperadminDetailView(APIView):
    """GET/PATCH/DELETE /usuarios/superadmins/<pk>/ — detalle de un superadmin."""
    permission_classes = [EsAdmin]

    def get_object(self, pk):
        return get_object_or_404(
            Usuario.objects.filter(roles__rol='superadmin').distinct(), pk=pk,
        )

    def get(self, request, pk):
        serializer = UsuarioSuperadminSerializer(self.get_object(pk))
        return Response(serializer.data)

    def patch(self, request, pk):
        usuario = self.get_object(pk)
        estaba_activo = usuario.is_active
        serializer = UsuarioSuperadminSerializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if estaba_activo and serializer.validated_data.get('is_active') is False:
            bloqueo = _bloqueo_desactivacion(request, usuario)
            if bloqueo is not None:
                return bloqueo
        serializer.save()
        usuario.refresh_from_db()
        if estaba_activo and not usuario.is_active:
            _auditar_gestion_superadmin(
                request.user, usuario, AuditoriaUsuario.DESACTIVAR, request,
            )
        elif not estaba_activo and usuario.is_active:
            _auditar_gestion_superadmin(
                request.user, usuario, AuditoriaUsuario.REACTIVAR, request,
            )
        return Response(serializer.data)

    def delete(self, request, pk):
        usuario = self.get_object(pk)
        bloqueo = _bloqueo_desactivacion(request, usuario)
        if bloqueo is not None:
            return bloqueo
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        _auditar_gestion_superadmin(
            request.user, usuario, AuditoriaUsuario.DESACTIVAR, request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsuarioSuperadminResendTempView(APIView):
    """POST /usuarios/superadmins/<pk>/resend-temp/ — reenvía temporal (72h)."""
    permission_classes = [EsAdmin]

    def post(self, request, pk):
        usuario = get_object_or_404(
            Usuario.objects.filter(roles__rol='superadmin').distinct(), pk=pk,
        )
        temp = generar_temporal(usuario)
        usuario.set_password(temp)
        usuario.must_change_password = True
        usuario.temporal_password_expires_at = timezone.now() + timedelta(hours=TEMP_EXPIRY_HOURS)
        usuario.save(update_fields=['password', 'must_change_password', 'temporal_password_expires_at'])
        enviar_temporal(usuario.email, temp, es_reenvio=True)
        _auditar_gestion_superadmin(
            request.user, usuario, AuditoriaUsuario.RESEND_TEMP, request,
        )
        return Response({'detail': 'Contraseña temporal reenviada.'})

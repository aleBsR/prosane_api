import secrets
from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from rest_framework import serializers
from django.utils import timezone

from apps.usuarios.models import PasswordResetCode, Usuario, Rol, RoleUsuario
from apps.escuelas.models import Escuela

ROL_ESCUELA = 'escuela'
ROL_AYUDANTE = 'ayudante'


def _generar_temporal():
    """Genera contraseña temporal aleatoria que pasa los validators."""
    # 12-14 chars urlsafe, si falla la validación reintenta
    for _ in range(5):
        temp = secrets.token_urlsafe(10)
        try:
            validate_password(temp)
            return temp
        except Exception:
            continue
    return secrets.token_urlsafe(12)


def _enviar_temporal_por_mail(usuario, temp_password):
    """Envía mail con la temporal. No loguea la clave, solo el destinatario."""
    try:
        send_mail(
            subject='Acceso PROSANE — contraseña temporal',
            message=(
                f'Hola,\n\n'
                f'Te crearon un acceso en PROSANE ({usuario.email}).\n'
                f'Contraseña temporal: {temp_password}\n'
                f'Vence en 72 horas. Al ingresar por primera vez el sistema te pedirá cambiarla.\n\n'
                f'Ingresá en: https://prosane.salta.gob.ar/login\n\n'
                f'Si no esperabas este mail, ignoralo.\n'
            ),
            from_email=None,
            recipient_list=[usuario.email],
            fail_silently=True,
        )
    except Exception:
        pass


class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = "__all__"


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleUsuario
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "email", "persona", "is_active", "is_staff"]
        read_only_fields = ["id"]


class UsuarioEscuelaSerializer(serializers.ModelSerializer):
    escuela = serializers.PrimaryKeyRelatedField(
        queryset=Escuela.objects.filter(activa=True),
    )
    escuela_nombre = serializers.CharField(source='escuela.nombre', read_only=True)
    password = serializers.CharField(write_only=True, required=False, min_length=6)
    rol = serializers.CharField(default='escuela', read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'email', 'password', 'escuela', 'escuela_nombre',
            'rol', 'is_active',
        ]
        read_only_fields = ['id', 'rol']

    def validate_email(self, value):
        qs = Usuario.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un usuario con este email.')
        return value

    def create(self, validated_data):
        validated_data.pop('password', None)
        temp = _generar_temporal()
        rol = Rol.objects.filter(rol=ROL_ESCUELA).first()
        if rol is None:
            raise serializers.ValidationError(
                {'detail': 'El rol "escuela" no existe. Ejecutá seed_permissions.'}
            )
        usuario = Usuario.objects.create_user(
            password=temp,
            must_change_password=True,
            temporal_password_expires_at=timezone.now() + timedelta(hours=72),
            **validated_data,
        )
        RoleUsuario.objects.create(id_user=usuario, id_rol=rol)
        _enviar_temporal_por_mail(usuario, temp)
        return usuario

    def update(self, instance, validated_data):
        # El admin/ayudante gestiona email/escuela/is_active, no la contraseña.
        # La contraseña solo la cambia el propio usuario (ChangePasswordView) o vía reenvío de temporal.
        validated_data.pop('password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class UsuarioAyudanteSerializer(serializers.ModelSerializer):
    """Alta y gestión de cuentas de ayudante (solo superadmin).

    Espejo de UsuarioEscuelaSerializer pero sin vinculación a escuela: crea un
    Usuario con rol `ayudante`.
    """
    password = serializers.CharField(write_only=True, required=False, min_length=6)
    rol = serializers.CharField(default=ROL_AYUDANTE, read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'email', 'password', 'rol', 'is_active']
        read_only_fields = ['id', 'rol']

    def validate_email(self, value):
        qs = Usuario.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un usuario con este email.')
        return value

    def create(self, validated_data):
        validated_data.pop('password', None)
        temp = _generar_temporal()
        rol = Rol.objects.filter(rol=ROL_AYUDANTE).first()
        if rol is None:
            raise serializers.ValidationError(
                {'detail': 'El rol "ayudante" no existe. Ejecutá seed_permissions.'}
            )
        usuario = Usuario.objects.create_user(
            password=temp,
            must_change_password=True,
            temporal_password_expires_at=timezone.now() + timedelta(hours=72),
            **validated_data,
        )
        RoleUsuario.objects.create(id_user=usuario, id_rol=rol)
        _enviar_temporal_por_mail(usuario, temp)
        return usuario

    def update(self, instance, validated_data):
        validated_data.pop('password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class PasswordResetRequestSerializer(serializers.Serializer):
    """POST /auth/reset-password/ — pide el envío del código por email."""
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """POST /auth/reset-password/confirm/ — valida el código y setea la password."""
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=6)

    def validate(self, attrs):
        code_obj = (
            PasswordResetCode.objects.filter(
                email__iexact=attrs['email'],
                code=attrs['code'],
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).first()
        )
        if code_obj is None:
            raise serializers.ValidationError('El código es inválido o expiró.')
        self.code_obj = code_obj
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """POST /auth/change-password/ — cambio autenticado."""
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=6)

    def validate_new_password(self, value):
        validate_password(value, self.context.get('request') and self.context['request'].user)
        return value


class MePatchSerializer(serializers.Serializer):
    """PATCH /auth/me/ — edita nombre/apellido de la Persona del usuario."""
    nombre = serializers.CharField(required=False, allow_blank=True, max_length=256)
    apellido = serializers.CharField(required=False, allow_blank=True, max_length=256)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('Enviá al menos nombre o apellido.')
        return attrs
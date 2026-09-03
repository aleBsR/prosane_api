import secrets
from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.profesionales.models import Profesional
from apps.profesionales.services.services_refeps import RefepsError, RefepsService
from apps.usuarios.models import Rol, RoleUsuario, Usuario

ROLES_PROFESIONAL = ("medico", "odontologo")


def _generar_temporal():
    for _ in range(5):
        cand = secrets.token_urlsafe(10)
        try:
            validate_password(cand)
            return cand
        except Exception:
            continue
    return secrets.token_urlsafe(12)


def _enviar_temporal(usuario, temp):
    try:
        send_mail(
            subject='Acceso PROSANE — contraseña temporal',
            message=(
                f'Hola,\n\n'
                f'Te crearon un acceso en PROSANE ({usuario.email}).\n'
                f'Contraseña temporal: {temp}\n'
                f'Vence en 72 horas. Al ingresar el sistema te pedirá cambiarla.\n\n'
                f'Ingresá en: https://prosane.salta.gob.ar/login\n'
            ),
            from_email=None,
            recipient_list=[usuario.email],
            fail_silently=True,
        )
    except Exception:
        pass


class ProfesionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profesional
        fields = "__all__"


def _consultar_refeps(matricula):
    """Consulta REFEPS sin propagar caídas (None si no disponible o no encontrada)."""
    try:
        return RefepsService.consultar(matricula)
    except RefepsError:
        return None


class ProfesionalCreateSerializer(serializers.Serializer):
    """Alta/edición de cuentas de profesionales (médico/odontólogo).

    Crea Usuario + RoleUsuario (rol médico/odontólogo) + Profesional (matrícula).
    El nombre/apellido se autocompletan desde REFEPS si la matrícula existe; si el
    servicio está caído o la matrícula no se encuentra, se usan los valores manuales
    (que pueden quedar vacíos sin bloquear el alta).
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=False, min_length=6)
    rol = serializers.ChoiceField(choices=ROLES_PROFESIONAL)
    matricula = serializers.CharField(max_length=256)
    nombre = serializers.CharField(max_length=256, required=False, allow_blank=True)
    apellido = serializers.CharField(max_length=256, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    def validate_email(self, value):
        qs = Usuario.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        validated_data.pop("password", None)
        temp = _generar_temporal()
        rol_name = validated_data["rol"]
        matricula = validated_data["matricula"]
        nombre = validated_data.get("nombre") or ""
        apellido = validated_data.get("apellido") or ""

        refeps = _consultar_refeps(matricula)
        if refeps:
            nombre = nombre or refeps.get("nombre", "") or ""
            apellido = apellido or refeps.get("apellido", "") or ""

        with transaction.atomic():
            usuario = Usuario.objects.create_user(
                email=email,
                password=temp,
                must_change_password=True,
                temporal_password_expires_at=timezone.now() + timedelta(hours=72),
            )
            rol, _ = Rol.objects.get_or_create(rol=rol_name)
            RoleUsuario.objects.create(id_user=usuario, id_rol=rol)
            Profesional.objects.create(
                matricula=matricula,
                id_usuario=usuario,
                nombre=nombre or None,
                apellido=apellido or None,
            )
        _enviar_temporal(usuario, temp)
        return usuario

    def update(self, instance, validated_data):
        validated_data.pop("password", None)
        rol_name = validated_data.pop("rol", None)
        email = validated_data.pop("email", None)
        is_active = validated_data.pop("is_active", None)
        if email:
            instance.email = email
        if is_active is not None:
            instance.is_active = is_active
        instance.save()

        if rol_name:
            rol, _ = Rol.objects.get_or_create(rol=rol_name)
            RoleUsuario.all_objects.filter(id_user=instance).hard_delete()
            RoleUsuario.objects.create(id_user=instance, id_rol=rol)

        profesional = instance.profesional_set.first()
        if "matricula" in validated_data:
            matricula = validated_data["matricula"]
            if profesional:
                profesional.matricula = matricula
            else:
                profesional = Profesional.objects.create(
                    matricula=matricula, id_usuario=instance
                )
        if profesional:
            if "nombre" in validated_data:
                profesional.nombre = validated_data.get("nombre") or None
            if "apellido" in validated_data:
                profesional.apellido = validated_data.get("apellido") or None
            profesional.save()
        return instance

    def to_representation(self, instance):
        profesional = instance.profesional_set.first()
        rol = instance.roles.first()
        return {
            "id": str(instance.id),
            "email": instance.email or "",
            "rol": rol.rol if rol else "",
            "matricula": profesional.matricula if profesional else "",
            "nombre": profesional.nombre or "" if profesional else "",
            "apellido": profesional.apellido or "" if profesional else "",
            "is_active": instance.is_active,
        }
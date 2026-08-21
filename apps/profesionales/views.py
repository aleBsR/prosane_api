from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.profesionales.serializers import (
    ROLES_PROFESIONAL,
    ProfesionalCreateSerializer,
)
from apps.profesionales.services.services_refeps import RefepsError, RefepsService
from apps.usuarios.models import Usuario
from apps.usuarios.permissions import require_action


class ValidarMatriculaView(APIView):
    """POST /api/v1/profesionales/validar-matricula/ — consulta REFEPS por matrícula.

    Devuelve los datos del profesional (nombre, apellido, profesión) para
    autocompletar el formulario. 404 si la matrícula no existe; 503 si REFEPS
    está caído (el alta igual se puede completar de forma manual).
    """

    permission_classes = [require_action("gestionarProfesionales")]

    def post(self, request):
        matricula = (request.data.get("matricula") or "").strip()
        if not matricula:
            return Response(
                {"detail": "La matrícula es obligatoria."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = RefepsService.consultar(matricula)
        except RefepsError:
            return Response(
                {"detail": "El servicio REFEPS no está disponible."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not data:
            return Response(
                {"detail": "Matrícula no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "nombre": data.get("nombre", "") or "",
                "apellido": data.get("apellido", "") or "",
                "profesion": data.get("profesion", "") or "",
                "dni": data.get("dni", "") or "",
                "sexo": data.get("sexo", "") or "",
                "fecha_nacimiento": data.get("fecha_nacimiento", "") or "",
            }
        )


class ProfesionalesListCreateView(APIView):
    """GET/POST /api/v1/profesionales/ — cuentas de profesionales (médico/odontólogo).

    Listado de las cuentas con rol `medico` u `odontologo`, y alta de una cuenta
    nueva (Usuario + rol + Profesional con matrícula). Solo con la acción
    `gestionarProfesionales`.
    """

    permission_classes = [require_action("gestionarProfesionales")]

    def get(self, request):
        usuarios = (
            Usuario.objects.filter(roles__rol__in=ROLES_PROFESIONAL)
            .prefetch_related("roles", "profesional_set")
            .distinct()
            .order_by("email")
        )
        serializer = ProfesionalCreateSerializer(usuarios, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProfesionalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProfesionalDetailView(APIView):
    """GET/PATCH/DELETE /api/v1/profesionales/<uuid:pk>/ — detalle de una cuenta.

    PATCH permite cambiar email/password, rol, matrícula y nombre/apellido.
    DELETE desactiva la cuenta (`is_active=False`).
    """

    permission_classes = [require_action("gestionarProfesionales")]

    def get_object(self, pk):
        return get_object_or_404(
            Usuario.objects.filter(roles__rol__in=ROLES_PROFESIONAL).distinct(),
            pk=pk,
        )

    def get(self, request, pk):
        serializer = ProfesionalCreateSerializer(self.get_object(pk))
        return Response(serializer.data)

    def patch(self, request, pk):
        usuario = self.get_object(pk)
        serializer = ProfesionalCreateSerializer(
            usuario, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        usuario = self.get_object(pk)
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
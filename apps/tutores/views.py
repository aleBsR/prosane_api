from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.tutores.serializers import (
    HijoCreateSerializer,
    HijoOutputSerializer,
    TutorRegistrationSerializer,
)
from apps.tutores.services.hijos import HijosError, crear_hijo, listar_hijos
from apps.tutores.services.registration import TutorRegistrationError, registrar_tutor


class RegisterTutorView(APIView):
    """POST /api/v1/auth/register/tutor/ — registro público de tutor."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TutorRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = registrar_tutor(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                persona_data=serializer.validated_data["persona"],
                parentesco=serializer.validated_data.get("parentesco"),
            )
        except TutorRegistrationError as exc:
            return Response(
                {exc.field or "non_field_errors": [exc.message]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_201_CREATED)


class TutorHijosView(APIView):
    """GET/POST /api/v1/tutores/<uuid:pk>/hijos/ — gestión de hijos del tutor."""

    permission_classes = [IsAuthenticated]

    def _verificar_tutor(self, request, tutor_pk):
        """Solo el tutor dueño puede gestionar sus hijos."""
        from apps.tutores.models import Tutor

        try:
            tutor = Tutor.objects.select_related("usuario").get(id=tutor_pk)
        except Tutor.DoesNotExist:
            return None, Response(
                {"detail": "Tutor no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if tutor.usuario != request.user and not request.user.is_superuser:
            return None, Response(
                {"detail": "No tenés permiso para gestionar estos hijos."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return tutor, None

    def get(self, request, pk):
        tutor, error = self._verificar_tutor(request, pk)
        if error:
            return error

        hijos = listar_hijos(tutor.id)
        serializer = HijoOutputSerializer(hijos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        tutor, error = self._verificar_tutor(request, pk)
        if error:
            return error

        serializer = HijoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            hijo = crear_hijo(tutor.id, serializer.validated_data)
        except HijosError as exc:
            return Response(
                {exc.field or "non_field_errors": [exc.message]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output = HijoOutputSerializer(hijo)
        return Response(output.data, status=status.HTTP_201_CREATED)

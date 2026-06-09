from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q

from core.models import Personas
from patients.models import Pacientes
from patients.serializers import PacientesSerializer
from .models import Profesionales
from .serializers import (
    ProfesionalPerfilSerializer,
    ProfesionalesSerializer,
    ValidarMatriculaSerializer,
)
from .services.services_refeps import RefepsService


class ProfesionalPerfilAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        persona = getattr(user, 'persona', None)

        try:
            profesional = Profesionales.objects.get(id_usuario=user)
        except Profesionales.DoesNotExist:
            return Response(
                {"detail": "No se encontró un perfil profesional para este usuario."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = {
            'email': user.email,
            'persona': persona,
            'profesional': profesional,
        }
        serializer = ProfesionalPerfilSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user
        persona = getattr(user, 'persona', None)

        if persona is None:
            return Response(
                {"detail": "Este usuario no tiene datos de persona asociados."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            profesional = Profesionales.objects.get(id_usuario=user)
        except Profesionales.DoesNotExist:
            return Response(
                {"detail": "No se encontró un perfil profesional para este usuario."},
                status=status.HTTP_404_NOT_FOUND
            )

        instance = {
            'user': user,
            'persona_obj': persona,
            'profesional_obj': profesional,
        }

        serializer = ProfesionalPerfilSerializer(
            instance, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validar_matricula(request):
    serializer = ValidarMatriculaSerializer(data=request.data)
    if serializer.is_valid():
        datos = RefepsService.consultar(serializer.validated_data['matricula'])
        return Response(datos, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuscarPacienteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dni = request.query_params.get('dni', '').strip()

        if not dni:
            return Response(
                {"detail": "Parámetro 'dni' requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        personas = Personas.objects.filter(
            Q(dni__icontains=dni) | Q(dni=dni)
        )

        pacientes = Pacientes.objects.filter(persona__in=personas).select_related(
            'persona', 'domicilio', 'responsable__persona'
        )

        serializer = PacientesSerializer(pacientes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

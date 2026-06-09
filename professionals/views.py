from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes

from authentication.permissions import EsProfesional

from .models import Profesionales
from .serializers import (
    ProfesionalPerfilSerializer,
    ProfesionalesSerializer,
    ValidarMatriculaSerializer,
)


class ProfesionalPerfilAPIView(APIView):
    permission_classes = [EsProfesional]

    def get(self, request):
        try:
            profesional = Profesionales.objects.get(id_usuario=request.user)
        except Profesionales.DoesNotExist:
            return Response(
                {"detail": "No se encontró un perfil profesional para este usuario."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProfesionalPerfilSerializer({
            'email': request.user.email,
            'persona': request.user.persona,
            'profesional': profesional,
        })
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        persona = getattr(request.user, 'persona', None)
        if persona is None:
            return Response(
                {"detail": "Este usuario no tiene datos de persona asociados."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            profesional = Profesionales.objects.get(id_usuario=request.user)
        except Profesionales.DoesNotExist:
            return Response(
                {"detail": "No se encontró un perfil profesional para este usuario."},
                status=status.HTTP_404_NOT_FOUND
            )

        instance = {
            'user': request.user,
            'persona_obj': persona,
            'profesional_obj': profesional,
        }
        serializer = ProfesionalPerfilSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([EsProfesional])
def validar_matricula(request):
    serializer = ValidarMatriculaSerializer(data=request.data)
    if serializer.is_valid():
        return Response(
            serializer.context['datos_refeps'],
            status=status.HTTP_200_OK
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
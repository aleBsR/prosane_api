

from rest_framework.decorators import api_view, permission_classes

from authentication.permissions import EsTutor
from .serializers import PacientesSerializer

@api_view(['POST'])
@permission_classes([EsTutor])
def crear_paciente(request):

    paciente = PacientesSerializer(data=request.data)

    if paciente.is_valid():
        paciente.save()


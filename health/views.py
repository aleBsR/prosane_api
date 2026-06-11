from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import require_action
from health.models import Apto
from health.serializers import AptoSerializer
from health import services


class AptoListCreateView(APIView):
    def get_permissions(self):
        action = 'crearApto' if self.request.method == 'POST' else 'verApto'
        return [require_action(action)()]

    def get(self, request):
        aptos = Apto.objects.all()
        return Response(AptoSerializer(aptos, many=True).data)

    def post(self, request):
        paciente_id = request.data.get('paciente')
        if not paciente_id:
            return Response({'paciente': ['Requerido.']}, status=status.HTTP_400_BAD_REQUEST)
        from patients.models import Pacientes
        paciente = get_object_or_404(Pacientes, pk=paciente_id)
        apto = services.crear_apto(paciente=paciente, profesional=request.user)
        return Response(AptoSerializer(apto).data, status=status.HTTP_201_CREATED)


class AptoDetailView(APIView):
    def get_permissions(self):
        action = 'crearApto' if self.request.method in ('PATCH', 'PUT') else 'verApto'
        return [require_action(action)()]

    def get(self, request, pk):
        return Response(AptoSerializer(get_object_or_404(Apto, pk=pk)).data)

    def patch(self, request, pk):
        apto = get_object_or_404(Apto, pk=pk)
        try:
            services.editar_apto(
                apto,
                peso_kg=request.data.get('peso_kg'),
                altura_cm=request.data.get('altura_cm'),
                observaciones=request.data.get('observaciones'),
            )
        except services.AptoInmutableError as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(AptoSerializer(apto).data)


class AptoFirmarView(APIView):
    permission_classes = [require_action('firmarApto')]

    def post(self, request, pk):
        apto = get_object_or_404(Apto, pk=pk)
        try:
            services.firmar_apto(apto, now=timezone.now())
        except services.AptoInmutableError as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(AptoSerializer(apto).data, status=status.HTTP_200_OK)

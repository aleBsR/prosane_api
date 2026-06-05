from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Pacientes, Responsables, Antecedentesfamiliares, Antecedentespersonales
from .serializers import (
    PacientesSerializer, 
    ResponsablesSerializer, 
    AntecedentesfamiliaresSerializer, 
    AntecedentespersonalesSerializer
)

class PacienteListCreateAPIView(APIView):
    """
    Vista para listar y crear pacientes.
    - GET: Lista los pacientes. Si no está autenticado, lista todos.
    - POST: Crea un nuevo paciente.
    """
    permission_classes = [AllowAny] # Descomentar para activar seguridad JWT

    def get(self, request):
        # Soporte para pruebas sin autenticación (AnonymousUser)
        if not request.user or request.user.is_anonymous:
            pacientes = Pacientes.objects.all()
        else:
            try:
                persona = getattr(request.user, 'id_persona', None)
                if not persona:
                    pacientes = Pacientes.objects.all()
                else:
                    responsable = Responsables.objects.get(id_persona=persona)
                    pacientes = Pacientes.objects.filter(id_responsable=responsable)
            except Responsables.DoesNotExist:
                pacientes = Pacientes.objects.all()

        serializer = PacientesSerializer(pacientes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data.copy()

        # Si el usuario está autenticado e ingresa como un tutor, auto-asignamos su responsable
        is_tutor = False
        if request.user and not request.user.is_anonymous:
            try:
                persona = getattr(request.user, 'id_persona', None)
                if persona:
                    responsable = Responsables.objects.get(id_persona=persona)
                    data['id_responsable'] = responsable.id
                    is_tutor = True
            except Responsables.DoesNotExist:
                pass

        # Si no es tutor autenticado, requerimos que el POST envíe 'id_responsable' en el cuerpo JSON
        if not is_tutor and 'id_responsable' not in data:
            return Response(
                {"id_responsable": ["Este campo es requerido cuando no se está logueado como tutor/responsable."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PacientesSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PacienteDetailAPIView(APIView):
    """
    Vista para consultar, actualizar y eliminar un paciente.
    """
    permission_classes = [AllowAny]

    def get_object(self, pk):
        return get_object_or_404(Pacientes, pk=pk)

    def get(self, request, pk):
        paciente = self.get_object(pk)
        serializer = PacientesSerializer(paciente)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        paciente = self.get_object(pk)
        serializer = PacientesSerializer(paciente, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        paciente = self.get_object(pk)
        serializer = PacientesSerializer(paciente, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        paciente = self.get_object(pk)
        paciente.delete()
        return Response({"message": "Paciente eliminado correctamente"}, status=status.HTTP_204_NO_CONTENT)


class AntecedentesFamiliaresAPIView(APIView):
    """
    Vista para obtener y guardar los antecedentes familiares de un paciente.
    """
    permission_classes = [AllowAny]

    def get(self, request, patient_id):
        paciente = get_object_or_404(Pacientes, pk=patient_id)
        try:
            antecedentes = Antecedentesfamiliares.objects.get(id_paciente=paciente)
            serializer = AntecedentesfamiliaresSerializer(antecedentes)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Antecedentesfamiliares.DoesNotExist:
            return Response(
                {"detail": "No se encontraron antecedentes familiares para este paciente."},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, patient_id):
        paciente = get_object_or_404(Pacientes, pk=patient_id)
        antecedentes, created = Antecedentesfamiliares.objects.get_or_create(id_paciente=paciente)
        
        data = request.data.copy()
        data['id_paciente'] = paciente.id
        
        serializer = AntecedentesfamiliaresSerializer(antecedentes, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=status_code)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AntecedentesPersonalesAPIView(APIView):
    """
    Vista para obtener y guardar los antecedentes personales de un paciente.
    """
    permission_classes = [AllowAny]

    def get(self, request, patient_id):
        paciente = get_object_or_404(Pacientes, pk=patient_id)
        try:
            antecedentes = Antecedentespersonales.objects.get(id_paciente=paciente)
            serializer = AntecedentespersonalesSerializer(antecedentes)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Antecedentespersonales.DoesNotExist:
            return Response(
                {"detail": "No se encontraron antecedentes personales para este paciente."},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, patient_id):
        paciente = get_object_or_404(Pacientes, pk=patient_id)
        
        defaults_valores = {
            'nacio_prematuro': 'NO',
            'peso_nacimiento': '0',
            'convulsiones_epilepsia': 'NO',
            'mareos_desmayos': 'NO',
            'infecciones_urinarias': 'NO',
            'asma_espasmos': 'NO',
            'tuberculosis': 'NO',
            'diabetes': 'NO',
            'hipertension': 'NO',
            'cardiopatia_congenita': 'NO',
            'traumatismo_internacion': 'NO',
            'diarrea_frecuente': 'NO',
            'infecciones_oido': 'NO',
            'causa_hospitalizacion': 'NO',
            'rabia_tratamiento': 'NO',
            'descripcion_tratamiento': 'NINGUNO',
            'ultima_consulta_medica': 'NINGUNA',
            'otros_problemas_salud': 'NINGUNO',
            'primera_menstruacion': 'NO',
            'edad_primera_menstruacion': 0
        }
        
        antecedentes, created = Antecedentespersonales.objects.get_or_create(
            id_paciente=paciente,
            defaults=defaults_valores
        )
        
        data = request.data.copy()
        data['id_paciente'] = paciente.id
        
        serializer = AntecedentespersonalesSerializer(antecedentes, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=status_code)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResponsableProfileAPIView(APIView):
    """
    Vista para gestionar el perfil del tutor/responsable autenticado.
    Nota: Requiere autenticación obligatoriamente.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user or request.user.is_anonymous:
            return Response(
                {"detail": "Las credenciales de autenticación no fueron provistas o el usuario es anónimo."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        persona = getattr(request.user, 'id_persona', None)
        if not persona:
            return Response(
                {"error": "El usuario actual no tiene una persona física asociada en la base de datos."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            responsable = Responsables.objects.get(id_persona=persona)
            serializer = ResponsablesSerializer(responsable)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Responsables.DoesNotExist:
            return Response(
                {"detail": "No se encontró un perfil de tutor/responsable para este usuario."},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request):
        if not request.user or request.user.is_anonymous:
            return Response(
                {"detail": "Las credenciales de autenticación no fueron provistas o el usuario es anónimo."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        persona = getattr(request.user, 'id_persona', None)
        if not persona:
            return Response(
                {"error": "El usuario actual no tiene una persona física asociada en la base de datos."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        responsable, created = Responsables.objects.get_or_create(
            id_persona=persona,
            defaults={'parentesco': 'OTRO'}
        )
        
        serializer = ResponsablesSerializer(responsable, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=status_code)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
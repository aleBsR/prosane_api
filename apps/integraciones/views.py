from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integraciones.federador import (
    FederadorAuthError,
    FederadorError,
    FederadorNoConfigurado,
    renaper_cobertura,
    renaper_persona,
)
from apps.usuarios.permissions import require_any_action


class ValidarDniView(APIView):
    """GET /api/v1/validar-dni/?dni=&sexo=[&tipo_dni=][&cobertura=1] — RENAPER directo.

    Devuelve el JSON filiatorio del Federador tal cual (apellido, nombres,
    fecha de nacimiento, domicilio, etc.) para autocompletar formularios.
    Con &cobertura=1 agrega la obra social (PUCO/SISA) bajo la clave
    "cobertura". 404 si no está en RENAPER; 503 si el servicio no está
    disponible o no hay credenciales. Solo DNI (Pasaporte → 400).
    """

    permission_classes = [
        require_any_action("registrarAlumnoEscuela", "gestionarUsuariosEscuela")
    ]

    def get(self, request):
        dni = (request.query_params.get("dni") or "").strip()
        tipo = (request.query_params.get("tipo_dni") or "DNI").strip()
        sexo = (request.query_params.get("sexo") or "").strip()
        con_cobertura = (request.query_params.get("cobertura") or "").strip() == "1"
        if not dni:
            return Response(
                {"detail": "El DNI es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tipo and tipo.upper() != "DNI":
            return Response(
                {"detail": "RENAPER solo valida DNI."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = renaper_persona(dni, sexo)
        except FederadorNoConfigurado as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except FederadorAuthError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except FederadorError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not data:
            return Response(
                {"detail": "Persona no encontrada en RENAPER."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if con_cobertura:
            try:
                data = dict(data)
                data["cobertura"] = renaper_cobertura(dni, sexo)
            except FederadorError:
                data = dict(data)
                data["cobertura"] = None
        return Response(data)

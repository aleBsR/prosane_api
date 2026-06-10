from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.response import Response
from rest_framework import status

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny

from authentication.me import build_me_payload
from authentication.action_resolution import effective_actions

from authentication.models import Roles, Usuarios
from authentication.serializers import (
    RolesSerializer, UserSerializer, UserRoleSerializer, LoginSerializer,
    RegisterTutorSerializer, RegisterProfesionalSerializer
)

from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import EsMedico, EsAdmin


def getCustomToken(user):
    token = RefreshToken.for_user(user)
    roles = user.roles.all()
    roles_serializer = RolesSerializer(roles, many=True)
    token['roles'] = roles_serializer.data
    return token


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    usuario = UserSerializer(data=request.data)
    if usuario.is_valid():
        usuario.save()
        return Response(
            {'message': 'User created succesfully', 'data': usuario.data},
            status=status.HTTP_201_CREATED
        )
    return Response({'error': usuario.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_tutor(request):
    serializer = RegisterTutorSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {'message': 'Tutor created succesfully'},
            status=status.HTTP_201_CREATED
        )
    return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_profesional(request):
    serializer = RegisterProfesionalSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {'message': 'Professional created succesfully'},
            status=status.HTTP_201_CREATED
        )
    return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user'] 
        token = getCustomToken(user)
        return Response({'token': str(token.access_token)}, status=status.HTTP_200_OK)
    return Response({'error': serializer.errors}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([EsAdmin])
def asignar_rol(request, id):
    usuario = get_object_or_404(Usuarios, pk=id)
    user_rol = UserRoleSerializer(data=request.data, context={'id_user': usuario})
    if user_rol.is_valid():
        user_rol.save(id_user=usuario)
        return Response({'message': 'rol asigned', 'data': user_rol.data})
    return Response({'error': user_rol.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([EsMedico])
def solo_medicos(request):
    return Response({'message': 'Solo medicos pueden ver esto'}, status=status.HTTP_200_OK)


@api_view(['GET'])
def me(request):
    """Sesión del usuario autenticado: datos + roles + acciones (contrato congelado).

    Slice 2: roles y acciones salen de la DB (effective_actions, resolución computada).
    El contrato es byte-por-byte idéntico al de Fase 1 (test de equivalencia lo blinda).
    Usa el permiso default (IsAuthenticated).
    """
    user = request.user
    role_names = list(user.roles.values_list('rol', flat=True))
    payload = build_me_payload(user, role_names, effective_actions(user), now=timezone.now())
    return Response(payload)
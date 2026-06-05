from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from django.contrib.auth import authenticate

from rest_framework.response import Response
from rest_framework import status

from rest_framework.decorators import api_view, authentication_classes , permission_classes
from rest_framework.permissions import AllowAny

from authentication.models import Roles, UserManager, UserRole, Usuarios
from authentication.serializers import RolesSerializer, UserSerializer, UserRoleSerializer, LoginSerializer


from core.models import Personas
from core.serializers import PersonasSerializer

from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import EsMedico, EsAdmin

# Create your views here.


def getCustomToken(user):
    token = RefreshToken.for_user(user)
    roles = user.roles.all() # obtenemos los roles del usuario a través de la relación ManyToMany definida en el modelo Usuarios.
    roles_serializer = RolesSerializer(roles, many=True)
    token['roles'] = roles_serializer.data #guardamos los roles
    return token

@api_view(['POST'])
@permission_classes([AllowAny]) #Esto permite que cualquier usuario ingrese al endpoint
def register(request):
    # La validacion va en el Serializer
    usuario = UserSerializer(data=request.data)
    if usuario.is_valid():
        usuario.save()
        return Response({'message': 'User created succesfully.', 'data':usuario.data}, status=status.HTTP_201_CREATED)
    else:
        return Response({'message': usuario.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    # La validación de credenciales va en el serializer (validate)
    serializer = LoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token = getCustomToken(user)
        return Response({'token': str(token.access_token)}, status=status.HTTP_200_OK)
    return Response({'error': serializer.errors}, status=status.HTTP_401_UNAUTHORIZED)
    

@api_view(['POST'])
@permission_classes([EsAdmin])
def asignar_rol(request, id):
   usuario = get_object_or_404(Usuarios,pk=id)
   user_rol = UserRoleSerializer(data=request.data, context={'id_user': usuario})
   if user_rol.is_valid():
       user_rol.save(id_user=usuario)
       return Response({'message':'rol asigned','data':user_rol.data})
   else:
       return Response({'error': user_rol.errors}, status=status.HTTP_400_BAD_REQUEST)

    



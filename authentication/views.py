from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from django.contrib.auth import authenticate

from rest_framework.response import Response
from rest_framework import status

from rest_framework.decorators import api_view, authentication_classes , permission_classes
from rest_framework.permissions import AllowAny

from authentication.models import Roles, UserManager, UserRole, Usuarios
from authentication.serializers import RolesSerializer, UserSerializer


from core.models import Personas
from core.serializers import PersonasSerializer

from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import EsMedico

# Create your views here.


def getCustomToken(user):
    token = RefreshToken.for_user(user)
    roles = user.roles.all() # obtenemos los roles del usuario a través de la relación ManyToMany definida en el modelo Usuarios.
    roles_serializer = RolesSerializer(roles, many=True)
    token['roles'] = roles_serializer.data #guardamos los roles
    return token

@api_view(['POST'])
@permission_classes([AllowAny]) #Esto permite que cualquier usuario,
#incluso aquellos que no están autenticados puedan acceder a esta vista para registrarse. 
def register(request):
    #primero crear la persona, luego el usuario y asociarlo a la persona creada
    nombre = request.data.get('nombre')
    apellido = request.data.get('apellido')
    dni = request.data.get('dni')
    tipo_dni = request.data.get('tipo_dni')
    email = request.data.get('email')
    password = request.data.get('password')

    #validar que se hayan proporcionado todos los campos necesarios
    if not all([nombre,apellido,dni,tipo_dni,email,password]):
        return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    # verificar si el email y el dni ya existen en la base de datos
    if Personas.objects.filter(dni=dni).exists():
        return Response({'error': 'A user with this dni already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    if Usuarios.objects.filter(email=email).exists():
        return Response({'error': 'A user with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)

    
    persona = PersonasSerializer(data={'nombre': nombre, 'apellido': apellido, 'dni': dni, 'tipo_dni': tipo_dni})
    if not persona.is_valid():
        return Response({'error': 'Invalid data provided for persona'}, status=status.HTTP_400_BAD_REQUEST)
    


    #guardamos la persona en la db 
    persona.save()

    usuario = UserSerializer(data={'email': email, 'password': password, 'persona': persona.instance.id})

    if usuario.is_valid():
        usuario.save() # se guarda en la db
        UserRole.objects.create( # creamos la fila en la db para asociar el usuario con su rol
            id_user=usuario.instance,
            id_rol=Roles.objects.get(rol='usuario')  # Asigna el rol 'user' por defecto al nuevo usuario    
        )
        return Response(
            {'message': 'User created successfully', 'user': usuario.data},
            status=status.HTTP_201_CREATED
        )
    return Response(usuario.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
 
    email = request.data.get('email')
    password = request.data.get('password')

    if not all ([email, password]):
        return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    #django valida
    user = authenticate(request, username=email, password=password)

    if user is not None:
        token = getCustomToken(user)
        print(token.payload)
        access_token = str(token.access_token)
        return Response({'token': access_token}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)
    

#falta permitir que solo el admin agregue
@api_view(['POST'])
@permission_classes([AllowAny])
def asignar_rol(request, id):

    #obtener usuario y rol
    userid = get_object_or_404(Usuarios,pk=id)
    rol = get_object_or_404(Roles, rol=request.data.get('rol'))

    #validar si el usuario ya tiene ese rol
    #Si no, lo crea
    user,created = UserRole.objects.get_or_create(
        id_user = userid,
        id_rol = rol
    )

    if created:
        return Response({'message':'Rol asigned correctly'},status=status.HTTP_201_CREATED)
    else:
        return Response({'message': 'Already with the role'}, status=status.HTTP_409_CONFLICT)
    
@api_view(['GET'])
@permission_classes([EsMedico])
def solo_medicos(request):
    return Response({'message':'YOU ARE ALLOWED'},status=status.HTTP_202_ACCEPTED)




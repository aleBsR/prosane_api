from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status

from rest_framework.decorators import api_view

from authentication.models import UserManager, Usuarios
from authentication.serializers import UserSerializer


from core.models import Personas
from core.serializers import PersonasSerializer

# Create your views here.

@api_view(['POST'])
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
        usuario.save()
        return Response(
            {'message': 'User created successfully', 'user': usuario.data},
            status=status.HTTP_201_CREATED
        )
    return Response(usuario.errors, status=status.HTTP_400_BAD_REQUEST)


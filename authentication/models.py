from django.db import models
from django.contrib.auth.models import AbstractBaseUser, AbstractUser, PermissionsMixin


class Roles(models.Model):
    rol = models.CharField(max_length=50, blank=True, null=True)
    ruta = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'


class UserManager(models.Manager):

    #**extra_fields es un diccionario que permite pasar campos adicionales al crear un usuario. 
    #Esto es útil para agregar campos personalizados al modelo de usuario sin tener que modificar la firma del método create_user.
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The email field must be provided')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password) 
        #set_password es un método proporcionado por AbstractBaseUser hashea
        # la contraseña antes de almacenarla en la base de datos.
        user.save() #Guarda el usuario en la base de datos utilizando el método save() del modelo. 
        return user
    
    def create_superuser(self,email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser',True)
        return self.create_user(email,password, **extra_fields)
        

class Usuarios(AbstractBaseUser,PermissionsMixin):
    id = models.UUIDField(primary_key=True) #UUIDField es un campo de modelo que almacena un identificador único universal (UUID) como clave primaria para el modelo Usuarios. Esto garantiza que cada usuario tenga un identificador único y no se repita, lo que es especialmente útil en aplicaciones distribuidas o cuando se requiere una mayor seguridad en la identificación de usuarios.
    id_persona = models.ForeignKey(
        'core.Personas', models.DO_NOTHING,
        db_column='id_persona', blank=True, null=True
    )
    email = models.CharField(unique=True, max_length=256, blank=True, null=True)
    password = models.CharField(max_length=256, db_column='password_hash', blank=True, null=True)

    is_active = models.BooleanField(default=True) #Indica si el usuario está activo o no. 
    #Si es False, el usuario no podrá iniciar sesión ni realizar acciones en la aplicación.
    #Is_active lo utiliza JWT para verificar si el usuario está activo antes de generar un token de acceso. 
    is_staff = models.BooleanField(default=False) #Indica si el usuario tiene permisos de administrador o no. 
    #Si es True, el usuario podrá acceder al panel de administración de Django y realizar acciones administrativas en la aplicación.
    date_joined = models.DateTimeField(auto_now_add=True) #Almacena la fecha y hora en que el usuario se unió a la aplicación.


    USERNAME_FIELD = 'email' #Indica que el campo email se utilizará como el identificador único para autenticar a los usuarios en lugar del campo username predeterminado. Esto significa que los usuarios iniciarán sesión utilizando su dirección de correo electrónico en lugar de un nombre de usuario tradicional.
    class Meta:
        managed = True
        db_table = 'usuarios'


class UserRole(models.Model):
    id = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Roles, models.DO_NOTHING, db_column='id_rol')
    id_user = models.ForeignKey(Usuarios, models.DO_NOTHING, db_column='id_user')
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_role'
        unique_together = (('id_rol', 'id_user'),)

from django.contrib.auth.models import AbstractUser
from django.db import models

# Como usamos AbstractUser, no necesitamos definir username, password y otros 
class Usuario(AbstractUser):
    # email único obligatorio
    email = models.EmailField(unique=True)

    # Diferenciar roles (propietario, comprador, admin, etc.)
    is_propietario = models.BooleanField(default=False)
    is_comprador = models.BooleanField(default=True)
    # Datos adicionales que quieras mostrar en perfil/contacto
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({'Propietario' if self.is_propietario else 'Comprador'})"

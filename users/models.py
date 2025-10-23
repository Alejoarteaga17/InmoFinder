from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    # email único obligatorio
    email = models.EmailField(unique=True)

    # Diferenciar roles (propietario, comprador, admin, etc.)
    is_admin = models.BooleanField(default=False)
    is_propietario = models.BooleanField(default=False)
    is_comprador = models.BooleanField(default=True)
    
    # Datos adicionales
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Campos adicionales útiles
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    USERNAME_FIELD = 'email'  # Usar email como campo de login
    REQUIRED_FIELDS = ['username']  # Campos requeridos además del USERNAME_FIELD

    def save(self, *args, **kwargs):
        # Si el usuario es admin, también debe ser staff y superuser
        if self.is_admin:
            self.is_staff = True
            self.is_superuser = True
        else:
            self.is_superuser = False
        # Mantener staff si es admin
        self.is_staff = bool(self.is_admin)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({'Admin' if self.is_admin else 'Propietario' if self.is_propietario else 'Comprador'})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def role(self):
        if self.is_admin:
            return "Admin"
        elif self.is_propietario:
            return "Propietario"
        else:
            return "Comprador"

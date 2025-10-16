from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.conf import settings


User = get_user_model()

class Propiedad(models.Model):
    # Relación con el propietario (owner)
    owner = models.ForeignKey(User, related_name='propiedades', on_delete=models.CASCADE, null=True, blank=True)

    # Información general
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255)
    property_type = models.CharField(max_length=50, choices=[
        ('Apartamento', 'Apartamento'),
        ('Casa', 'Casa'),
        ('Lote', 'Lote'),
        ('Oficina', 'Oficina'),
        ('Otro', 'Otro'),
    ])
    condition = models.CharField(max_length=100, blank=True, null=True)
    seller = models.CharField(max_length=255, blank=True, null=True)
    listing_url = models.URLField(blank=True, null=True)

    # Características físicas
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    area_privada_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    rooms = models.IntegerField()
    bathrooms = models.IntegerField()
    parking_spaces = models.IntegerField()
    floor = models.IntegerField()
    estrato = models.IntegerField(blank=True, null=True)

    # Estado y adicionales
    antiguedad = models.CharField(max_length=50, blank=True, null=True)
    cantidad_de_pisos = models.IntegerField(blank=True, null=True)
    codigo_fincaraiz = models.CharField(max_length=50, blank=True, null=True)

    # Amenidades
    amenities = models.JSONField(blank=True, null=True)

    # Precio y administración
    price_cop = models.BigIntegerField()
    admin_fee_cop = models.BigIntegerField(blank=True, null=True)

    # Características adicionales
    pets_allowed = models.BooleanField(default=False)
    furnished = models.BooleanField(default=False)

    # Fechas
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.location}"


class MediaPropiedad(models.Model):
    propiedad = models.ForeignKey(Propiedad, related_name='media', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='propiedades/', blank=True, null=True)
    tipo = models.CharField(max_length=10, choices=[('imagen', 'Imagen'), ('video', 'Video')], blank=True)
    url = models.URLField(blank=True, null=True)  # Para almacenar links de imágenes externas (como los del JSON)

    def save(self, *args, **kwargs):
        # Detecta el tipo automáticamente si no se pasa
        if not self.tipo and self.url:
            if any(self.url.lower().endswith(ext) for ext in ['.mp4', '.mov', '.avi']):
                self.tipo = 'video'
            else:
                self.tipo = 'imagen'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Media de {self.propiedad.title} ({self.tipo})"

class ContactMessage(models.Model):
    propiedad = models.ForeignKey(
        'Propiedad',
        related_name='contact_messages',
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='contact_messages',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True, null=True)  # ✅ agregado (útil para contacto)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)  # ✅ agregado (para marcar mensajes leídos)

    def __str__(self):
        # ✅ corregido: 'propiedad.nombre' no existe, debe ser 'propiedad.title'
        return f"Mensaje de {self.nombre} sobre {self.propiedad.title}"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE, related_name='favoritos')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'propiedad')

    def __str__(self):
        return f"{self.user.username} ❤️ {self.propiedad.title}"
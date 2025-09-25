# propiedades/models.py
from decimal import Decimal
from pathlib import Path
from django.db import models
from django.conf import settings

TIPO_PROPIEDAD_CHOICES = [
    ('Piso', 'Piso'),
    ('Casa', 'Casa'),
    ('Chalet', 'Chalet'),
    ('Ático', 'Ático'),
    ('Dúplex', 'Dúplex'),
    ('Estudio', 'Estudio'),
    ('Loft', 'Loft'),
    ('Finca', 'Finca'),
]

class Propiedad(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="propiedades",
        on_delete=models.CASCADE
    )
    nombre = models.CharField(max_length=200, default="")
    descripcion = models.TextField(default="")
    precio_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    precio_m2 = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    habitaciones = models.PositiveIntegerField(default=1)
    banos = models.PositiveIntegerField(default=1)
    parqueaderos = models.PositiveIntegerField(default=0)
    area = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    ubicacion = models.CharField(max_length=200, default="")
    tipo = models.CharField(max_length=20, choices=TIPO_PROPIEDAD_CHOICES, default='Piso')
    zonas_comunes = models.TextField(blank=True, null=True)
    fecha_disponibilidad = models.DateField(auto_now_add=False, blank=True, null=True)
    garaje = models.BooleanField(default=False)
    mascotas = models.BooleanField(default=False)
    estrato = models.PositiveIntegerField(blank=True, null=True)
    construccion_ano = models.PositiveIntegerField(blank=True, null=True)
    piso = models.PositiveIntegerField(blank=True, null=True)
    ascensor = models.BooleanField(default=False)



    class Meta:
        indexes = [
            models.Index(fields=['precio_total']),
            models.Index(fields=['area']),
            models.Index(fields=['ubicacion']),
            models.Index(fields=['tipo']),
        ]

    def save(self, *args, **kwargs):
        if self.area and self.area > 0 and self.precio_total is not None:
            self.precio_m2 = (self.precio_total / self.area).quantize(Decimal('1.00'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} - {self.ubicacion}"


class MediaPropiedad(models.Model):
    propiedad = models.ForeignKey(Propiedad, related_name='media', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='propiedades/', blank=True, null=True)
    tipo = models.CharField(max_length=10, choices=[('imagen', 'Imagen'), ('video', 'Video')], blank=True)

    def save(self, *args, **kwargs):
        if not self.tipo and self.archivo:
            ext = Path(self.archivo.name).suffix.lower()
            self.tipo = 'video' if ext in {'.mp4', '.webm', '.ogg'} else 'imagen'
        super().save(*args, **kwargs)

    @property
    def es_video(self):
        return self.tipo == 'video'

    def __str__(self):
        t = 'Video' if self.es_video else 'Imagen'
        return f"{t} de {self.propiedad.nombre}"

class ContactMessage(models.Model):
    propiedad = models.ForeignKey(Propiedad, related_name='contact_messages', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='contact_messages', on_delete=models.SET_NULL, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mensaje de {self.nombre} sobre {self.propiedad.nombre}"

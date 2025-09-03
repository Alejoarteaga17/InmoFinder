import datetime
from decimal import Decimal
from django.db import models

class Propiedad(models.Model):
    nombre = models.CharField(max_length=200, default="")
    descripcion = models.TextField(default="")
    precio_total = models.DecimalField(max_digits=12, decimal_places=2,default=Decimal('0.00'))
    precio_m2 = models.DecimalField(max_digits=10, decimal_places=2,default=Decimal('0.00'))
    habitaciones = models.IntegerField(default=1)
    bannos = models.IntegerField(default=1)
    parqueaderos = models.IntegerField(default=0)
    area = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))  # m²
    ubicacion = models.CharField(max_length=200, default="")
    tipo = models.CharField(
        max_length=50,
        choices=[
            ('Piso', 'Piso'),
            ('Casa', 'Casa'),
            ('Chalet', 'Chalet'),
            ('Ático', 'Ático'),
            ('Dúplex', 'Dúplex'),
            ('Estudio', 'Estudio'),
            ('Loft', 'Loft'),
        ],default='Piso'
    )
    zonas_comunes = models.TextField(blank=True, null=True)  # piscina, gym, etc.
    fecha_disponibilidad = models.DateField(default=datetime.date.today)
    garaje = models.BooleanField(default=False)
    mascotas = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} - {self.ubicacion}"


class MediaPropiedad(models.Model):
    propiedad = models.ForeignKey(Propiedad, related_name="media", on_delete=models.CASCADE)
    archivo = models.FileField(upload_to="propiedades/")
    tipo = models.CharField(
        max_length=10,
        choices=[
            ('imagen', 'Imagen'),
            ('video', 'Video'),
        ]
    )

    def __str__(self):
        return f"{self.tipo} de {self.propiedad.nombre}"

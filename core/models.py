from django.db import models

class Propiedad(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    direccion = models.CharField(max_length=255)
    imagen = models.ImageField(upload_to='propiedades/', blank=True, null=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

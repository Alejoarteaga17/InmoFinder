from django.shortcuts import render, get_object_or_404
from .models import Propiedad

def home(request):
    propiedades = Propiedad.objects.all()
    return render(request, 'home.html', {'propiedades': propiedades})

def detalle_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    # Si 'imagen' es un ImageField, solo hay una imagen
    imagenes = [propiedad.imagen] if propiedad.imagen else []
    return render(request, 'detalle_propiedad.html', {
        'propiedad': propiedad,
        'imagenes': imagenes
    })

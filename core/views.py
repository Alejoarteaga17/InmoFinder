from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from core.models import Propiedad
    
# Create your views here.
def home(request):
    return render(request, 'home.html')

def lista_propiedades(request):
    propiedades = Propiedad.objects.all()
    return render(request, 'propiedades.html', {'propiedades': propiedades})

def detalle_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    imagenes = propiedad.imagen  # Todas las imágenes extra
    return render(request, 'detalle_propiedad.html', {
        'propiedad': propiedad,
        'imagenes': imagenes
    })
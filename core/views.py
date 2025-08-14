from django.shortcuts import render
from django.http import HttpResponse
from core.models import Propiedad
    
# Create your views here.
def home(request):
    return render(request, 'home.html')

def lista_propiedades(request):
    propiedades = Propiedad.objects.all()
    return render(request, 'propiedades.html', {'propiedades': propiedades})
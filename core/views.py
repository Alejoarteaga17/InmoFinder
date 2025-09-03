from django.shortcuts import render, get_object_or_404
from .models import Propiedad, MediaPropiedad
from django.db.models import Q


def home(request):
    """
    Lista todas las propiedades disponibles
    """
    propiedades = Propiedad.objects.all().prefetch_related("media")
    return render(request, "home.html", {"propiedades": propiedades})


def detalle_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    media = propiedad.media.all()  # type: ignore # usa el related_name
    return render(request, "detalle_propiedad.html", {"propiedad": propiedad, "media": media})

def buscar_propiedades(request):
    propiedades = Propiedad.objects.all()

    # --- Búsqueda por texto libre ---
    query = request.GET.get("q")
    if query:
        propiedades = propiedades.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(ubicacion__icontains=query)
        )

    # --- Filtros ---
    precio_min = request.GET.get("precio_min")
    precio_max = request.GET.get("precio_max")
    if precio_min:
        propiedades = propiedades.filter(precio_total__gte=precio_min)
    if precio_max:
        propiedades = propiedades.filter(precio_total__lte=precio_max)

    habitaciones = request.GET.get("habitaciones")
    if habitaciones:
        propiedades = propiedades.filter(habitaciones=habitaciones)

    banos = request.GET.get("banos")
    if banos:
        propiedades = propiedades.filter(banos=banos)

    parqueaderos = request.GET.get("parqueaderos")
    if parqueaderos:
        propiedades = propiedades.filter(parqueaderos=parqueaderos)

    tipo = request.GET.get("tipo")
    if tipo:
        propiedades = propiedades.filter(tipo=tipo)

    area_min = request.GET.get("area_min")
    area_max = request.GET.get("area_max")
    if area_min:
        propiedades = propiedades.filter(area__gte=area_min)
    if area_max:
        propiedades = propiedades.filter(area__lte=area_max)

    disponibilidad = request.GET.get("disponibilidad")
    if disponibilidad:
        propiedades = propiedades.filter(fecha_disponibilidad__lte=disponibilidad)

    garaje = request.GET.get("garaje")
    if garaje == "1":
        propiedades = propiedades.filter(garaje=True)

    mascotas = request.GET.get("mascotas")
    if mascotas == "1":
        propiedades = propiedades.filter(mascotas=True)

    return render(request, "buscar.html", {"propiedades": propiedades})
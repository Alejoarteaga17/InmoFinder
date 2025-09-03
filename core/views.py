from django.shortcuts import render, get_object_or_404
from .models import Propiedad, MediaPropiedad


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

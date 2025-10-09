from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from .models import Propiedad, MediaPropiedad
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .forms import ContactForm
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST


def home(request):
    # show latest properties (use created_at as fallback)
    qs = Propiedad.objects.all().order_by('-created_at')[:12]
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.exclude(archivo__isnull=True).exclude(archivo="").order_by('id'))
    qs = qs.prefetch_related(media_prefetch)
    return render(request, "properties/home.html", {"propiedades": qs})


def buscar_propiedades(request):
    propiedades = Propiedad.objects.all()

    # Texto libre (map to new fields)
    search = request.GET.get("search")
    if search:
        propiedades = propiedades.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(location__icontains=search)
        )

    # Filtros numéricos (map names)
    precio_min = request.GET.get("precio_min")
    precio_max = request.GET.get("precio_max")
    if precio_min:
        propiedades = propiedades.filter(price_cop__gte=precio_min)
    if precio_max:
        propiedades = propiedades.filter(price_cop__lte=precio_max)

    habitaciones = request.GET.get("habitaciones")
    if habitaciones:
        propiedades = propiedades.filter(rooms=habitaciones)

    banos = request.GET.get("banos")
    if banos:
        propiedades = propiedades.filter(bathrooms=banos)

    parqueaderos = request.GET.get("parqueaderos")
    if parqueaderos:
        propiedades = propiedades.filter(parking_spaces=parqueaderos)

    area_min = request.GET.get("area_min")
    area_max = request.GET.get("area_max")
    if area_min:
        propiedades = propiedades.filter(area_m2__gte=area_min)
    if area_max:
        propiedades = propiedades.filter(area_m2__lte=area_max)

    tipo = request.GET.get("tipo")
    if tipo:
        propiedades = propiedades.filter(property_type=tipo)

    if request.GET.get("garaje") == "1":
        propiedades = propiedades.filter(parking_spaces__gt=0)
    if request.GET.get("mascotas") == "1":
        propiedades = propiedades.filter(pets_allowed=True)

    # Orden
    orden = request.GET.get("orden")
    mapping = {
        "precio_asc": "price_cop",
        "precio_desc": "-price_cop",
        "area_asc": "area_m2",
        "area_desc": "-area_m2",
        "recientes": "-created_at",
    }
    if orden in mapping:
        propiedades = propiedades.order_by(mapping[orden])

    # Prefetch media + paginación
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.exclude(archivo__isnull=True).exclude(archivo="").order_by('id'))
    propiedades = propiedades.prefetch_related(media_prefetch)

    paginator = Paginator(propiedades, 12)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    return render(request, "properties/buscar.html", {"propiedades": page_obj})


def detalle_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    # If requested as modal, render the partial used by AJAX
    if request.GET.get("modal") == "1":
        return render(request, "properties/partials/propiedad_modal.html", {"propiedad": propiedad})
    return render(request, "properties/detalle_propiedad.html", {"propiedad": propiedad})


@login_required
def contact_form(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    form = ContactForm(user=request.user)
    return render(request, "properties/partials/contact_form.html", {"form": form, "propiedad": propiedad})



@login_required
@require_POST
def contact_owner(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    form = ContactForm(request.POST, user=request.user)

    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "errors": form.errors
            })
        messages.error(request, "Please correct the errors in the form.")
        return redirect("detalle_propiedad", propiedad_id=propiedad_id)

    # Guardar mensaje
    cm = form.save(commit=False)
    cm.propiedad = propiedad
    cm.user = request.user
    cm.save()

    # Enviar email
    owner = propiedad.owner
    if owner and owner.email:
        subject = f"New message about your property «{propiedad.title}»"
        context = {
            "propiedad": propiedad,
            "message": cm.mensaje,
            "sender_name": cm.nombre,
            "sender_email": cm.email,
            "site": request.get_host(),
        }
        body_html = render_to_string("properties/partials/contact_owner.html", context)
        email = EmailMessage(subject, body_html, to=[owner.email])
        email.content_subtype = "html"
        try:
            email.send()
        except Exception:
            pass

    # Responder según tipo de request
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "success": True,
            "message": "Your message has been sent to the owner."
        })

    messages.success(request, "Your message has been sent to the owner.")
    return redirect("home")
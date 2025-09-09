from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from .models import Propiedad, MediaPropiedad
from django.contrib.auth import login, logout
from django.views.generic.edit import FormView
from django.contrib.auth.views import LoginView as AuthLoginView
from .forms import RegisterForm, LoginForm

def home(request):
    qs = Propiedad.objects.all().order_by('-fecha_disponibilidad')[:12]
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.exclude(archivo__isnull=True).exclude(archivo="").order_by('id'))
    qs = qs.prefetch_related(media_prefetch)
    return render(request, "home.html", {"propiedades": qs})

class LoginView(AuthLoginView):
    template_name = "auth/login.html"
    authentication_form = LoginForm

def logout_view(request):
    logout(request)
    return redirect("home")

class RegisterView(FormView):
    template_name = "auth/register.html"
    form_class = RegisterForm

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect("home")

def buscar_propiedades(request):
    propiedades = Propiedad.objects.all()

    # Texto libre
    search = request.GET.get("search")
    if search:
        propiedades = propiedades.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(ubicacion__icontains=search)
        )

    # Filtros numéricos
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

    area_min = request.GET.get("area_min")
    area_max = request.GET.get("area_max")
    if area_min:
        propiedades = propiedades.filter(area__gte=area_min)
    if area_max:
        propiedades = propiedades.filter(area__lte=area_max)

    tipo = request.GET.get("tipo")
    if tipo:
        propiedades = propiedades.filter(tipo=tipo)

    if request.GET.get("garaje") == "1":
        propiedades = propiedades.filter(garaje=True)
    if request.GET.get("mascotas") == "1":
        propiedades = propiedades.filter(mascotas=True)

    # Orden
    orden = request.GET.get("orden")
    mapping = {
        "precio_asc": "precio_total",
        "precio_desc": "-precio_total",
        "area_asc": "area",
        "area_desc": "-area",
        "recientes": "-fecha_disponibilidad",
    }
    if orden in mapping:
        propiedades = propiedades.order_by(mapping[orden])

    # Prefetch media + paginación
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.exclude(archivo__isnull=True).exclude(archivo="").order_by('id'))
    propiedades = propiedades.prefetch_related(media_prefetch)

    paginator = Paginator(propiedades, 12)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    return render(request, "buscar.html", {"propiedades": page_obj})

def detalle_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad.objects.prefetch_related('media'), pk=propiedad_id)
    media_validas = [m for m in propiedad.media.all() if m.archivo]  # type: ignore
    return render(request, "detalle_propiedad.html", {"propiedad": propiedad, "media_validas": media_validas})

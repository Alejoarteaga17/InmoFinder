from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from .models import Propiedad, MediaPropiedad
from django.contrib.auth import login, logout
from django.views.generic.edit import FormView
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from .forms import ContactForm
from django.http import JsonResponse
from django.core.mail import send_mail


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
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    if request.GET.get("modal") == "1":
        return render(request, "partials/propiedad_modal.html", {"propiedad": propiedad})
    return render(request, "detalle_propiedad.html", {"propiedad": propiedad})

@login_required
def contact_owner(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            # Aquí pondrás la lógica de guardar/enviar correo
            '''if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "message": "Mensaje enviado correctamente"
                })'''
            messages.success(request, "✅ Your message has been sent!")
            return redirect("home")   # 👈 si no es AJAX, redirige al home
        else:
            '''if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "errors": form.errors}, status=400)'''
            messages.error(request, "❌ Please correct the errors below.")
            return redirect("detalle_propiedad", propiedad_id=propiedad_id)

    return redirect("home")


# 🚨 Nueva vista: solo devuelve el formulario en HTML
@login_required
def contact_form(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)

    if request.method == "POST":
        form = ContactForm(request.POST, user=request.user)
        if form.is_valid():
            contacto = form.save(commit=False)
            contacto.propiedad = propiedad
            contacto.user = request.user
            contacto.save()

            # enviar correo al dueño
            #send_mail(
            #    subject=f"New message about your property {propiedad.nombre}",
            #    message=f"""
            #    You received a new contact request.

            #    From: {contacto.nombre} ({contacto.email})
            #    Property: {propiedad.nombre}
            #    Message:
            #    {contacto.mensaje}
            #    """,
            #    from_email="noreply@inmofinder.com",
            #    recipient_list=[propiedad.owner.email],  # 👈 asegúrate que tu modelo tenga `owner`
            #    fail_silently=False,
            #)
            

            return JsonResponse({"success": True, "message": "✅ Your message has been sent!"})
    else:
        form = ContactForm(user=request.user)

    return render(request, "partials/contact_form.html", {"form": form, "propiedad": propiedad})
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from .models import Propiedad, MediaPropiedad
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .forms import ContactForm, PropiedadForm
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

def home(request):
    # show latest properties (use created_at as fallback)
    qs = Propiedad.objects.all().order_by('-created_at')[:12]
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.exclude(archivo__isnull=True).exclude(archivo=""))
    qs = qs.prefetch_related(media_prefetch)
    return render(request, "properties/home.html", {"propiedades": qs})

@login_required
def contact_form(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    form = ContactForm(user=request.user)
    return render(request, "properties/partials/contact_form.html", {"form": form, "propiedad": propiedad})


class PropietarioRequiredMixin(UserPassesTestMixin):
    """Restringe acceso solo a propietarios"""
    def test_func(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        # Si no hay request o user, denegar acceso
        if not user or not getattr(user, "is_authenticated", False):
            return False
        # Caso 1: si tienes campo is_propietario en tu modelo personalizado
        if hasattr(user, "is_propietario"):
            return bool(user.is_propietario)
        return user.groups.filter(name="Propietarios").exists()

class AdminRequiredMixin(UserPassesTestMixin):
    """Restringe acceso solo a administradores"""
    def test_func(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        # Si no hay request o user, denegar acceso
        if not user or not getattr(user, "is_authenticated", False):
            return False
        # Caso 1: si tienes campo is_admin en tu modelo personalizado
        if hasattr(user, "is_admin"):
            return bool(user.is_admin)
        return user.groups.filter(name="Administradores").exists()
    
# --- DASHBOARDS ---
class OwnerDashboardView(LoginRequiredMixin, PropietarioRequiredMixin, ListView):
    model = Propiedad
    template_name = "properties/owner_dashboard.html"
    context_object_name = "propiedades"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user).order_by("-id")


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Propiedad
    template_name = "properties/admin_dashboard.html"
    context_object_name = "propiedades"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("owner").order_by("-id")

class RoleSuccessUrlMixin:
    """Devuelve el success_url correcto según el rol del usuario."""
    def get_success_url(self):
        user = getattr(self.request, "user", None) # type: ignore
        if user and getattr(user, "is_admin", False):
            return reverse_lazy("admin_dashboard")
        if user and getattr(user, "is_propietario", False):
            return reverse_lazy("dashboard")
        return reverse_lazy("home")

class PropiedadCreateView(LoginRequiredMixin, PropietarioRequiredMixin, RoleSuccessUrlMixin, CreateView):
    model = Propiedad
    form_class = PropiedadForm
    template_name = "properties/add_property.html"

    def form_valid(self, form):
        # asignar propietario
        form.instance.owner = self.request.user
        response = super().form_valid(form)

        # procesar multimedia si el formulario lo permite
        can_attach = getattr(form, "can_enable_multimedia", lambda: False)()
        if can_attach:
            files = self.request.FILES.getlist("multimedia_files")
            obj = form.instance
            for f in files:
                try:
                    MediaPropiedad.objects.create(propiedad=obj, archivo=f)
                except Exception:
                    pass

        messages.success(self.request, "Propiedad creada correctamente")
        return response

# --- EDITAR PROPIEDAD ---
class PropiedadUpdateView(LoginRequiredMixin, PropietarioRequiredMixin, RoleSuccessUrlMixin, UpdateView):
    model = Propiedad
    form_class = PropiedadForm
    template_name = "properties/add_property.html"

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self.request.user, "is_admin", False):
            return qs
        return qs.filter(owner=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)

        can_attach = getattr(form, "can_enable_multimedia", lambda: False)()
        if can_attach:
            files = self.request.FILES.getlist("multimedia_files")
            obj = form.instance
            for f in files:
                try:
                    MediaPropiedad.objects.create(propiedad=obj, archivo=f)
                except Exception:
                    pass

        messages.success(self.request, "Propiedad actualizada correctamente")
        return response

# --- ELIMINAR PROPIEDAD ---
class PropiedadDeleteView(LoginRequiredMixin, PropietarioRequiredMixin, RoleSuccessUrlMixin, DeleteView):
    model = Propiedad
    template_name = "properties/delete_property.html"

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self.request.user, "is_admin", False):
            return qs
        return qs.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Propiedad eliminada correctamente")
        return super().delete(request, *args, **kwargs)

# --- DETALLE DE PROPIEDAD ---
def detalle_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    # If requested as modal, render the partial used by AJAX
    if request.GET.get("modal") == "1":
        return render(request, "properties/partials/propiedad_modal.html", {"propiedad": propiedad})
    return render(request, "properties/detalle_propiedad.html", {"propiedad": propiedad})

# --- VISTA: REDIRECCIÓN POR ROL (después de login) ---
@login_required
def role_redirect(request):
    user = request.user
    if getattr(user, "is_admin", False):
        return redirect(reverse_lazy("admin_dashboard"))
    if getattr(user, "is_propietario", False):
        return redirect(reverse_lazy("dashboard"))
    return redirect(reverse_lazy("home"))


# --- VISTA: LISTAR MEDIA DE UNA PROPIEDAD (link from templates) ---
@login_required
def media_list(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    medias = propiedad.media.all() if hasattr(propiedad, "media") else [] # type: ignore
    return render(request, "properties/media_list.html", {"propiedad": propiedad, "medias": medias})

# --- CONTACTO CON EL PROPIETARIO ---
@login_required
@require_POST
def contact_owner(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    form = ContactForm(request.POST, user=request.user)

    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors})
        messages.error(request, "Por favor corrige los errores del formulario.")
        return redirect("detalle_propiedad", propiedad_id=propiedad_id)

    contact = form.save(commit=False)
    contact.propiedad = propiedad
    contact.user = request.user
    contact.save()

    # Envío de email al propietario
    owner = propiedad.owner
    if owner and owner.email:
        subject = f"Nuevo mensaje sobre tu propiedad «{propiedad.title}»"
        context = {"propiedad": propiedad, "mensaje": contact.mensaje, "remitente": contact.nombre, "email": contact.email}
        body_html = render_to_string("properties/partials/contact_owner.html", context)
        email = EmailMessage(subject, body_html, to=[owner.email])
        email.content_subtype = "html"
        try:
            email.send()
        except Exception:
            pass

    messages.success(request, "📨 Tu mensaje fue enviado al propietario.")
    return redirect("home")


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


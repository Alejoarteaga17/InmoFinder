from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required

from .models import Propiedad, MediaPropiedad
from .forms import ContactForm, PropiedadForm

# ---------- Constants for media validation ----------
MAX_MB = 1000  # per-file limit; adjust easily
ALLOWED_CONTENT_PREFIXES = ("image/", "video/")  # allow images and videos


# ---------- Home ----------
def home(request):
    # show latest properties (use created_at as fallback)
    qs = Propiedad.objects.all().order_by('-created_at')[:12]
    # Prefetch only local files (exclude remote URLs) as requested
    media_prefetch = Prefetch(
        'media',
        queryset=MediaPropiedad.objects.exclude(archivo__isnull=True).exclude(archivo="").order_by('id')
    )
    qs = qs.prefetch_related(media_prefetch)
    return render(request, "properties/home.html", {"propiedades": qs})


# ---------- Contact (modal) ----------
@login_required
def contact_form(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    form = ContactForm(user=request.user)
    return render(request, "properties/partials/contact_form.html", {"form": form, "propiedad": propiedad})


# ---------- Mixins (roles) ----------
class PropietarioRequiredMixin(UserPassesTestMixin):
    """Restrict access to property owners."""
    def test_func(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if hasattr(user, "is_propietario"):
            return bool(user.is_propietario)
        return user.groups.filter(name="Propietarios").exists()


class AdminRequiredMixin(UserPassesTestMixin):
    """Restrict access to admins."""
    def test_func(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if hasattr(user, "is_admin"):
            return bool(user.is_admin)
        return user.groups.filter(name="Administradores").exists()


# ---------- Dashboards ----------
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
    """Return success_url based on user role."""
    def get_success_url(self):
        user = getattr(self.request, "user", None)  # type: ignore
        if user and getattr(user, "is_admin", False):
            return reverse_lazy("admin_dashboard")
        if user and getattr(user, "is_propietario", False):
            return reverse_lazy("dashboard")
        return reverse_lazy("home")


# ---------- Create / Update / Delete ----------
class PropiedadCreateView(LoginRequiredMixin, PropietarioRequiredMixin, RoleSuccessUrlMixin, CreateView):
    model = Propiedad
    form_class = PropiedadForm
    template_name = "properties/add_property.html"

    def form_valid(self, form):
        # assign owner
        form.instance.owner = self.request.user
        with transaction.atomic():
            response = super().form_valid(form)

            # handle media files only if form is valid
            if getattr(form, "can_enable_multimedia", lambda: False)():
                files = self.request.FILES.getlist("multimedia_files")
                created = 0
                for f in files:
                    # basic validations
                    if f.size and f.size > MAX_MB * 1024 * 1024:
                        messages.error(self.request, f"{f.name} exceeds {MAX_MB} MB.")
                        continue
                    ctype = (getattr(f, "content_type", "") or "")
                    if not any(ctype.startswith(p) for p in ALLOWED_CONTENT_PREFIXES):
                        messages.error(self.request, f"{f.name}: unsupported content type ({ctype}).")
                        continue

                    MediaPropiedad.objects.create(propiedad=self.object, archivo=f)  # type inferred in save()
                    created += 1

                if created:
                    messages.success(self.request, f"{created} media file(s) uploaded.")

        messages.success(self.request, "Property created successfully.")
        return response


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
        with transaction.atomic():
            response = super().form_valid(form)

            if getattr(form, "can_enable_multimedia", lambda: False)():
                files = self.request.FILES.getlist("multimedia_files")
                created = 0
                for f in files:
                    if f.size and f.size > MAX_MB * 1024 * 1024:
                        messages.error(self.request, f"{f.name} exceeds {MAX_MB} MB.")
                        continue
                    ctype = (getattr(f, "content_type", "") or "")
                    if not any(ctype.startswith(p) for p in ALLOWED_CONTENT_PREFIXES):
                        messages.error(self.request, f"{f.name}: unsupported content type ({ctype}).")
                        continue

                    MediaPropiedad.objects.create(propiedad=self.object, archivo=f)
                    created += 1

                if created:
                    messages.success(self.request, f"{created} media file(s) uploaded.")

        messages.success(self.request, "Property updated successfully.")
        return response


class PropiedadDeleteView(LoginRequiredMixin, PropietarioRequiredMixin, RoleSuccessUrlMixin, DeleteView):
    model = Propiedad
    template_name = "properties/delete_property.html"

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self.request.user, "is_admin", False):
            return qs
        return qs.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Property deleted successfully.")
        return super().delete(request, *args, **kwargs)


# ---------- Property detail ----------
def detalle_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    # If requested as modal, render the partial used by AJAX
    if request.GET.get("modal") == "1":
        return render(request, "properties/partials/propiedad_modal.html", {"propiedad": propiedad})
    # The template can iterate propiedad.media.all to show gallery
    return render(request, "properties/detalle_propiedad.html", {"propiedad": propiedad})


# ---------- Role-based redirect after login ----------
@login_required
def role_redirect(request):
    user = request.user
    if getattr(user, "is_admin", False):
        return redirect(reverse_lazy("admin_dashboard"))
    if getattr(user, "is_propietario", False):
        return redirect(reverse_lazy("dashboard"))
    return redirect(reverse_lazy("home"))


# ---------- Media management (list + upload + delete) ----------
def _ensure_owner_or_admin(request, propiedad):
    """Raise 403 if the user is not the owner nor an admin."""
    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied("DEFAULT")
    if getattr(user, "is_admin", False):
        return
    if propiedad.owner_id != user.id:
        raise PermissionDenied("OWNER_ONLY")


@login_required
@require_http_methods(["GET", "POST"])
def media_list(request, propiedad_id):
    """
    GET: list media + show upload form
    POST: upload multiple files
    Only owner or admin can access.
    """
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    _ensure_owner_or_admin(request, propiedad)

    if request.method == "POST":
        files = request.FILES.getlist("file") or request.FILES.getlist("multimedia_files")
        if not files:
            messages.info(request, "No files were provided.")
            return redirect("properties:media_list", propiedad_id=propiedad_id)

        created = 0
        with transaction.atomic():
            for f in files:
                if f.size and f.size > MAX_MB * 1024 * 1024:
                    messages.error(request, f"{f.name} exceeds {MAX_MB} MB.")
                    continue
                ctype = (getattr(f, "content_type", "") or "")
                if not any(ctype.startswith(p) for p in ALLOWED_CONTENT_PREFIXES):
                    messages.error(request, f"{f.name}: unsupported content type ({ctype}).")
                    continue
                MediaPropiedad.objects.create(propiedad=propiedad, archivo=f)  # tipo inferred
                created += 1

        if created:
            messages.success(request, f"{created} media file(s) uploaded.")
        return redirect("properties:media_list", propiedad_id=propiedad_id)

    # GET
    medias = propiedad.media.all() if hasattr(propiedad, "media") else []  # type: ignore
    return render(request, "properties/media_list.html", {"propiedad": propiedad, "medias": medias})


@login_required
@require_POST
def media_delete(request, propiedad_id, media_id):
    """
    Delete one media item.
    Only owner or admin can delete.
    """
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    _ensure_owner_or_admin(request, propiedad)

    media = get_object_or_404(MediaPropiedad, id=media_id, propiedad=propiedad)
    media.delete()
    messages.success(request, "Media file deleted.")
    return redirect("properties:media_list", propiedad_id=propiedad_id)


# ---------- Contact owner ----------
@login_required
@require_POST
def contact_owner(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    form = ContactForm(request.POST, user=request.user)

    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors})
        messages.error(request, "Please fix the form errors.")
        return redirect("detalle_propiedad", propiedad_id=propiedad_id)

    contact = form.save(commit=False)
    contact.propiedad = propiedad
    contact.user = request.user
    contact.save()

    # Send email to owner (best-effort)
    owner = propiedad.owner
    if owner and owner.email:
        from django.core.mail import EmailMessage
        from django.template.loader import render_to_string

        subject = f"New message about your property «{propiedad.title}»"
        context = {
            "propiedad": propiedad,
            "mensaje": contact.mensaje,
            "remitente": contact.nombre,
            "email": contact.email
        }
        body_html = render_to_string("properties/partials/contact_owner.html", context)
        email = EmailMessage(subject, body_html, to=[owner.email])
        email.content_subtype = "html"
        try:
            email.send()
        except Exception:
            pass

    messages.success(request, "Your message was sent to the owner.")
    return redirect("home")


# ---------- Search ----------
def buscar_propiedades(request):
    propiedades = Propiedad.objects.all()

    # free text search
    search = request.GET.get("search")
    if search:
        propiedades = propiedades.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(location__icontains=search)
        )

    # numeric filters
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

    # ordering
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

    # Prefetch only media with local files (no URLs), as requested
    media_prefetch = Prefetch(
        'media',
        queryset=MediaPropiedad.objects.exclude(archivo__isnull=True).exclude(archivo="").order_by('id')
    )
    propiedades = propiedades.prefetch_related(media_prefetch)

    paginator = Paginator(propiedades, 12)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    return render(request, "properties/buscar.html", {"propiedades": page_obj})

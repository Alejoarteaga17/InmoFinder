from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch, Case, When, IntegerField
from .models import Propiedad, MediaPropiedad
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .forms import ContactForm, PropiedadForm
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
import logging
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from .models import Favorite, Propiedad
try:
    # Importar la búsqueda por embeddings (carga el modelo una sola vez por proceso)
    from properties.management.commands.embeddings import buscar_propiedades as emb_buscar
except Exception:
    emb_buscar = None  # fallback si no está disponible


def home(request):
    # show latest properties (use created_at as fallback)
    qs = Propiedad.objects.all().order_by('-created_at')[:12]
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.all())
    qs = qs.prefetch_related(media_prefetch)
    # Agregar atributo portada a cada propiedad
    for propiedad in qs:
        portada = None
        for media in propiedad.media.all(): # type: ignore
            if media.archivo:
                portada = media.archivo.url
                break
            elif media.url:
                portada = media.url
                break
        propiedad.portada = portada # type: ignore
    
    # Obtener IDs de favoritos si el usuario está autenticado
    favorite_ids = []
    if request.user.is_authenticated:
        favorite_ids = list(Favorite.objects.filter(user=request.user).values_list('propiedad_id', flat=True))

    # -- Propiedades vistas recientemente (sesión) --
    recent_ids = request.session.get('recently_viewed', [])
    recent_props = []
    if recent_ids:
        # Tomar máximo 4, preservar orden
        top_ids = list(recent_ids)[:4]
        when_list = [When(id=pk, then=pos) for pos, pk in enumerate(top_ids)]
        recent_qs = (
            Propiedad.objects.filter(id__in=top_ids)
            .prefetch_related(media_prefetch)
            .order_by(Case(*when_list, output_field=IntegerField()))
        )
        # Agregar portada a cada propiedad reciente
        tmp = []
        for propiedad in recent_qs:
            portada = None
            for media in propiedad.media.all(): # type: ignore
                if media.archivo:
                    portada = media.archivo.url
                    break
                elif media.url:
                    portada = media.url
                    break
            propiedad.portada = portada # type: ignore
            tmp.append(propiedad)
        recent_props = tmp

    return render(request, "properties/home.html", {
        "propiedades": qs,
        "favorite_ids": favorite_ids,
        "recent_props": recent_props,
    })

@login_required
def contact_form(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    
    # Si la propiedad no tiene propietario, redirigir al home
    if not propiedad.owner:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'redirect': '/',
                'message': 'Esta propiedad no tiene propietario asignado.'
            })
        return redirect('home')
    
    form = ContactForm(user=request.user)
    return render(request, "properties/partials/contact_form.html", {"form": form, "propiedad": propiedad})


class PropietarioRequiredMixin(UserPassesTestMixin):
    """Restringe acceso solo a propietarios y admins"""
    def test_func(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        # Si no hay request o user, denegar acceso
        if not user or not getattr(user, "is_authenticated", False):
            return False
        # Permitir acceso a admins
        if hasattr(user, "is_admin") and bool(user.is_admin):
            return True
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
        
        try:
            response = super().form_valid(form)

            # procesar multimedia si el formulario lo permite
            can_attach = getattr(form, "can_enable_multimedia", lambda: False)()
            if can_attach:
                files = self.request.FILES.getlist("multimedia_files")
                obj = form.instance
                for f in files:
                    try:
                        MediaPropiedad.objects.create(propiedad=obj, archivo=f)
                    except Exception as e:
                        # Log error but don't fail the whole operation
                        print(f"Error creating media: {e}")

            messages.success(self.request, "Propiedad creada correctamente")
            return response
        except Exception as e:
            messages.error(self.request, f"Error al crear la propiedad: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        # Mostrar mensaje de error cuando el formulario no es válido
        messages.error(self.request, "Por favor, corrige los errores en el formulario.")
        return super().form_invalid(form)

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
    # Registrar en sesión como recientemente vista (LRU simple)
    try:
        rv = request.session.get('recently_viewed', [])
        # Normalizar a ints y deduplicar moviendo al frente
        rv = [int(x) for x in rv if x is not None]
        if propiedad.id in rv: # type: ignore
            rv.remove(propiedad.id) # type: ignore
        rv.insert(0, int(propiedad.id)) # type: ignore
        # Cap a 20
        request.session['recently_viewed'] = rv[:20]
        request.session.modified = True
    except Exception:
        pass
    # Siempre renderiza el mismo template (que ya está diseñado como modal)
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
            # Devolver mensaje legible además de los errores de campo para que
            # el frontend pueda mostrarlos fácilmente.
            return JsonResponse({
                "success": False,
                "message": "Por favor corrige los errores del formulario.",
                "errors": form.errors,
            }, status=400)
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
        # Build context keys expected by the email template
        context = {
            "propiedad": propiedad,
            "sender_name": contact.nombre,
            "sender_email": contact.email,
            "message": contact.mensaje,
            "site": request.get_host(),
        }
        body_html = render_to_string("properties/partials/contact_owner.html", context)
        # Use DEFAULT_FROM_EMAIL as From address (safer) and set reply-to to sender
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or None
        email = EmailMessage(subject, body_html, from_email, [owner.email], reply_to=[contact.email])
        # Intenta incluir el nombre y correo del remitente en la cabecera From
        # Nota: algunos proveedores SMTP pueden sobrescribir o rechazar headers From
        # que no coincidan con la cuenta usada para autenticar el envío.
        try:
            email.extra_headers = {'From': f'{contact.nombre} <{contact.email}>'}
        except Exception:
            # No crítico: continuar sin extra headers si algo falla
            pass
        email.content_subtype = "html"
        email_sent = True
        try:
            email.send()
        except Exception:
            email_sent = False
            # Log exception to the server console so we can debug SMTP/auth issues
            logging.exception("Error sending contact email for propiedad id %s", propiedad_id)

        # Responder apropiadamente según si la petición fue AJAX
        success_message = "📨 Tu mensaje fue enviado al propietario."
        messages.success(request, success_message)

        # If email wasn't sent, add a warning for regular requests and include a flag in AJAX
        if not email_sent:
            warning_msg = "⚠️ No se pudo enviar el email al propietario (problema con el servidor de correo)."
            # Mostrar advertencia en mensajes para solicitudes normales
            messages.warning(request, warning_msg)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": success_message, "email_sent": email_sent})

        return redirect("home")


def buscar_propiedades(request):
    propiedades = Propiedad.objects.all()

    # Texto libre: usar embeddings si hay consulta y el motor está disponible; si falla, usar icontains
    search = request.GET.get("search")
    ids_ranked = []
    used_embeddings = False
    if search:
        if emb_buscar is not None:
            try:
                # Obtener un conjunto razonable de candidatos para luego aplicar filtros
                results = emb_buscar(search, top_k=500)
                ids_ranked = [r.get("id") for r in results if r.get("id")]
                if ids_ranked:
                    propiedades = propiedades.filter(id__in=ids_ranked)
                    used_embeddings = True
            except Exception:
                # Fallback a búsqueda simple
                propiedades = propiedades.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(location__icontains=search)
                )
        else:
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

    habitaciones = request.GET.get("rooms")
    if habitaciones:
        propiedades = propiedades.filter(rooms=habitaciones)

    banos = request.GET.get("bathrooms")
    if banos:
        propiedades = propiedades.filter(bathrooms=banos)

    parqueaderos = request.GET.get("parking_spaces")
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

    # Orden: si usamos embeddings y no se especifica otro orden, preservamos ranking por similitud
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
    elif used_embeddings and ids_ranked:
        # Preservar el orden de ids_ranked
        when_list = [When(id=pk, then=pos) for pos, pk in enumerate(ids_ranked)]
        propiedades = propiedades.order_by(Case(*when_list, output_field=IntegerField()))

    # Prefetch media + paginación
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.all())
    propiedades = propiedades.prefetch_related(media_prefetch)

    paginator = Paginator(propiedades, 12)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)
    
    # Agregar atributo portada a cada propiedad en la página
    for propiedad in page_obj:
        portada = None
        for media in propiedad.media.all():
            if media.archivo:
                portada = media.archivo.url
                break
            elif media.url:
                portada = media.url
                break
        propiedad.portada = portada

    # Obtener IDs de favoritos si el usuario está autenticado
    favorite_ids = []
    if request.user.is_authenticated:
        favorite_ids = list(Favorite.objects.filter(user=request.user).values_list('propiedad_id', flat=True))

    # Build querystring without page for clean pagination links
    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    return render(request, "properties/buscar.html", {
        "propiedades": page_obj,
        "favorite_ids": favorite_ids,
        "querystring": querystring,
    })

@login_required
def toggle_favorite(request, propiedad_id):
    propiedad = Propiedad.objects.get(id=propiedad_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, propiedad=propiedad)

    if not created:
        favorite.delete()
        return JsonResponse({'status': 'removed'})
    else:
        return JsonResponse({'status': 'added'})

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch, Case, When, IntegerField
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST, require_http_methods
from django.urls import reverse_lazy, reverse
import logging
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse

from .forms import ContactForm, PropiedadForm
from .models import Favorite, Propiedad, MediaPropiedad

# Intentar importar búsqueda por embeddings
try:
    from properties.management.commands.embeddings import buscar_propiedades as emb_buscar
except Exception:
    emb_buscar = None  # fallback si no está disponible


# =========================
#  Constantes para MEDIA
# =========================

# Límite por archivo en MB (básico, ajustable)
MAX_MB = 1000
# Se permiten imágenes y videos (por prefijo de content-type)
ALLOWED_CONTENT_PREFIXES = ("image/", "video/")


# =========================
#  Home
# =========================
def home(request):
    """
    Renderiza las últimas propiedades y añade una 'portada' (primer media disponible).
    También expone favoritos del usuario y propiedades vistas recientemente.
    """
    qs = Propiedad.objects.all().order_by('-created_at')[:12]
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.all())
    qs = qs.prefetch_related(media_prefetch)

    # Agregar atributo portada a cada propiedad (primer archivo o url disponible)
    for propiedad in qs:
        portada = None
        for media in propiedad.media.all():  # type: ignore
            if getattr(media, "archivo", None):
                portada = media.archivo.url
                break
            elif getattr(media, "url", None):
                portada = media.url
                break
        propiedad.portada = portada  # type: ignore

    # IDs de favoritos
    favorite_ids = []
    if request.user.is_authenticated:
        favorite_ids = list(
            Favorite.objects.filter(user=request.user).values_list('propiedad_id', flat=True)
        )

    # Propiedades vistas recientemente (en sesión)
    recent_ids = request.session.get('recently_viewed', [])
    recent_props = []
    if recent_ids:
        top_ids = list(recent_ids)[:4]
        when_list = [When(id=pk, then=pos) for pos, pk in enumerate(top_ids)]
        recent_qs = (
            Propiedad.objects.filter(id__in=top_ids)
            .prefetch_related(media_prefetch)
            .order_by(Case(*when_list, output_field=IntegerField()))
        )
        tmp = []
        for propiedad in recent_qs:
            portada = None
            for media in propiedad.media.all():  # type: ignore
                if getattr(media, "archivo", None):
                    portada = media.archivo.url
                    break
                elif getattr(media, "url", None):
                    portada = media.url
                    break
            propiedad.portada = portada  # type: ignore
            tmp.append(propiedad)
        recent_props = tmp

    return render(request, "properties/home.html", {
        "propiedades": qs,
        "favorite_ids": favorite_ids,
        "recent_props": recent_props,
    })


# =========================
#  Contacto (modal)
# =========================
@login_required
def contact_form(request, propiedad_id):
    """
    Devuelve el formulario de contacto (partial) para una propiedad.
    Si la propiedad no tiene propietario, redirige al home o responde JSON en AJAX.
    """
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)

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


# =========================
#  Mixins de rol
# =========================
class PropietarioRequiredMixin(UserPassesTestMixin):
    """Permite acceso a propietarios o administradores."""
    def test_func(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if hasattr(user, "is_admin") and bool(user.is_admin):
            return True
        if hasattr(user, "is_propietario"):
            return bool(user.is_propietario)
        return user.groups.filter(name="Propietarios").exists()


class AdminRequiredMixin(UserPassesTestMixin):
    """Permite acceso solo a administradores."""
    def test_func(self):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if hasattr(user, "is_admin"):
            return bool(user.is_admin)
        return user.groups.filter(name="Administradores").exists()


# =========================
#  Dashboards
# =========================
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
        user = getattr(self.request, "user", None)  # type: ignore
        if user and getattr(user, "is_admin", False):
            return reverse_lazy("admin_dashboard")
        if user and getattr(user, "is_propietario", False):
            return reverse_lazy("dashboard")
        return reverse_lazy("home")


# =========================
#  Crear / Editar / Eliminar Propiedad
# =========================
class PropiedadCreateView(LoginRequiredMixin, PropietarioRequiredMixin, RoleSuccessUrlMixin, CreateView):
    """
    Crea una propiedad y, si corresponde, adjunta archivos multimedia.
    - Se usa transaction.atomic() para que la creación + adjuntos sea todo-o-nada.
    - Se validan tamaño y content-type de cada archivo.
    """
    model = Propiedad
    form_class = PropiedadForm
    template_name = "properties/add_property.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user

        try:
            with transaction.atomic():
                # Guardar propiedad
                response = super().form_valid(form)

                # Adjuntar multimedia (opcional según el form)
                can_attach = getattr(form, "can_enable_multimedia", lambda: False)()
                if can_attach:
                    files = self.request.FILES.getlist("multimedia_files")
                    created = 0
                    for f in files:
                        # Validaciones mínimas de media
                        if getattr(f, "size", None) and f.size > MAX_MB * 1024 * 1024:
                            messages.error(self.request, f"{f.name} excede {MAX_MB} MB.")
                            continue
                        ctype = (getattr(f, "content_type", "") or "")
                        if not any(ctype.startswith(p) for p in ALLOWED_CONTENT_PREFIXES):
                            messages.error(self.request, f"{f.name}: tipo no soportado ({ctype}).")
                            continue

                        MediaPropiedad.objects.create(propiedad=form.instance, archivo=f)
                        created += 1
                    if created:
                        messages.success(self.request, f"{created} archivo(s) subido(s).")

            messages.success(self.request, "Propiedad creada correctamente")
            return response
        except Exception as e:
            messages.error(self.request, f"Error al crear la propiedad: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Por favor, corrige los errores en el formulario.")
        return super().form_invalid(form)


class PropiedadUpdateView(LoginRequiredMixin, PropietarioRequiredMixin, RoleSuccessUrlMixin, UpdateView):
    """
    Actualiza una propiedad y adjunta nuevos archivos si aplica.
    Se usa transaction.atomic() para garantizar consistencia.
    """
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

            can_attach = getattr(form, "can_enable_multimedia", lambda: False)()
            if can_attach:
                files = self.request.FILES.getlist("multimedia_files")
                created = 0
                for f in files:
                    if getattr(f, "size", None) and f.size > MAX_MB * 1024 * 1024:
                        messages.error(self.request, f"{f.name} excede {MAX_MB} MB.")
                        continue
                    ctype = (getattr(f, "content_type", "") or "")
                    if not any(ctype.startswith(p) for p in ALLOWED_CONTENT_PREFIXES):
                        messages.error(self.request, f"{f.name}: tipo no soportado ({ctype}).")
                        continue
                    MediaPropiedad.objects.create(propiedad=form.instance, archivo=f)
                    created += 1
                if created:
                    messages.success(self.request, f"{created} archivo(s) subido(s).")

            messages.success(self.request, "Propiedad actualizada correctamente")

            # Enviar email al owner notificando que la propiedad fue actualizada
            try:
                owner = form.instance.owner
                # Sólo enviar si el propietario tiene email
                if owner and getattr(owner, 'email', None):
                    subject = f"Detalles actualizados: {form.instance.title or 'tu propiedad'}"
                    detail_url = self.request.build_absolute_uri(
                        reverse('detalle_propiedad', args=[form.instance.id])
                    )
                    context = {
                        'owner': owner,
                        'propiedad': form.instance,
                        'detail_url': detail_url,
                    }
                    body_html = render_to_string('properties/partials/property_updated_email.html', context)
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                    email = EmailMessage(subject, body_html, from_email, [owner.email], reply_to=[from_email] if from_email else None)
                    email.content_subtype = 'html'
                    try:
                        # En desarrollo puede imprimirse en consola según EMAIL_BACKEND
                        email.send()
                    except Exception:
                        logging.exception('Error sending property-updated email for propiedad id %s', form.instance.id)
            except Exception:
                # No queremos que un error en el envío impida la actualización
                logging.exception('Unexpected error while preparing property-updated email for propiedad id %s', form.instance.id)

            return response


class PropiedadDeleteView(LoginRequiredMixin, PropietarioRequiredMixin, RoleSuccessUrlMixin, DeleteView):
    """Elimina una propiedad (propietario o admin)."""
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


# =========================
#  Detalle de propiedad
# =========================
def detalle_propiedad(request, propiedad_id):
    """
    Muestra el detalle de una propiedad y registra su visita en sesión
    (lista LRU simple de IDs recientes).
    """
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    try:
        rv = request.session.get('recently_viewed', [])
        rv = [int(x) for x in rv if x is not None]
        if propiedad.id in rv:  # type: ignore
            rv.remove(propiedad.id)  # type: ignore
        rv.insert(0, int(propiedad.id))  # type: ignore
        request.session['recently_viewed'] = rv[:20]
        request.session.modified = True
    except Exception:
        pass
    return render(request, "properties/detalle_propiedad.html", {"propiedad": propiedad})


# =========================
#  Redirección por rol (post-login)
# =========================
@login_required
def role_redirect(request):
    """Redirige al dashboard correspondiente según el rol del usuario."""
    user = request.user
    if getattr(user, "is_admin", False):
        return redirect(reverse_lazy("admin_dashboard"))
    if getattr(user, "is_propietario", False):
        return redirect(reverse_lazy("dashboard"))
    return redirect(reverse_lazy("home"))


# =========================
#  Gestión de Media
# =========================
@login_required
@require_http_methods(["GET", "POST"])
def media_list(request, propiedad_id):
    """
    GET: lista los archivos multimedia de la propiedad (solo propietario/admin).
    POST: sube múltiples archivos (solo propietario/admin).
    - Valida tamaño (MAX_MB) y tipo (image/* o video/*).
    - En POST, se usa transaction.atomic() para subir todos-o-ninguno.
    """
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)

    if request.method == "POST":
        files = request.FILES.getlist("file") or request.FILES.getlist("multimedia_files")
        if not files:
            messages.info(request, "No se recibieron archivos.")
            return redirect("media_list", propiedad_id=propiedad_id)

        created = 0
        with transaction.atomic():
            for f in files:
                if getattr(f, "size", None) and f.size > MAX_MB * 1024 * 1024:
                    messages.error(request, f"{f.name} excede {MAX_MB} MB.")
                    continue
                ctype = (getattr(f, "content_type", "") or "")
                if not any(ctype.startswith(p) for p in ALLOWED_CONTENT_PREFIXES):
                    messages.error(request, f"{f.name}: tipo no soportado ({ctype}).")
                    continue
                MediaPropiedad.objects.create(propiedad=propiedad, archivo=f)
                created += 1

        if created:
            messages.success(request, f"{created} archivo(s) subido(s).")
        return redirect("media_list", propiedad_id=propiedad_id)

    # GET
    medias = propiedad.media.all() if hasattr(propiedad, "media") else []  # type: ignore
    return render(request, "properties/media_list.html", {"propiedad": propiedad, "medias": medias})


@login_required
@require_POST
def media_delete(request, propiedad_id, media_id):
    """
    Elimina un archivo multimedia de una propiedad (solo propietario/admin).
    Usa require_POST para evitar borrados por GET.
    """
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)

    media = get_object_or_404(MediaPropiedad, id=media_id, propiedad=propiedad)
    media.delete()
    messages.success(request, "Archivo eliminado.")
    return redirect("media_list", propiedad_id=propiedad_id)


# =========================
#  Contactar propietario (envío)
# =========================
@login_required
@require_POST
def contact_owner(request, propiedad_id):
    """
    Procesa el formulario de contacto y envía correo al propietario (best-effort).
    require_POST garantiza que solo se acepte método POST.
    """
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


# =========================
#  Búsqueda de propiedades
# =========================
def buscar_propiedades(request):
    """
    Búsqueda de propiedades con:
      - Texto libre (embeddings si está disponible; fallback a icontains).
      - Filtros numéricos/categóricos.
      - Ordenamiento estándar o preservando ranking de similitud.
      - Prefetch de media y paginación.
    """
    propiedades = Propiedad.objects.all()

    # Texto libre
    search = request.GET.get("search")
    ids_ranked = []
    used_embeddings = False
    if search:
        if emb_buscar is not None:
            try:
                results = emb_buscar(search, top_k=500)
                ids_ranked = [r.get("id") for r in results if r.get("id")]
                if ids_ranked:
                    propiedades = propiedades.filter(id__in=ids_ranked)
                    used_embeddings = True
            except Exception:
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

    # Filtros
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

    # Ordenamiento
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
        when_list = [When(id=pk, then=pos) for pos, pk in enumerate(ids_ranked)]
        propiedades = propiedades.order_by(Case(*when_list, output_field=IntegerField()))

    # Prefetch media + paginación
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.all())
    propiedades = propiedades.prefetch_related(media_prefetch)

    paginator = Paginator(propiedades, 12)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    # Atributo portada por propiedad en la página
    for propiedad in page_obj:
        portada = None
        for media in propiedad.media.all():
            if getattr(media, "archivo", None):
                portada = media.archivo.url
                break
            elif getattr(media, "url", None):
                portada = media.url
                break
        propiedad.portada = portada

    # IDs de favoritos del usuario
    favorite_ids = []
    if request.user.is_authenticated:
        favorite_ids = list(
            Favorite.objects.filter(user=request.user).values_list('propiedad_id', flat=True)
        )

    # Querystring sin 'page' para paginación limpia
    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    return render(request, "properties/buscar.html", {
        "propiedades": page_obj,
        "favorite_ids": favorite_ids,
        "querystring": querystring,
    })


# =========================
#  Favoritos (toggle)
# =========================
@login_required
def toggle_favorite(request, propiedad_id):
    """
    Alterna favorito para una propiedad del usuario autenticado.
    (No relacionado con media/transaction/require_http_methods, se mantiene tal cual.)
    """
    propiedad = Propiedad.objects.get(id=propiedad_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, propiedad=propiedad)

    if not created:
        favorite.delete()
        return JsonResponse({'status': 'removed'})
    else:
        return JsonResponse({'status': 'added'})

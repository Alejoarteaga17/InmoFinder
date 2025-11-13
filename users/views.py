from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm, UserUpdateForm
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView as AuthLoginView, PasswordChangeView
from django.shortcuts import redirect
from django.views.generic import FormView
from properties.models import Favorite
from django.contrib import messages
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.views import View
from django.contrib.auth import get_user_model
from .mixins import AdminRequiredMixin
from typing import Any

# Create your views here.

class LoginView(AuthLoginView):
    template_name = "users/login.html"
    authentication_form = LoginForm

    def get_success_url(self):
        # Si hay un parámetro next, respétalo solo si NO contiene '?modal=1'
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url and "?modal=1" not in next_url:
            return next_url
        return "/"  # Redirige al home si el next contiene ?modal=1 o no existe

def logout_view(request):
    logout(request)
    return redirect("home")

class RegisterView(FormView):
    template_name = "users/register.html"
    form_class = RegisterForm

    def form_valid(self, form):
        # Crear usuario pero desactivado hasta que confirme por email
        user = form.save(commit=False)
        user.is_active = False
        # Roles por defecto
        user.is_comprador = True
        user.is_propietario = False
        user.save()

        # Enviar correo de activación con token
        try:
            subject = "Confirma tu correo en InmoFinder"
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            confirm_path = reverse('confirm_email', args=[uid, token])
            confirm_url = self.request.build_absolute_uri(confirm_path)
            context = {
                'user': user,
                'site': self.request.get_host(),
                'confirm_url': confirm_url,
            }
            body_html = render_to_string('users/activation_email.html', context)
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            email = EmailMessage(subject, body_html, from_email, [user.email])
            email.content_subtype = 'html'
            email.send()
        except Exception:
            import logging; logging.exception('Error sending activation email to %s', getattr(user, 'email', None))

        # Informar al usuario que revise su correo
        # Redirigimos a home por simplicidad; se puede crear una página específica si se desea.
        messages.info(self.request, 'Hemos enviado un correo de confirmación. Revisa tu bandeja y sigue el enlace para activar tu cuenta.')
        return redirect('home')


def confirm_email(request, uidb64, token):
    """Confirma el correo del usuario usando uidb64 y token. Si es válido, activa la cuenta y hace login."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        # Auto-login tras activación
        try:
            login(request, user)
        except Exception:
            pass
        # Mostrar plantilla de activación completa
        return render(request, 'users/activation_complete.html', {'user': user})
    else:
        # Token inválido o usuario no encontrado
        return render(request, 'users/activation_invalid.html', status=400)

REASONS = {
    "ADMIN_ONLY":        "Esta sección es solo para usuarios con rol Admin.",
    "PROPIETARIO_ONLY":  "Esta sección es solo para usuarios con rol Propietario.",
    "COMPRADOR_ONLY":    "Esta sección es solo para usuarios con rol Comprador.",
    "OWNER_ONLY":        "No puedes operar sobre recursos que no te pertenecen.",
    "DEFAULT":           "No tienes permisos para acceder a esta página.",
}

def error_403(request, exception=None):
    raw = None
    if exception and getattr(exception, "args", None):
        raw = exception.args[0]  # el mensaje que lanzamos en PermissionDenied("CODIGO")

    # Asegura que la clave sea string y evita problemas de tipado
    key = raw or "DEFAULT"
    reason_human = REASONS.get(key, REASONS["DEFAULT"])  
    ctx = {
        "reason_code": key,
        "reason_human": reason_human,
        "path": request.path,
        "user": getattr(request, "user", None),
    }
    return render(request, "403.html", ctx, status=403)
    
@login_required
def profile(request):
    return render(request, "users/profile.html")   


@login_required
def edit_profile(request):
    """Permite al usuario autenticado editar su información básica."""
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, "users/edit_profile.html", {"form": form})

@login_required
def favorites_list(request):
    from django.db.models import Prefetch
    from properties.models import MediaPropiedad, Propiedad
    
    # Obtener IDs de favoritos primero
    favorite_ids = list(
        Favorite.objects.filter(user=request.user).values_list('propiedad_id', flat=True)
    )
    
    # Obtener las propiedades favoritas con sus medias
    propiedades = Propiedad.objects.filter(id__in=favorite_ids)
    media_prefetch = Prefetch('media', queryset=MediaPropiedad.objects.all())
    propiedades = propiedades.prefetch_related(media_prefetch)
    
    # Agregar atributo portada a cada propiedad (igual que en home)
    for propiedad in propiedades:
        portada = None
        for media in propiedad.media.all():  # type: ignore
            if media.archivo:
                portada = media.archivo.url
                break
            elif media.url:
                portada = media.url
                break
        propiedad.portada = portada  # type: ignore
    
    return render(request, 'users/favorites.html', {
        'propiedades': propiedades,
        'favorite_ids': favorite_ids
})

@login_required
def clear_favorites(request):
    """Remove all favorites for the current user"""
    if request.method == 'POST':
        Favorite.objects.filter(user=request.user).delete()
        messages.success(request, 'All favorites have been cleared successfully.')
    return redirect('favorites')


class ChangePasswordView(PasswordChangeView):
    template_name = "users/change_password.html"
    success_url = "/users/profile/"

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)


class UserControlView(AdminRequiredMixin, View):
    """
    Admin-only page to view all users and toggle their roles via checkboxes.
    Roles managed:
    - is_admin (also sets is_staff/is_superuser through model save)
    - is_propietario
    - is_comprador

    Safeguards:
    - Prevent demoting self from admin within this page to avoid lockout.
    - Ensure at least one role is True; if none selected, default to comprador.
    """

    template_name = "users/user_control.html"

    def get(self, request):
        User = get_user_model()
        users = User.objects.all().order_by("id")
        return render(request, self.template_name, {"users": users})

    def post(self, request):
        User = get_user_model()
        user_ids = request.POST.getlist("user_ids")
        updated = 0
        warnings = 0
        for uid in user_ids:
            try:
                u = User.objects.get(pk=uid)
            except User.DoesNotExist:
                continue

            # Read checkbox values; presence means True
            want_admin = request.POST.get(f"is_admin_{u.pk}") == "on"
            want_prop = request.POST.get(f"is_propietario_{u.pk}") == "on"
            want_comp = request.POST.get(f"is_comprador_{u.pk}") == "on"

            # prevent removing own admin
            if u.pk == request.user.pk and not want_admin and getattr(u, "is_admin", False):
                warnings += 1
                want_admin = True  # keep admin

            # at least one role
            if not (want_admin or want_prop or want_comp):
                want_comp = True

            cur_admin = bool(getattr(u, "is_admin", False))
            cur_prop = bool(getattr(u, "is_propietario", False))
            cur_comp = bool(getattr(u, "is_comprador", False))
            changed = (cur_admin != want_admin) or (cur_prop != want_prop) or (cur_comp != want_comp)
            if changed:
                setattr(u, "is_admin", want_admin)
                setattr(u, "is_propietario", want_prop)
                setattr(u, "is_comprador", want_comp)
                u.save()
                updated += 1

        if updated:
            messages.success(request, f"Updated roles for {updated} user(s).")
        if warnings:
            messages.warning(request, "You cannot remove your own admin role via this page; change ignored for your account.")
        return redirect("user_control")

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm, UserUpdateForm
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView as AuthLoginView, PasswordChangeView
from django.shortcuts import redirect
from django.views.generic import FormView
from properties.models import Favorite
from django.contrib import messages

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
        # Crear usuario
        user = form.save()
        # Autenticar y hacer login con las credenciales recién creadas
        from django.contrib.auth import authenticate
        email = form.cleaned_data.get("email")
        password = form.cleaned_data.get("password1")
        user_auth = authenticate(self.request, username=email, password=password)
        if user_auth is not None:
            login(self.request, user_auth)
        else:
            # Fallback en caso de que el backend no acepte authenticate con email directamente
            try:
                login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
            except Exception:
                pass
        return redirect("home")

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


class ChangePasswordView(PasswordChangeView):
    template_name = "users/change_password.html"
    success_url = "/users/profile/"

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)

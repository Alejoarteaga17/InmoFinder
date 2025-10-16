from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView as AuthLoginView
from django.shortcuts import redirect
from django.views.generic import FormView
from properties.models import Favorite

# Create your views here.

class LoginView(AuthLoginView):
    template_name = "users/login.html"
    authentication_form = LoginForm

def get_success_url(self):
        # Si hay un parámetro next, respétalo (incluyendo ?modal=1)
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url:
            return next_url
        return super().get_success_url()

def logout_view(request):
    logout(request)
    return redirect("home")

class RegisterView(FormView):
    template_name = "users/register.html"
    form_class = RegisterForm

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
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
    reason_human = REASONS.get(raw, REASONS["DEFAULT"])
    ctx = {
        "reason_code": raw or "DEFAULT",
        "reason_human": reason_human,
        "path": request.path,
        "user": getattr(request, "user", None),
    }
    return render(request, "403.html", ctx, status=403)
    
@login_required
def profile(request):
    return render(request, "users/profile.html")   

@login_required
def favorites_list(request):
    from django.db.models import Prefetch
    from properties.models import MediaPropiedad
    
    # Prefetch solo las medias con archivo válido
    media_prefetch = Prefetch(
        'propiedad__media',
        queryset=MediaPropiedad.objects.exclude(archivo__isnull=True).exclude(archivo="")
    )
    favorites = Favorite.objects.filter(user=request.user).select_related('propiedad').prefetch_related(media_prefetch)
    
    # Obtener IDs de favoritos para marcarlos en las cards
    favorite_ids = list(favorites.values_list('propiedad_id', flat=True))
    
    return render(request, 'users/favorites.html', {
        'favorites': favorites,
        'favorite_ids': favorite_ids
})

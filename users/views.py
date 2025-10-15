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
    
@login_required
def profile(request):
    return render(request, "users/profile.html")   

@login_required
def favorites_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('propiedad')
    return render(request, 'users/favorites.html', {'favorites': favorites})
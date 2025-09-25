from django.shortcuts import render
from .forms import RegisterForm, LoginForm
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView as AuthLoginView
from django.shortcuts import redirect
from django.views.generic import FormView

# Create your views here.

class LoginView(AuthLoginView):
    template_name = "users/login.html"
    authentication_form = LoginForm

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

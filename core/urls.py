from django.urls import path
from core import views

urlpatterns = [
    path("", views.home, name="home"),
    path("buscar/", views.buscar_propiedades, name="buscar_propiedades"),
    path("propiedad/<int:propiedad_id>/", views.detalle_propiedad, name="detalle_propiedad"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
]

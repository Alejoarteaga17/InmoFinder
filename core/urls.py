from django.urls import path
from core import views

urlpatterns = [
    path("buscar/", views.buscar_propiedades, name="buscar_propiedades"),
    path("propiedad/<int:propiedad_id>/", views.detalle_propiedad, name="detalle_propiedad"),
]

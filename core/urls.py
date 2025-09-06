from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("buscar/", views.buscar_propiedades, name="buscar_propiedades"),
    path("propiedad/<int:propiedad_id>/", views.detalle_propiedad, name="detalle_propiedad"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    # nombre exacto que busca el código/templates
    path("buscar/", views.buscar_propiedades, name="buscar_propiedades"),
    path("buscar/", views.buscar_propiedades, name="buscar"),
    path("dashboard/", views.OwnerDashboardView.as_view(), name="dashboard"),
    path("admin-dashboard/", views.AdminDashboardView.as_view(), name="admin_dashboard"),
    path("create/", views.PropiedadCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", views.PropiedadUpdateView.as_view(), name="edit"),
    path("delete/<int:pk>/", views.PropiedadDeleteView.as_view(), name="delete"),
    path("propiedad/<int:propiedad_id>/", views.detalle_propiedad, name="detalle_propiedad"),
    path("propiedad/<int:propiedad_id>/contact/", views.contact_owner, name="contact_owner"),
    path("media/<int:propiedad_id>/", views.media_list, name="media_list"),
    path("contact/<int:propiedad_id>/", views.contact_owner, name="contact"),
    path("contact-form/<int:propiedad_id>/", views.contact_form, name="contact_form"),
    path("role-redirect/", views.role_redirect, name="role_redirect"),
    path('toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
]
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "is_propietario", "is_comprador", "is_staff")
    list_filter = ("is_propietario", "is_comprador", "is_staff")
    fieldsets = list(UserAdmin.fieldsets) + [
        ("Rol en InmoFinder", {"fields": ("is_propietario", "is_comprador", "telefono")}),
    ]


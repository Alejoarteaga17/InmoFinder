from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "email", "is_admin", "is_propietario", "is_comprador", "is_staff")
    list_filter = ("is_admin","is_propietario", "is_comprador", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name", "phone")

    fieldsets = list(UserAdmin.fieldsets) + [
        ("Rol en InmoFinder", {"fields": ("is_admin", "is_propietario", "is_comprador", "phone")}),
    ]


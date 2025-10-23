from django.contrib import admin
from .models import Propiedad, MediaPropiedad

class MediaPropiedadInline(admin.TabularInline):
    model = MediaPropiedad
    extra = 0

@admin.register(Propiedad)
class PropiedadAdmin(admin.ModelAdmin):
    list_display  = ("id", "title", "owner", "location", "property_type", "price_cop", "created_at")
    list_filter   = ("property_type", "pets_allowed", "furnished", "estrato", "created_at")
    search_fields = ("title", "location", "seller", "listing_url")
    inlines       = [MediaPropiedadInline]
    ordering      = ("-created_at", "-id")

@admin.register(MediaPropiedad)
class MediaPropiedadAdmin(admin.ModelAdmin):
    list_display  = ("id", "propiedad", "tipo", "created_at")
    list_filter   = ("tipo", "created_at")
    search_fields = ("propiedad__title", "url", "archivo")
    ordering      = ("-created_at", "-id")

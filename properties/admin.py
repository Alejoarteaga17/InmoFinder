from django.contrib import admin
from .models import Propiedad, MediaPropiedad


class MediaPropiedadInline(admin.TabularInline):
    model = MediaPropiedad
    extra = 1


@admin.register(Propiedad)
class PropiedadAdmin(admin.ModelAdmin):
    list_display  = ("id", "title", "location", "price_cop", "price_m2_display")
    search_fields = ("title", "location")
    inlines       = [MediaPropiedadInline]
    # Si quieres mantenerlo como solo lectura en el detalle:
    readonly_fields = ("price_m2_display",)


@admin.register(MediaPropiedad)
class MediaPropiedadAdmin(admin.ModelAdmin):
    list_display  = ("id", "propiedad", "tipo")
    list_filter   = ("tipo",)        # <-- tupla
    search_fields = ("propiedad__title", "url", "archivo")
    ordering      = ("-id",)         # <-- tupla

from django.contrib import admin
from .models import Propiedad, MediaPropiedad

# Register your models here.
admin.site.register(MediaPropiedad)

class MediaPropiedadInline(admin.TabularInline):
    model = MediaPropiedad
    extra = 1

class PropiedadAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "location", "price_cop", "price_m2_display")
    readonly_fields = ("price_m2_display",)
    search_fields = ("title", "location")

admin.site.register(Propiedad,PropiedadAdmin)

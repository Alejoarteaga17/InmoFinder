from django.contrib import admin
from .models import Propiedad, MediaPropiedad

# Register your models here.
admin.site.register(MediaPropiedad)

class MediaPropiedadInline(admin.TabularInline):
    model = MediaPropiedad
    extra = 1

class PropiedadAdmin(admin.ModelAdmin):
    pass

admin.site.register(Propiedad,PropiedadAdmin)

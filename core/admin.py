from django.contrib import admin
from .models import Propiedad, MediaPropiedad

admin.site.register(MediaPropiedad)

# admin.site.register(ImagenPropiedad)

# class ImagenPropiedadInline(admin.TabularInline):
#     model = ImagenPropiedad
#     extra = 1

class MediaPropiedadInline(admin.TabularInline):
    model = MediaPropiedad
    extra = 1

class PropiedadAdmin(admin.ModelAdmin):
    pass

admin.site.register(Propiedad,PropiedadAdmin)

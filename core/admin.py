from django.contrib import admin
from .models import ImagenPropiedad, Propiedad

admin.site.register(ImagenPropiedad)

class ImagenPropiedadInline(admin.TabularInline):
    model = ImagenPropiedad
    extra = 1

class PropiedadAdmin(admin.ModelAdmin):
    inlines = [ImagenPropiedadInline]

admin.site.register(Propiedad,PropiedadAdmin)



# Register your models here.

from mimetypes import guess_type

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

User = get_user_model()

class Propiedad(models.Model):
    # Relación con el propietario (owner)
    owner = models.ForeignKey(User, related_name='propiedades', on_delete=models.CASCADE, null=True, blank=True)

    # Información general
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255)
    property_type = models.CharField(max_length=50, choices=[
        ('Apartamento', 'Apartamento'),
        ('Casa', 'Casa'),
        ('Lote', 'Lote'),
        ('Oficina', 'Oficina'),
        ('Otro', 'Otro'),
    ])
    condition = models.CharField(max_length=100, blank=True, null=True)
    seller = models.CharField(max_length=255, blank=True, null=True)
    listing_url = models.URLField(blank=True, null=True)

    # Características físicas
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    area_privada_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    rooms = models.IntegerField()
    bathrooms = models.IntegerField()
    parking_spaces = models.IntegerField()
    floor = models.IntegerField()
    estrato = models.IntegerField(blank=True, null=True)

    # Estado y adicionales
    antiguedad = models.CharField(max_length=50, blank=True, null=True)
    cantidad_de_pisos = models.IntegerField(blank=True, null=True)
    codigo_fincaraiz = models.CharField(max_length=50, blank=True, null=True)

    # Amenidades
    amenities = models.JSONField(blank=True, null=True)

    # Precio y administración
    price_cop = models.BigIntegerField()
    admin_fee_cop = models.BigIntegerField(blank=True, null=True)

    # Características adicionales
    pets_allowed = models.BooleanField(default=False)
    furnished = models.BooleanField(default=False)

    # Fechas
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.location}"

    @property
    def price_m2(self):
        """Computed price per square meter (COP per m2).

        Returns None if area is zero or missing to avoid division errors.
        Uses Decimal math from the stored Decimal/Integer fields.
        """
        try:
            # area_m2 is DecimalField; price_cop is integer
            if not self.area_m2 or float(self.area_m2) == 0:
                return None
            # Convert to float for simple division; templates can format as needed
            return float(self.price_cop) / float(self.area_m2)
        except Exception:
            return None

    @property
    def price_m2_display(self):
        """Friendly integer value (COP per m²) to show in templates/admin.

        Returns an int (rounded) or None when price per m2 is not computable.
        """
        val = self.price_m2
        if val is None:
            return None
        # Return integer rounded to nearest COP
        try:
            return int(round(val))
        except Exception:
            return None


class MediaPropiedad(models.Model):
    MAX_FILES_PER_PROPERTY = 10
    MAX_FILE_MB = 1000  # 1000 MB
    ALLOWED_PREFIXES = ("image/", "video/")

    propiedad = models.ForeignKey(Propiedad, related_name='media', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='propiedades/', blank=True, null=True)
    tipo = models.CharField(max_length=10, choices=[('imagen', 'Imagen'), ('video', 'Video')], blank=True)
    url = models.URLField(blank=True, null=True)  # Para almacenar links de imágenes externas (como los del JSON)

    # ------ Helpers internos ------
    def _infer_mime_and_type(self):
        """
        Devuelve (mime, tipo_inferido) según archivo o url.
        tipo_inferido en {'imagen', 'video'}.
        """
        # 1) Si viene desde request.FILES, suele traer content_type
        content_type = ""
        if self.archivo and hasattr(self.archivo, "file"):
            content_type = getattr(self.archivo, "content_type", "") or ""

        # 2) Si no, intenta por nombre/ruta
        candidate = ""
        if not content_type:
            if self.archivo:
                candidate = getattr(self.archivo, "name", "") or ""
            elif self.url:
                candidate = self.url or ""
            mime, _ = guess_type(candidate)
        else:
            mime = content_type

        if not mime:
            # fallback por extensión
            lower = (candidate or "").lower()
            if lower.endswith((".mp4", ".mov", ".avi", ".webm", ".mkv")):
                return ("video/mp4", "video")
            # por defecto lo tratamos como imagen
            return ("image/jpeg", "imagen")

        tipo_inferido = "video" if mime.startswith("video/") else "imagen"
        return (mime, tipo_inferido)

    # ------ Validaciones ------
    def clean(self):
        super().clean()

        # --- 1) Al menos uno: archivo o url
        if not self.archivo and not self.url:
            raise ValidationError("Provide a file or an external URL.")

        # --- 2) Validaciones de archivo (si viene archivo)
        if self.archivo:
            size = getattr(self.archivo, "size", None)
            if size is not None and size > self.MAX_FILE_MB * 1024 * 1024:
                raise ValidationError(f"File exceeds {self.MAX_FILE_MB} MB.")

            ctype = getattr(self.archivo, "content_type", "") or ""
            if ctype and not any(ctype.startswith(p) for p in self.ALLOWED_PREFIXES):
                raise ValidationError(f"Unsupported content type: {ctype}. Allowed: images/videos.")

        # --- 3) Validaciones de URL (si viene URL)
        if self.url:
            mime, tipo = self._infer_mime_and_type()
            if not any(mime.startswith(p) for p in self.ALLOWED_PREFIXES):
                raise ValidationError(f"Unsupported URL content type: {mime}. Allowed: images/videos.")

        # --- 4) Tope total (imágenes + videos) = 10 por propiedad
        # Solo valida si hay propiedad (en admin inline y en vistas debería haberla)
        if not self.propiedad_id and getattr(self, "propiedad", None):
            # por si tienes la FK en memoria pero no el id aún
            self.propiedad_id = self.propiedad.pk

        if self.propiedad_id:
            qs = MediaPropiedad.objects.filter(propiedad_id=self.propiedad_id)
            # si es actualización, no contarse a sí mismo
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.count() >= self.MAX_FILES_PER_PROPERTY:
                raise ValidationError(
                    f"Esta propiedad ya alcanzó el máximo de {self.MAX_FILES_PER_PROPERTY} archivos (imágenes + videos)."
                )

    def save(self, *args, **kwargs):
        # Ejecutar validaciones de modelo siempre
        self.full_clean()

        # Detectar tipo automáticamente si no se pasó
        if not self.tipo:
            # Inferir de archivo o url
            _, tipo = self._infer_mime_and_type()
            self.tipo = tipo or 'imagen'

        super().save(*args, **kwargs)

    @property
    def media_url(self) -> str:
        """URL pública del recurso (archivo o remota)."""
        if self.archivo:
            try:
                return self.archivo.url
            except Exception:
                return ""
        return self.url or ""

    def __str__(self):
        return f"Media de {self.propiedad.title or f'Propiedad {self.propiedad_id}'} ({self.tipo or '—'})"

class ContactMessage(models.Model):
    propiedad = models.ForeignKey(
        'Propiedad',
        related_name='contact_messages',
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='contact_messages',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    nombre = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True, null=True)  # ✅ agregado (útil para contacto)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)  # ✅ agregado (para marcar mensajes leídos)

    def __str__(self):
        # ✅ corregido: 'propiedad.nombre' no existe, debe ser 'propiedad.title'
        return f"Mensaje de {self.nombre} sobre {self.propiedad.title}"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE, related_name='favoritos')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'propiedad')

    def __str__(self):
        return f"{self.user.username} ❤️ {self.propiedad.title}"
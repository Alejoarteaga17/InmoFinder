from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from mimetypes import guess_type

User = get_user_model()

# =========================
# Propiedad
# =========================

class Propiedad(models.Model):
    # Relación con el propietario (owner)
    owner = models.ForeignKey(
        User,
        related_name='propiedades',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

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
    area_privada_m2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
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

    # Fechas (mantengo tu definición original)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        # Orden por más reciente cuando created_at esté poblado
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f"{self.title or 'Propiedad'} - {self.location}"


# =========================
# MediaPropiedad
# =========================
class MediaPropiedad(models.Model):
    MAX_FILE_MB = 1000  # 1000 MB
    ALLOWED_PREFIXES = ("image/", "video/")

    propiedad = models.ForeignKey(
        Propiedad,
        related_name='media',
        on_delete=models.CASCADE
    )
    # Un solo campo para imágenes o videos
    archivo = models.FileField(upload_to='propiedades/%Y/%m/%d/', blank=True, null=True)
    tipo = models.CharField(
        max_length=10,
        choices=[('imagen', 'Imagen'), ('video', 'Video')],
        blank=True
    )
    # URLs remotas (para las traídas por IA si las usas)
    url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # útil si reemplazas archivo

    class Meta:
        ordering = ['-created_at', '-id']

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
        # Al menos uno: archivo o url
        if not self.archivo and not self.url:
            raise ValidationError("Provide a file or an external URL.")

        # Si viene archivo, validar tamaño y tipo
        if self.archivo:
            size = getattr(self.archivo, "size", None)
            if size is not None and size > self.MAX_FILE_MB * 1024 * 1024:
                raise ValidationError(f"File exceeds {self.MAX_FILE_MB} MB.")

            ctype = getattr(self.archivo, "content_type", "") or ""
            if ctype and not any(ctype.startswith(p) for p in self.ALLOWED_PREFIXES):
                raise ValidationError(f"Unsupported content type: {ctype}. Allowed: images/videos.")

        # Si viene URL, inferir tipo por MIME/extensión
        if self.url:
            mime, tipo = self._infer_mime_and_type()
            if not any(mime.startswith(p) for p in self.ALLOWED_PREFIXES):
                raise ValidationError(f"Unsupported URL content type: {mime}. Allowed: images/videos.")

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


# =========================
# Contact Message
# =========================
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
    telefono = models.CharField(max_length=20, blank=True, null=True)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha_envio', '-id']

    def __str__(self):
        return f"Mensaje de {self.nombre} sobre {self.propiedad.title}"

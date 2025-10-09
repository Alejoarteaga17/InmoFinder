import json
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth import get_user_model
from properties.models import Propiedad, MediaPropiedad

User = get_user_model()

class Command(BaseCommand):
    help = "Importa propiedades desde un archivo JSON y las guarda en la base de datos"

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Ruta al archivo JSON")
        parser.add_argument(
            "--email",
            type=str,
            help="Email del usuario propietario (opcional)",
            default=None
        )

    def handle(self, *args, **options):
        json_path = options["json_path"]
        owner_email = options.get("email")

        # Si se pasa un email, intenta obtener el usuario
        owner = None
        if owner_email:
            try:
                owner = User.objects.get(email=owner_email)
                self.stdout.write(self.style.SUCCESS(f"Usando usuario: {owner.email}"))
            except User.DoesNotExist:
                raise CommandError(f"No existe un usuario con el email: {owner_email}")

        # Cargar el JSON
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f"Error al leer el archivo JSON: {e}")

        # Si no es lista, envolverlo
        if isinstance(data, dict):
            data = [data]

        count = 0
        for entry in data:
            try:
                details = entry.get("property details") or {}
                antiguedad = details.get("antiguedad") if isinstance(details, dict) else None
                cantidad_de_pisos = details.get("cantidad_de_pisos") if isinstance(details, dict) else None
                codigo_fincaraiz = details.get("codigo_fincaraiz") if isinstance(details, dict) else None

                propiedad = Propiedad.objects.create(
                    owner=owner,
                    title=entry.get("title"),
                    description=entry.get("description"),
                    location=entry.get("location"),
                    property_type=entry.get("property_type"),
                    condition=entry.get("condition"),
                    seller=entry.get("seller"),
                    listing_url=entry.get("listing_url"),
                    area_m2=entry.get("area_m2") or 0,
                    area_privada_m2=entry.get("area_privada_m2") or 0,
                    rooms=entry.get("rooms") or 0,
                    bathrooms=entry.get("bathrooms") or 0,
                    parking_spaces=entry.get("parking_spaces") or 0,
                    floor=entry.get("floor") or 0,
                    estrato=entry.get("estrato"),
                    antiguedad=antiguedad,
                    cantidad_de_pisos=cantidad_de_pisos,
                    codigo_fincaraiz=codigo_fincaraiz,
                    amenities=entry.get("amenities", []),
                    price_cop=entry.get("price_cop") or 0,
                    admin_fee_cop=entry.get("admin_fee_cop"),
                    pets_allowed=entry.get("pets_allowed", False),
                    furnished=entry.get("furnished", False),
                    created_at=timezone.now(),
                )

                # Agregar media (URLs)
                media_urls = entry.get("media_urls", [])
                for url in media_urls:
                    MediaPropiedad.objects.create(propiedad=propiedad, url=url)

                count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"✅ Propiedad creada: {propiedad.title or '(sin título)'} — {len(media_urls)} medios."
                ))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error en propiedad {entry.get('title')}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Importación completada. Total: {count} propiedades."))

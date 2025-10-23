import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from properties.models import Propiedad, MediaPropiedad

# Datos base
tipos = ["Piso", "Casa", "Chalet", "Ático", "Dúplex", "Estudio", "Loft"]
zonas_comunes_opciones = [
    "Piscina comunitaria",
    "Gimnasio",
    "Zona infantil",
    "Parqueadero de visitantes",
    "Terraza BBQ",
    "Cancha de fútbol",
    "Vigilancia 24h",
    "Jacuzzi"
]
imagenes_demo = [
    "properties/default.jpg",
]
videos_demo = [
    "properties/muestra.mp4",
]
barrios = [
    "El Poblado", "Laureles", "Envigado", "Bello",
    "Sabaneta", "Itagüí", "Robledo", "Belén",
    "Castilla", "San Javier", "La América", "Buenos Aires"
]


class Command(BaseCommand):
    help = "Puebla la base de datos con propiedades de ejemplo en Medellín"

    def add_arguments(self, parser):
        parser.add_argument("--n", type=int, default=20, help="Cantidad de propiedades a generar")

    def handle(self, *args, **options):
        n = options["n"]
        User = get_user_model()

        # 👤 Crear o recuperar usuario propietario demo
        demo_email = "alejandro_10_123@hotmail.com"
        demo_user, created = User.objects.get_or_create(
            email=demo_email,
            defaults={
                "username": "alejandro_demo",
                "is_propietario": True,
                "is_comprador": False,
            }
        )
        if created:
            demo_user.set_password("123456")  # ⚠️ password por defecto, puedes cambiarlo
            demo_user.save()
            self.stdout.write(self.style.SUCCESS(f"👤 Usuario demo creado: {demo_email} (propietario)"))
        else:
            self.stdout.write(f"➡️ Usando usuario existente: {demo_email}")

        # 🏡 Crear propiedades
        for _ in range(n):
            nombre = f"{random.choice(tipos)} en {random.choice(barrios)}"
            area = Decimal(random.randint(35, 250))
            precio_m2 = Decimal(random.randint(250000, 6000000))
            precio_total = precio_m2 * area
            habitaciones = random.randint(1, 6)
            banos = random.randint(1, 4)
            parqueaderos = random.randint(0, 3)

            propiedad = Propiedad.objects.create(
                owner=demo_user,
                title=nombre,
                description=f"Propiedad en {nombre}, ideal para familias o inversión.",
                price_cop=int(precio_total),
                area_m2=area,
                rooms=habitaciones,
                bathrooms=banos,
                parking_spaces=parqueaderos,
                location="Medellín, Colombia",
                property_type=random.choice(tipos),
                amenities=random.sample(zonas_comunes_opciones, k=random.randint(1, 3)),
                pets_allowed=bool(random.getrandbits(1))
            )

            # Añadir imágenes
            for _ in range(random.randint(1, 3)):
                MediaPropiedad.objects.create(
                    propiedad=propiedad,
                    # for demo we use url field pointing to static demo image
                    url=random.choice(imagenes_demo),
                    tipo="imagen"
                )

            # Añadir un video opcional
            if random.choice([True, False]):
                MediaPropiedad.objects.create(
                    propiedad=propiedad,
                    url=random.choice(videos_demo),
                    tipo="video"
                )

        self.stdout.write(self.style.SUCCESS(
            f"✅ Se generaron {n} propiedades de ejemplo en Medellín para {demo_email}."
        ))

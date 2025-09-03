import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import Propiedad, MediaPropiedad

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
    "propiedades/demo1.jpg",
    "propiedades/demo2.jpg",
    "propiedades/demo3.jpg",
    "propiedades/demo4.jpg",
    "propiedades/demo5.jpg"
]
videos_demo = [
    "propiedades/tour1.mp4",
    "propiedades/tour2.mp4",
    "propiedades/tour3.mp4"
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

        for _ in range(n):
            nombre = f"{random.choice(tipos)} en {random.choice(barrios)}"
            area = Decimal(random.randint(35, 250))
            precio_m2 = Decimal(random.randint(250000, 6000000))
            precio_total = precio_m2 * area
            habitaciones = random.randint(1, 6)
            bannos = random.randint(1, 4)  # 👈 corregido con doble "n"
            parqueaderos = random.randint(0, 3)

            propiedad = Propiedad.objects.create(
                nombre=nombre,
                descripcion=f"Propiedad en {nombre}, ideal para familias o inversión.",
                precio_total=precio_total,
                precio_m2=precio_m2,
                habitaciones=habitaciones,
                bannos=bannos,
                parqueaderos=parqueaderos,
                area=area,
                ubicacion="Medellín, Colombia",
                tipo=random.choice(tipos),
                zonas_comunes=", ".join(random.sample(zonas_comunes_opciones, k=random.randint(1, 3))),
                fecha_disponibilidad=date.today() + timedelta(days=random.randint(10, 180)),
                garaje=bool(random.getrandbits(1)),
                mascotas=bool(random.getrandbits(1))
            )

            # Añadir imágenes
            for _ in range(random.randint(1, 3)):
                MediaPropiedad.objects.create(
                    propiedad=propiedad,
                    archivo=random.choice(imagenes_demo),
                    tipo="imagen"
                )

            # Añadir un video opcional
            if random.choice([True, False]):
                MediaPropiedad.objects.create(
                    propiedad=propiedad,
                    archivo=random.choice(videos_demo),
                    tipo="video"
                )

        self.stdout.write(self.style.SUCCESS(f"✅ Se generaron {n} propiedades de ejemplo en Medellín."))

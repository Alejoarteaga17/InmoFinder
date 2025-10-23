from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Crea un usuario admin de pruebas."

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            email="admin_test@example.com",
            defaults={"username": "admin_test"}
        )
        user.is_admin = True  # setea is_staff vía save()
        user.is_propietario = True   # si quieres probar coexistencia
        user.is_comprador  = True
        user.set_password("Admin1234!")
        user.save()
        self.stdout.write(self.style.SUCCESS("Admin de pruebas listo: admin_test@example.com / Admin1234!"))

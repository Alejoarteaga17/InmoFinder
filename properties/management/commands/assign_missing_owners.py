from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from properties.models import Propiedad
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Asigna como owner a las propiedades que no tienen owner a un usuario específico. "
        "Si el usuario no existe, lo crea con el nombre y email proporcionados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            dest="email",
            default="ealvarezc1@eafit.edu.co",
            help="Email del usuario owner a asignar (por defecto: ealvarezc1@eafit.edu.co)",
        )
        parser.add_argument(
            "--name",
            dest="name",
            default="Emmanuel Alvarez",
            help="Nombre completo del usuario owner (por defecto: 'Emmanuel Alvarez')",
        )
        parser.add_argument(
            "--username",
            dest="username",
            default=None,
            help="Username para el usuario si se debe crear (por defecto: parte antes de @ del email)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="No realiza cambios: sólo muestra cuántas propiedades serían actualizadas",
        )
        parser.add_argument(
            "--limit",
            type=int,
            dest="limit",
            default=0,
            help="Número máximo de propiedades a actualizar (0 = todas)",
        )
        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            dest="yes",
            help="No pedir confirmación interactiva",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        email = options.get("email")
        name = options.get("name")
        username = options.get("username") or (email.split("@")[0] if email else None)
        dry_run = options.get("dry_run")
        limit = options.get("limit") or 0
        auto_confirm = options.get("yes")

        # Preparar/obtener usuario
        first_name = ""
        last_name = ""
        if name:
            parts = name.split()
            first_name = parts[0]
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        user_defaults = {"username": username, "first_name": first_name, "last_name": last_name}
        # Algunos modelos de usuario no aceptan username en defaults; envolvemos en try/except
        try:
            user, created = User.objects.get_or_create(email=email, defaults=user_defaults)
        except Exception:
            # Intentar sin username en defaults si el modelo personalizado no lo permite
            user, created = User.objects.get_or_create(email=email)
            # Asegurar username/first/last estén actualizados
            updated = False
            if username and getattr(user, "username", None) != username:
                try:
                    user.username = username
                    updated = True
                except Exception:
                    pass
            if first_name and getattr(user, "first_name", None) != first_name:
                try:
                    user.first_name = first_name
                    updated = True
                except Exception:
                    pass
            if last_name and getattr(user, "last_name", None) != last_name:
                try:
                    user.last_name = last_name
                    updated = True
                except Exception:
                    pass
            if updated:
                user.save()

        if created:
            # No ponemos contraseña real: marcamos unusable
            try:
                user.set_unusable_password()
                user.save()
            except Exception:
                # Si el modelo no soporta set_unusable_password(), ignorar
                pass
            self.stdout.write(self.style.SUCCESS(f"Usuario creado: {email}"))
        else:
            self.stdout.write(f"Usuario existente: {email}")

        # Consultar propiedades sin owner
        qs = Propiedad.objects.filter(owner__isnull=True).order_by("id")
        total = qs.count()
        if limit and limit > 0:
            qs = qs[:limit]
        selected_count = qs.count() if hasattr(qs, 'count') else len(list(qs))

        self.stdout.write(f"Propiedades sin owner encontradas: {total}")
        if limit:
            self.stdout.write(f"Se actualizarán (limit): {selected_count}")
        else:
            self.stdout.write(f"Se actualizarán: {selected_count}")

        if selected_count == 0:
            self.stdout.write(self.style.NOTICE("No hay propiedades para actualizar."))
            return

        if not auto_confirm:
            confirm = input("¿Deseas continuar y asignar el owner a esas propiedades? [y/N]: ")
            if confirm.lower() not in ("y", "yes"):
                self.stdout.write("Operación cancelada.")
                return

        # Realizar la actualización dentro de una transacción
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run habilitado — no se harán cambios."))
            # Mostrar ids de ejemplo
            ids = list(qs.values_list('id', flat=True)[:20])
            self.stdout.write(f"IDs que serían actualizados (ejemplo hasta 20): {ids}")
            return

        with transaction.atomic():
            updated = 0
            # Ejecutar update en queryset de forma eficiente
            try:
                updated = qs.update(owner=user)
            except Exception:
                # Fallback: asignar uno a uno
                updated = 0
                for p in qs:
                    p.owner = user
                    p.save()
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Propiedades actualizadas: {updated}"))

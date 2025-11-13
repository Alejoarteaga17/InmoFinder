from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "properties"

    def ready(self):
        """
        Pre-cargar embeddings en memoria al iniciar el servidor.
        Esto evita la latencia en la primera búsqueda.
        """
        # Solo ejecutar en el proceso principal (no en runserver reloader)
        import os
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            try:
                from properties.management.commands.embeddings import _load_embeddings_to_cache
                print("🔄 Pre-cargando embeddings en memoria...")
                _load_embeddings_to_cache()
                print("✅ Embeddings cargados y listos para búsqueda rápida")
            except Exception as e:
                print(f"⚠️ No se pudieron pre-cargar embeddings: {e}")
                print("   (La búsqueda funcionará con fallback o cargará embeddings en el primer uso)")

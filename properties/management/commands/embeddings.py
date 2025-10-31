import os
import numpy as np
import joblib
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from django.core.management.base import BaseCommand, CommandError
from properties.models import Propiedad

# ---------- CONFIG ----------
EMBED_MODEL_NAME = 'all-MiniLM-L6-v2'
EMBED_PATH = 'property_embeddings.npy'
ID_PATH = 'property_ids.joblib'
TOP_K = 5

_model = None  # cache para el modelo


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


# ---------- GENERADOR DE EMBEDDINGS ----------
def load_or_generate_embeddings(force: bool = False):
    """Carga o genera embeddings para todas las propiedades en la BD.

    Si force=True, vuelve a generarlos aunque existan en disco.
    """
    if (not force) and os.path.exists(EMBED_PATH) and os.path.exists(ID_PATH):
        print("Cargando embeddings desde cache...")
        embeddings = np.load(EMBED_PATH)
        property_ids = joblib.load(ID_PATH)
        return property_ids, embeddings

    print("Generando embeddings desde la base de datos...")

    # 1. Obtener todas las propiedades
    propiedades = Propiedad.objects.all()
    if not propiedades.exists():
        raise CommandError("No hay propiedades en la base de datos.")

    # 2. Crear textos representativos
    corpus = []
    property_ids = []

    for prop in propiedades:
        text_parts = [
            prop.title or "",
            prop.location or "",
            prop.property_type or "",
            prop.condition or "",
            prop.description or "",
            ", ".join(prop.amenities or []),
            f"{prop.rooms} habitaciones, {prop.bathrooms} baños, {prop.area_m2} m², Estrato {prop.estrato or ''}",
            "Amoblado" if prop.furnished else "",
            "Se permiten mascotas" if prop.pets_allowed else "",
        ]
        texto_final = " ".join(str(x) for x in text_parts if x)
        corpus.append(texto_final)
        property_ids.append(prop.id)  # type: ignore

    # 3. Generar embeddings
    model = _get_model()
    embeddings = model.encode(corpus, show_progress_bar=True, convert_to_numpy=True)

    # 4. Guardar resultados
    np.save(EMBED_PATH, embeddings)
    joblib.dump(property_ids, ID_PATH)
    print(f"Embeddings generados y guardados ({len(property_ids)} propiedades).")

    return property_ids, embeddings


# ---------- BÚSQUEDA ----------
def buscar_propiedades(query_text, top_k=TOP_K):
    """Busca propiedades similares a una consulta textual."""
    if not os.path.exists(EMBED_PATH) or not os.path.exists(ID_PATH):
        raise CommandError("No hay embeddings. Ejecuta con --build para generarlos.")

    model = _get_model()
    query_vec = model.encode([query_text], convert_to_numpy=True)

    # Cargar embeddings guardados
    property_ids = joblib.load(ID_PATH)
    embeddings = np.load(EMBED_PATH)

    sims = cosine_similarity(query_vec, embeddings).flatten()
    top_idx = np.argsort(-sims)[:top_k]

    resultados = []
    for idx in top_idx:
        prop = Propiedad.objects.get(id=property_ids[idx])
        resultados.append({
            "title": prop.title,
            "location": prop.location,
            "price": prop.price_cop,
            "url": prop.listing_url,
            "score": round(float(sims[idx]), 3),
        })
    return resultados


class Command(BaseCommand):
    help = "Genera y consulta embeddings de propiedades (Sentence-Transformers)."

    def add_arguments(self, parser):
        parser.add_argument("--build", action="store_true", help="Genera (o recarga) los embeddings")
        parser.add_argument("--force", action="store_true", help="Fuerza regenerar, ignorando cache")
        parser.add_argument("--query", type=str, help="Texto a buscar entre propiedades")
        parser.add_argument("--top-k", type=int, default=TOP_K, help="Número de resultados a devolver")

    def handle(self, *args, **options):
        do_build = bool(options.get("build"))
        force = bool(options.get("force"))
        query = options.get("query")
        top_k = int(options.get("top_k") or TOP_K)

        if do_build:
            load_or_generate_embeddings(force=force)
            self.stdout.write(self.style.SUCCESS("✅ Embeddings listos."))

        if query:
            if not os.path.exists(EMBED_PATH) or not os.path.exists(ID_PATH):
                self.stdout.write("No hay embeddings en cache; generando primero...")
                load_or_generate_embeddings(force=force)
            results = buscar_propiedades(query, top_k=top_k)
            self.stdout.write("\nResultados más cercanos:")
            for r in results:
                self.stdout.write(
                    f"🏠 {r['title']} | {r['location']} | ${r['price']:,} COP | score={r['score']} | {r['url']}"
                )

        if not do_build and not query:
            self.stdout.write(
                "Uso: python manage.py embeddings --build | --query 'texto' [--top-k 5] [--force]"
            )

import os
import json
import logging
from dotenv import load_dotenv
from google import genai  # SDK de Google para Gemini / Generative Language

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Cargar API key desde .env
load_dotenv(dotenv_path="openAI.env")  # ejemplo de nombre
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicializar cliente Gemini — el SDK lee la var de entorno o la puedes pasar explícitamente
client = genai.Client(api_key=GEMINI_API_KEY)

# URLs de respaldo
URLS = [
    "https://www.fincaraiz.com.co/venta/medellin/antioquia",
    "https://www.metrocuadrado.com/apartamentos/venta/medellin/",
    "https://www.properati.com.co/s/venta/apartamento/medellin"
]

SYSTEM_MSG = """You are a real estate listings extractor.
Always return JSON with details (title, price, area, rooms, bathrooms,
location, seller, images url, listing url, etc.).
If some data is missing, use null.
"""

TARGET_RESULTS = 10

def extract_listings():
    results = []

    for url in URLS:
        if len(results) >= TARGET_RESULTS:
            logging.info("Meta alcanzada, no más URLs necesarias.")
            break

        logging.info(f"🔎 Intentando extraer desde: {url}")

        prompt = f"""
        {SYSTEM_MSG}

        Browse the following url {url}, extract up to {TARGET_RESULTS - len(results)} 
        apartment or house listings in Medellín (especially El Poblado),
        and return them as a JSON list of objects, each with a url field.
        """

        try:
            logging.info("📡 Enviando petición a Gemini...")
            response = client.models.generate_content(
                model="gemini-2.5-flash",  # o el modelo que prefieras
                contents=prompt
            )
            text = response.text
            logging.info("✅ Respuesta recibida, intentando parsear JSON...")

            try:
                listings = json.loads(text) # type: ignore
            except Exception as e:
                logging.error(f"❌ No se pudo parsear JSON de {url}: {e}")
                continue

            if isinstance(listings, dict):
                listings = [listings]

            results.extend(listings)
            logging.info(f"➡️ Extraídos {len(listings)} desde {url} | Total acumulado: {len(results)}")

        except Exception as e:
            logging.error(f"⚠️ Error con {url}: {e}")
            continue

    # Guardar JSON
    if results:
        os.makedirs("data", exist_ok=True)
        out_file = "data/listings_gemini.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logging.info(f"💾 JSON guardado en {out_file}")
    else:
        logging.warning("❌ No se extrajo nada de las URLs.")

    return results

if __name__ == "__main__":
    logging.info("🚀 Iniciando extracción con Gemini...")
    listings = extract_listings()
    logging.info(f"🏁 Proceso finalizado. Total listings: {len(listings)} (Meta: {TARGET_RESULTS})")

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Cargar API key desde .env (ajusta el nombre exacto de tu var)
load_dotenv(dotenv_path="openAI.env")
OPENAI_APIKEY = os.getenv("openai_apikey2")

client = OpenAI(api_key=OPENAI_APIKEY)

# Pool de URLs de respaldo
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

TARGET_RESULTS = 100  # número objetivo de propiedades

def extract_listings():
    results = []

    for url in URLS:
        if len(results) >= TARGET_RESULTS:
            logging.info("Meta alcanzada, no se necesitan más URLs.")
            break

        logging.info(f"Intentando extraer desde: {url}")

        USER_MSG = f"""
        Browse the following url {url}, extract up to {TARGET_RESULTS - len(results)} 
        apartment or house listings in Medellín (especially El Poblado),
        and return them as a JSON list of objects, each with a url field.
        """

        try:
            logging.info("Enviando request a OpenAI...")
            response = client.responses.create(
                model="gpt-5",
                tools=[{"type": "web_search"}],
                input=[
                    {"role": "system", "content": SYSTEM_MSG},
                    {"role": "user", "content": USER_MSG}
                ]
            )
            logging.info("Respuesta recibida, intentando parsear JSON...")

            data = response.output_text

            try:
                listings = json.loads(data)
            except Exception as e:
                logging.error(f"No se pudo parsear JSON de {url}: {e}")
                continue

            if isinstance(listings, dict):  # a veces responde dict en vez de lista
                listings = [listings]

            results.extend(listings)
            logging.info(f"➡️ Extraídos {len(listings)} desde {url} | Total acumulado: {len(results)}")

        except Exception as e:
            logging.error(f"⚠️ Error con {url}: {e}")
            continue

    # Guardar JSON en carpeta data/
    if results:
        os.makedirs("data", exist_ok=True)
        out_file = "data/listings.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logging.info(f"💾 JSON guardado en {out_file}")
    else:
        logging.warning("❌ No se extrajo ningún resultado de las URLs.")

    return results


if __name__ == "__main__":
    logging.info("🚀 Iniciando extracción de propiedades...")
    listings = extract_listings()
    logging.info(f"🏁 Proceso finalizado. Total listings: {len(listings)} (Meta: {TARGET_RESULTS})")

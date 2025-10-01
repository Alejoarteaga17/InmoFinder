import os
import json
import logging
import requests
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Cargar API key desde .env
load_dotenv(dotenv_path="openAI.env")
HF_APIKEY = os.getenv("HUGGINGFACE_API_KEY")

# Endpoint de Hugging Face (elige un modelo compatible con texto largo)
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"  # 👈 puedes cambiarlo
HF_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

HEADERS = {"Authorization": f"Bearer {HF_APIKEY}"}

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

TARGET_RESULTS = 100


def query_hf(prompt: str):
    """Enviar prompt al modelo de Hugging Face"""
    payload = {"inputs": prompt, "parameters": {"temperature": 0.3, "max_new_tokens": 2048}}
    response = requests.post(HF_URL, headers=HEADERS, json=payload)

    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}: {response.text}")

    output = response.json()

    # Hugging Face puede devolver lista o dict
    if isinstance(output, list) and len(output) > 0 and "generated_text" in output[0]:
        return output[0]["generated_text"]
    elif isinstance(output, dict) and "generated_text" in output:
        return output["generated_text"]
    else:
        return json.dumps(output, indent=2)


def extract_listings():
    results = []

    for url in URLS:
        if len(results) >= TARGET_RESULTS:
            logging.info("Meta alcanzada, no se necesitan más URLs.")
            break

        logging.info(f"🔎 Intentando extraer desde: {url}")

        USER_MSG = f"""
        {SYSTEM_MSG}

        Browse the following url {url}, extract up to {TARGET_RESULTS - len(results)} 
        apartment or house listings in Medellín (especially El Poblado),
        and return them as a JSON list of objects, each with a url field.
        """

        try:
            logging.info("📡 Enviando request a Hugging Face...")
            response_text = query_hf(USER_MSG)
            logging.info("✅ Respuesta recibida, intentando parsear JSON...")

            try:
                listings = json.loads(response_text)
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
    logging.info("🚀 Iniciando extracción de propiedades con Hugging Face...")
    listings = extract_listings()
    logging.info(f"🏁 Proceso finalizado. Total listings: {len(listings)} (Meta: {TARGET_RESULTS})")

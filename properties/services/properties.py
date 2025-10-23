
# extractor_con_mejor_filtro.py
import os
import re
import json
import time
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# ---------------- Config ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv(dotenv_path="openAI.env")
OPENAI_APIKEY = os.getenv("openai_apikey2")
client = OpenAI(api_key=OPENAI_APIKEY)

URLS = [
    "https://www.fincaraiz.com.co/venta/medellin/antioquia",
    "https://www.metrocuadrado.com/apartamentos/venta/medellin/",
    "https://www.properati.com.co/s/venta/apartamento/medellin"
]

SYSTEM_MSG = """You are a real estate listings extractor.
Always return JSON with details like:
- title
- price_cop
- area_m2
- rooms
- bathrooms
- location
- seller
- admin_fee_cop
- parking_spaces
- estrato
- floor
- area_privada_m2
- property_type
- condition
- description
- amenities (as a list)
- property details
- listing_url (MUST always be included and valid)
- pets_allowed (boolean or null)
- furnished (boolean or null)

Do NOT include image URLs (images_url). They will be scraped separately.
If some data is missing, use null.
"""

TARGET_RESULTS = 200  # ajusta según lo que necesites

# ---------- Imágenes: parámetros y utilidades ----------
IMG_ATTRS = ["src", "data-src", "data-lazy", "data-original"]
MIN_WIDTH = 300         # ancho mínimo en px para aceptar por filename (heurística)
MIN_BYTES = 10_000      # tamaño mínimo (bytes) para aceptar por HEAD
MAX_IMG_CHECKS = 30     # máximo HEADs/validaciones para no sobrecargar
HEAD_TIMEOUT = 6        # timeout para HEAD requests
SLEEP_BETWEEN_HEADS = 0.15  # pausa entre HEADs (evitar rate-limits)

# patrones que claramente indican recursos no deseados
BLACKLIST_KEYWORDS = [
    r'logo|icon|sprite|banner|placeholder|default|avatar|thumb|favicon|'
    r'facebook|google|apple|twitter|youtube|instagram|linkedin|brand|'
    r'whatsapp|email|phone|map|marker|meta|cloudfront|promo|seo|'
    r'amazonaws|s3|huawei|recorte|miniatura|header|footer'
    r'|button|btn|loader|loading|spinner|ads?|adserver|analytics|tracking',
]

# patrones que sugieren fotografías de propiedad (whitelist)
SITE_WHITELIST = [
    r"infocdn__",           # FincaRaiz pattern
    r"/repo/img/",            # many property images sit here
    r"imagenesprof",          # provider used in examples
    r"/images/",              # common pattern
    r"cdn"
]

DIM_RE = re.compile(r"(\d{2,4})[xX](\d{2,4})")  # busca "800x600" etc.
IMG_EXT_RE = re.compile(r'\.(jpg|jpeg|png|webp|gif|avif)(\?|#|$)', re.I)

_session = None
def _headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

def session():
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update(_headers())
        _session = s
    return _session

def _pick_from_srcset(srcset: str, base_url: str) -> str | None:
    try:
        parts = [p.strip() for p in srcset.split(",") if p.strip()]
        if not parts:
            return None
        # usually last has largest resolution "url 800w"
        last = parts[-1].split()[0]
        return urljoin(base_url, last)
    except Exception:
        return None

def _extract_json_urls_from_scripts(soup: BeautifulSoup, base_url: str) -> list[str]:
    urls = []
    for script in soup.find_all("script"):
        txt = (script.string or script.get_text() or "").strip()
        if not txt:
            continue
        # heurística: buscar urls dentro del script
        for m in re.finditer(r'https?://[^\s"\'<>]+', txt):
            u = m.group(0)
            if IMG_EXT_RE.search(u) or "infocdn__gr" in u:
                urls.append(urljoin(base_url, u))
    return urls

def _parse_dims_from_url(u: str) -> tuple[int, int] | None:
    m = DIM_RE.search(u)
    if m:
        try:
            w = int(m.group(1)); h = int(m.group(2))
            return w, h
        except Exception:
            return None
    return None

def _bad_keyword_in_url(u: str) -> bool:
    lu = u.lower()
    for pat in BLACKLIST_KEYWORDS:
        if re.search(pat, lu):
            return True
    return False

def _quick_whitelist(u: str) -> bool:
    lu = u.lower()
    for pat in SITE_WHITELIST:
        if re.search(pat, lu):
            return True
    return False

def _head_check_is_image(u: str) -> bool:
    try:
        s = session()
        # HEAD can be blocked; try HEAD then GET with stream if necessary
        resp = s.head(u, allow_redirects=True, timeout=HEAD_TIMEOUT)
        # Some servers don't like HEAD, try GET stream
        if resp.status_code >= 400 or not resp.headers:
            resp = s.get(u, stream=True, timeout=HEAD_TIMEOUT)
        ct = (resp.headers.get("Content-Type") or "").lower()
        cl = resp.headers.get("Content-Length")
        if not ct.startswith("image/"):
            return False
        if cl:
            try:
                if int(cl) < MIN_BYTES:
                    return False
            except Exception:
                pass
        # if we get here, it's likely a valid image
        return True
    except Exception:
        return False

def get_property_images(url: str, max_imgs: int = 12) -> list[str]:
    """
    Extrae y filtra URLs de imágenes desde la página de un anuncio.
    No descarga imágenes, usa HEAD para validar cuando es necesario.
    """
    try:
        s = session()
        resp = s.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logging.warning(f"No se pudo cargar {url} para imágenes: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    candidates = []

    # 1) srcset/source
    for tag in soup.find_all(["img", "source"]):
        if tag.name == "img":
            srcset = tag.get("srcset")
            if srcset:
                # bs4 may return an AttributeValue (string or list-like); normalize to a string
                if isinstance(srcset, (list, tuple)):
                    srcset_str = ",".join(str(p) for p in srcset)
                else:
                    srcset_str = str(srcset)
                chosen = _pick_from_srcset(srcset_str, url)
                if chosen:
                    candidates.append(chosen)
        # common lazy attrs + src
        for a in IMG_ATTRS + ["src"]:
            v = tag.get(a)
            if v:
                candidates.append(urljoin(url, str(v)))

    # 2) meta tags
    for prop in ["og:image", "twitter:image", "og:image:url"]:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            candidates.append(urljoin(url, str(tag["content"])))

    # 3) inline JSON / scripts
    candidates.extend(_extract_json_urls_from_scripts(soup, url))

    # 4) embedded styles background-image
    for tag in soup.find_all(style=True):
        style = str(tag.get("style", ""))  # ensure a str for the regex finder (bs4 may return non-str types)
        for m in re.finditer(r'url\((["\']?)(.*?)\1\)', style):
            candidates.append(urljoin(url, m.group(2)))

    # Normalize, preserve order
    seen = set()
    normalized = []
    for c in candidates:
        if not c:
            continue
        # strip fragments/params that are irrelevant for uniqueness but keep them for HEAD
        nc = c.split("#")[0]
        if nc not in seen:
            seen.add(nc)
            normalized.append(nc)

    # Soft-filter and then validate with HEAD when uncertain
    accepted = []
    head_checks_done = 0
    for c in normalized:
        lc = c.lower()

        # quick rejection: obviously non-image or svg
        if not IMG_EXT_RE.search(lc) and "infocdn__gr" not in lc:
            # may still be an image (some URLs lack extension), try later with HEAD if under limit
            if head_checks_done < MAX_IMG_CHECKS:
                head_checks_done += 1
                time.sleep(SLEEP_BETWEEN_HEADS)
                if _head_check_is_image(c):
                    accepted.append(c)
            continue

        # reject small thumbnails by dimension in filename if present
        dims = _parse_dims_from_url(lc)
        if dims:
            w, h = dims
            if w < MIN_WIDTH or h < 80:  # height threshold low but width must be reasonable
                logging.debug(f"Skipping small dimension image {c} ({w}x{h})")
                continue

        # reject by blacklist keywords
        if _bad_keyword_in_url(lc):
            logging.debug(f"Skipping blacklisted image {c}")
            continue

        # quick whitelist acceptance for known good patterns
        if _quick_whitelist(lc):
            accepted.append(c)
            if len(accepted) >= max_imgs:
                break
            else:
                continue

        # if extension indicates an image, do a HEAD check if we still need more certainty
        if IMG_EXT_RE.search(lc):
            # some images might be small icons, check size with HEAD
            if head_checks_done < MAX_IMG_CHECKS:
                head_checks_done += 1
                time.sleep(SLEEP_BETWEEN_HEADS)
                if _head_check_is_image(c):
                    accepted.append(c)
            else:
                # if we exhausted head checks, accept heuristically
                accepted.append(c)

        # stop if we have enough
        if len(accepted) >= max_imgs:
            break

    logging.info(f"Found {len(normalized)} candidates, accepted {len(accepted)} images for {url}")
    return accepted[:max_imgs]

# ---------- Extractor principal ----------
def extract_listings():
    results = []

    for base_url in URLS:
        if len(results) >= TARGET_RESULTS:
            logging.info("Meta alcanzada, no se necesitan más URLs.")
            break

        logging.info(f"Intentando extraer desde: {base_url}")

        USER_MSG = f"""
        Browse the following url {base_url}, extract up to {TARGET_RESULTS - len(results)} 
        apartment or house listings in Medellín (especially El Poblado),
        and return them as a JSON list of objects. 
        Each object MUST include a valid "listing_url" pointing to the property page.
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
            data = response.output_text
            logging.info("Respuesta recibida, intentando parsear JSON...")

            try:
                listings = json.loads(data)
            except Exception as e:
                logging.error(f"No se pudo parsear JSON de {base_url}: {e}")
                continue

            if isinstance(listings, dict):
                listings = [listings]

            # Por cada propiedad, scrapear imágenes
            for prop in listings:
                prop_url = prop.get("listing_url") or prop.get("listing url") or prop.get("url")
                if not prop_url:
                    prop["media_urls"] = None
                    continue
                imgs = get_property_images(prop_url, max_imgs=12)
                prop["media_urls"] = imgs if imgs else None

            logging.info(f"Imágenes extraídas para {len(listings)} propiedades.")
            results.extend(listings)
            logging.info(f"Extraídos {len(listings)} desde {base_url} | Total acumulado: {len(results)}")

        except Exception as e:
            logging.error(f"Error con {base_url}: {e}")
            continue

    # Guardar JSON: filtrar solo los que tengan listing_url y media_urls (si así lo deseas)
    valid_results = [p for p in results if (p.get("listing_url") or p.get("listing url") or p.get("url")) and p.get("media_urls")]

    if valid_results:
        os.makedirs("data", exist_ok=True)
        out_file = "data/listingFiltered.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(valid_results, f, indent=2, ensure_ascii=False)
        logging.info(f"JSON guardado en {out_file} con {len(valid_results)} propiedades válidas.")
    else:
        logging.warning("No se extrajo ningún resultado válido con imágenes.")

    return valid_results

if __name__ == "__main__":
    logging.info("Iniciando extracción de propiedades...")
    listings = extract_listings()
    logging.info(f"Proceso finalizado. Total listings guardadas: {len(listings)} (Meta: {TARGET_RESULTS})")


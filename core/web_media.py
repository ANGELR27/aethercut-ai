import re
import ssl
from pathlib import Path
from typing import Optional, Dict, Any, List

import aiohttp
import aiofiles
import certifi

# Verificación TLS activa, con el paquete de certificados de certifi (el del sistema puede estar desactualizado).
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

def _session(headers: Dict[str, str], total: int) -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=total),
        connector=aiohttp.TCPConnector(ssl=_SSL_CTX),
    )

# Wikimedia exige un User-Agent identificable; sin él responde 403.
USER_AGENT = "AetherCutAI/1.0 (video editor; educational use) python-aiohttp"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}


class WikiResult:
    """Resultado de una búsqueda enciclopédica real (título, extracto, imagen y URL fuente)."""

    def __init__(self, title: str, extract: str, image_url: Optional[str], page_url: str, lang: str):
        self.title = title
        self.extract = extract
        self.image_url = image_url
        self.page_url = page_url
        self.lang = lang

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "extract": self.extract,
            "image_url": self.image_url,
            "page_url": self.page_url,
            "lang": self.lang,
        }


class WikiMediaClient:
    """
    Cliente de Wikipedia/Wikimedia (gratuito, sin API key).

    A diferencia de un generador de imágenes con IA, devuelve FOTOS REALES y texto de una
    enciclopedia con enlace verificable, apto para usar como referencia en pantalla.
    """

    API = "https://{lang}.wikipedia.org/w/api.php"

    async def search(self, query: str, langs: Optional[List[str]] = None) -> Optional[WikiResult]:
        for lang in (langs or ["es", "en"]):
            result = await self._search_one(query, lang)
            if result:
                return result
        return None

    async def _search_one(self, query: str, lang: str) -> Optional[WikiResult]:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": 1,
            "prop": "pageimages|extracts|info",
            "piprop": "thumbnail",
            "pithumbsize": 1280,
            "exintro": 1,
            "explaintext": 1,
            "exsentences": 3,
            "inprop": "url",
            "redirects": 1,
        }
        try:
            async with _session(HEADERS, 12) as session:
                async with session.get(self.API.format(lang=lang), params=params) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json(content_type=None)
        except Exception as exc:
            print(f"[WikiMedia] Error buscando '{query}' ({lang}): {exc}")
            return None

        pages = (data.get("query") or {}).get("pages") or {}
        if not pages:
            return None
        page = sorted(pages.values(), key=lambda p: p.get("index", 99))[0]
        extract = re.sub(r"\s+", " ", (page.get("extract") or "")).strip()
        if not extract:
            return None
        return WikiResult(
            title=page.get("title", query),
            extract=extract,
            image_url=(page.get("thumbnail") or {}).get("source"),
            page_url=page.get("fullurl", ""),
            lang=lang,
        )

    async def download_image(self, url: str, destination: Path) -> bool:
        try:
            async with _session({"User-Agent": USER_AGENT}, 25) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return False
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(destination, "wb") as fh:
                        await fh.write(await resp.read())
            return True
        except Exception as exc:
            print(f"[WikiMedia] Error descargando imagen: {exc}")
            return False

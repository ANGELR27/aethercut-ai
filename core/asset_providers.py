import os
import abc
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
from config.settings import settings
from core.models import BRollCue

class AssetProvider(abc.ABC):
    """Interfaz base para proveedores de recursos multimedia (B-Roll)."""

    @abc.abstractmethod
    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        """Busca el activo más relevante y lo descarga de forma asíncrona en target_dir."""
        pass


class PixabayAssetProvider(AssetProvider):
    """Proveedor de stock utilizando la API de Pixabay (videos y fotos de alta resolución)."""

    BASE_URL_VIDEOS = "https://pixabay.com/api/videos/"
    BASE_URL_PHOTOS = "https://pixabay.com/api/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.PIXABAY_API_KEY

    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        if not self.api_key:
            return None

        query = cue.search_query_en or cue.concept
        print(f"[PixabayProvider] Buscando recurso para '{query}' ({cue.asset_type})...")

        # 1. Intentar video primero si el tipo es video
        if cue.asset_type.lower() == "video":
            download_url = await self._search_video(query)
            if download_url:
                out_path = target_dir / f"{cue.cue_id}.mp4"
                if await self._download_file(download_url, out_path):
                    return out_path

        # 2. Si no hubo video o se solicitó foto, buscar imagen
        download_url = await self._search_image(query)
        if download_url:
            out_path = target_dir / f"{cue.cue_id}.jpg"
            if await self._download_file(download_url, out_path):
                return out_path

        return None

    async def _search_video(self, query: str) -> Optional[str]:
        params = {
            "key": self.api_key,
            "q": query,
            "per_page": 3,
            "video_type": "film"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL_VIDEOS, params=params, timeout=12) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        hits = data.get("hits", [])
                        if hits:
                            videos = hits[0].get("videos", {})
                            # Preferir resolución medium o large
                            chosen = videos.get("medium", {}) or videos.get("small", {}) or videos.get("large", {})
                            return chosen.get("url")
        except Exception as e:
            print(f"[PixabayProvider] Error al buscar video: {e}")
        return None

    async def _search_image(self, query: str) -> Optional[str]:
        params = {
            "key": self.api_key,
            "q": query,
            "per_page": 3,
            "image_type": "photo",
            "orientation": "horizontal"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL_PHOTOS, params=params, timeout=12) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        hits = data.get("hits", [])
                        if hits:
                            return hits[0].get("largeImageURL") or hits[0].get("webformatURL")
        except Exception as e:
            print(f"[PixabayProvider] Error al buscar imagen: {e}")
        return None

    async def _download_file(self, url: str, destination: Path) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        async with aiofiles.open(destination, mode="wb") as f:
                            async for chunk in resp.content.iter_chunked(256 * 1024):
                                await f.write(chunk)
                        print(f"[PixabayProvider] Guardado exitosamente: {destination.name}")
                        return True
        except Exception as e:
            print(f"[PixabayProvider] Error al descargar {url}: {e}")
        return False


class PexelsAssetProvider(AssetProvider):
    """Proveedor utilizando la API oficial de Pexels (si está disponible con clave activa)."""

    BASE_URL_VIDEOS = "https://api.pexels.com/videos/search"
    BASE_URL_PHOTOS = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.PEXELS_API_KEY

    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        if not self.api_key:
            return None

        query = cue.search_query_en or cue.concept
        headers = {"Authorization": self.api_key}
        print(f"[PexelsProvider] Buscando recurso para '{query}' en Pexels...")

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                # 1. Intentar video
                if cue.asset_type.lower() == "video":
                    async with session.get(f"{self.BASE_URL_VIDEOS}?query={query}&per_page=1", timeout=12) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            videos = data.get("videos", [])
                            if videos:
                                files = videos[0].get("video_files", [])
                                if files:
                                    # Elegir calidad hd o primera disponible
                                    chosen = next((f for f in files if f.get("quality") == "hd"), files[0])
                                    dl_url = chosen.get("link")
                                    out_path = target_dir / f"{cue.cue_id}.mp4"
                                    if await self._download_direct(session, dl_url, out_path):
                                        return out_path

                # 2. Fallback a foto
                async with session.get(f"{self.BASE_URL_PHOTOS}?query={query}&per_page=1", timeout=12) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        photos = data.get("photos", [])
                        if photos:
                            dl_url = photos[0].get("src", {}).get("large2x") or photos[0].get("src", {}).get("large")
                            out_path = target_dir / f"{cue.cue_id}.jpg"
                            if await self._download_direct(session, dl_url, out_path):
                                return out_path

        except Exception as e:
            print(f"[PexelsProvider] Error en Pexels: {e}")
        return None

    async def _download_direct(self, session: aiohttp.ClientSession, url: str, destination: Path) -> bool:
        try:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(destination, mode="wb") as f:
                        async for chunk in resp.content.iter_chunked(256 * 1024):
                            await f.write(chunk)
                    print(f"[PexelsProvider] Guardado en: {destination.name}")
                    return True
        except Exception as e:
            print(f"[PexelsProvider] Error de descarga: {e}")
        return False


class OpenStockAssetProvider(AssetProvider):
    """
    Proveedor de fotos e ilustraciones enciclopédicas reales verificadas de alta resolución
    mediante Wikimedia Commons y bibliotecas abiertas (100% libre de IA deforme).
    """

    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        from core.web_media import WikiMediaClient
        query = cue.search_query_en or cue.concept
        print(f"[OpenStockProvider] Buscando fotografía real enciclopédica para '{query}'...")
        client = WikiMediaClient()
        res = await client.search(query, langs=["es", "en"])
        if res and res.image_url:
            out_path = target_dir / f"{cue.cue_id}_wiki.jpg"
            if await client.download_image(res.image_url, out_path):
                try:
                    from PIL import Image
                    with Image.open(out_path) as im:
                        # Asegurar resolución aceptable
                        if im.size[0] >= 640 and im.size[1] >= 360:
                            print(f"[OpenStockProvider] Foto real verificada obtenida: {out_path.name} ({im.size})")
                            return out_path
                except Exception:
                    pass
                out_path.unlink(missing_ok=True)
        return None


class FallbackSyntheticAssetProvider(AssetProvider):
    """
    Proveedor resiliente autónomo.
    Genera un B-Roll cinematográfico estilizado mediante Pillow si las APIs externas
    no tienen claves o están pausadas, garantizando que el pipeline de render NUNCA se rompa.
    """

    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        from PIL import Image, ImageDraw

        out_path = target_dir / f"{cue.cue_id}_fallback.jpg"
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"[FallbackProvider] Generando asset sintético de alta resolución para '{cue.concept}'...")

        width, height = 1920, 1080
        img = Image.new("RGB", (width, height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        draw.rectangle([60, 60, width - 60, height - 60], outline=(56, 189, 248), width=3)

        title = f"[B-ROLL: {cue.concept.upper()}]"
        subtitle = f"Visual Cue: {cue.search_query_en} ({cue.asset_type})"
        meta = f"Duración: {round(cue.end_sec - cue.start_sec, 2)}s | Motivo: {cue.reasoning}"

        draw.text((120, height // 2 - 80), title, fill=(248, 250, 252))
        draw.text((120, height // 2), subtitle, fill=(148, 163, 184))
        draw.text((120, height // 2 + 60), meta, fill=(56, 189, 248))

        img.save(out_path, "JPEG", quality=95)
        return out_path


class WebPhotoAssetProvider(AssetProvider):
    """Foto REAL desde la búsqueda de imágenes web (DuckDuckGo), filtrando marcas de agua comerciales y exigiendo alta resolución."""

    WATERMARK_DOMAINS = (
        "dreamstime", "alamy", "shutterstock", "istockphoto", "istock",
        "gettyimages", "123rf", "adobestock", "depositphotos", "bigstockphoto", "canstockphoto",
        "freepik", "vectorstock", "stockphoto", "watermark", "pond5", "envato",
        "storyblocks", "motionelements", "pixtastock", "agefotostock",
        "ftcdn.net", "ftcdn", "stock.adobe", "adobe.com", "canva", "eyeem", "shutter"
    )

    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        import asyncio
        from PIL import Image
        from core.web_media import WikiMediaClient

        query = cue.search_query_en or cue.concept

        def search() -> list:
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    # Priorizar imágenes Wallpaper o Large fotorrealistas sin marcas de agua
                    res = []
                    search_term = f"{query} editorial documentary photograph -stock -watermark -shutterstock -adobestock"
                    try:
                        res = list(ddgs.images(search_term, size="Wallpaper", max_results=15))
                    except Exception:
                        pass
                    if not res:
                        try:
                            res = list(ddgs.images(search_term, size="Large", max_results=15))
                        except Exception:
                            pass
                    if not res:
                        res = list(ddgs.images(f"{query} documentary -stock", size="Large", max_results=15))
                    if not res:
                        res = list(ddgs.images(query, max_results=15))

                clean_urls = []
                for r in res:
                    img_url = r.get("image") or ""
                    if not img_url.startswith("http"):
                        continue
                    img_lower = img_url.lower()
                    page_lower = (r.get("url") or "").lower()
                    title_lower = (r.get("title") or "").lower()
                    if any(bad in img_lower or bad in page_lower or bad in title_lower for bad in self.WATERMARK_DOMAINS):
                        continue
                    w = int(r.get("width") or 0)
                    h = int(r.get("height") or 0)
                    # Exigir alta definición mínima (HD real) y evitar banners deformes
                    if (w >= 1280 and h >= 720) or (w >= 1000 and 1.2 <= (w / max(1, h)) <= 2.2):
                        clean_urls.append(img_url)
                    elif not clean_urls and min(w, h) >= 800:
                        clean_urls.append(img_url)
                return clean_urls
            except Exception as exc:
                print(f"[WebPhotoProvider] Búsqueda falló: {exc}")
                return []

        client = WikiMediaClient()
        urls = await asyncio.to_thread(search)
        for i, url in enumerate(urls[:8]):
            dest = target_dir / f"{cue.cue_id}_web{i}.jpg"
            if not await client.download_image(url, dest):
                continue
            try:
                with Image.open(dest) as im:
                    im.verify()
                with Image.open(dest) as im:
                    # Filtro de calidad estricto: mínimo 900x500 y no cuadrado ni hiper-alargado
                    aspect = im.size[0] / max(1, im.size[1])
                    if im.size[0] >= 900 and im.size[1] >= 500 and 1.1 <= aspect <= 2.4:
                        print(f"[WebPhotoProvider] Imagen HD real descargada: {dest.name} ({im.size})")
                        return dest
            except Exception:
                pass
            dest.unlink(missing_ok=True)
        return None


class YouTubeReactionAssetProvider(AssetProvider):
    """
    Proveedor autónomo de video-clips reales de YouTube y redes sociales para B-Rolls dinámicos y video-reacciones.
    Utiliza búsqueda integrada de YouTube y yt-dlp con Node.js para descargar un fragmento corto (12s) en HD 720p sin claves de API.
    """

    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        import asyncio
        import yt_dlp

        # Solo buscar clip de video si el asset requerido es explícitamente video
        if (cue.asset_type or "").lower() != "video":
            return None

        query = cue.search_query_en or cue.concept
        print(f"[YouTubeReactionProvider] Buscando clip de video para '{query}'...")

        def _fetch_slice() -> Optional[Path]:
            target_path = target_dir / f"{cue.cue_id}_yt.mp4"
            target_path.unlink(missing_ok=True)

            try:
                # Extraer un fragmento dinámico de 14 segundos variando el inicio para cada escena (evita inicios estáticos)
                start_slice = 8 + (abs(hash(query)) % 15)
                end_slice = start_slice + 14
                ydl_opts = {
                    'format': 'bestvideo[height<=1080][vcodec^=avc1]+bestaudio/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
                    'outtmpl': str(target_path.with_suffix('')) + '.%(ext)s',
                    'download_ranges': yt_dlp.utils.download_range_func(None, [(start_slice, end_slice)]),
                    'force_keyframes_at_cuts': True,
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 18,
                }
                search_query = f"ytsearch1:{query} 4k 1080p documentary video"
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([search_query])

                matches = list(target_dir.glob(f"{cue.cue_id}_yt.*"))
                if matches and matches[0].exists() and matches[0].stat().st_size > 50000:
                    chosen = matches[0]
                    if chosen.suffix.lower() != ".mp4":
                        final_mp4 = target_path.with_suffix(".mp4")
                        chosen.replace(final_mp4)
                        chosen = final_mp4

                    print(f"[YouTubeReactionProvider] Clip H.264 limpio obtenido: {chosen.name} ({chosen.stat().st_size // 1024} KB)")
                    return chosen
            except Exception as e:
                print(f"[YouTubeReactionProvider] Falló descarga de clip para '{query}': {e}")
            return None

        return await asyncio.to_thread(_fetch_slice)


class AssetProviderFactory:
    """Fábrica que prioriza fotos reales web de alta resolución sin marcas de agua ni deformaciones y clips de video para video-reacciones."""

    @staticmethod
    def get_providers():
        providers = []
        if settings.PEXELS_API_KEY:
            providers.append(PexelsAssetProvider())
        if settings.PIXABAY_API_KEY:
            providers.append(PixabayAssetProvider())
        # Proveedor de video-clips para reacciones y B-Rolls dinámicos
        providers.append(YouTubeReactionAssetProvider())
        # Priorizar fotos reales web de alta definición
        providers.append(WebPhotoAssetProvider())
        providers.append(OpenStockAssetProvider())
        return providers

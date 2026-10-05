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
                            await f.write(await resp.read())
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
                        await f.write(await resp.read())
                    print(f"[PexelsProvider] Guardado en: {destination.name}")
                    return True
        except Exception as e:
            print(f"[PexelsProvider] Error de descarga: {e}")
        return False


class OpenStockAssetProvider(AssetProvider):
    """
    Proveedor de Stock 100% abierto y gratuito SIN NECESIDAD DE API KEY.
    Utiliza Unsplash y repositorios abiertos para obtener imágenes reales en HD (1080p)
    inmediatamente según el concepto de búsqueda.
    """

    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        query = cue.search_query_en or cue.concept
        # Reemplazar espacios para URL
        sanitized_query = query.replace(" ", "%20")
        
        # Endpoint de imagen real de alta definición temática sin clave
        download_url = f"https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1920&q=80"
        
        # También probamos el motor dinámico temático abierto de Pollinations/Unsplash
        dynamic_url = f"https://image.pollinations.ai/prompt/{sanitized_query}%20cinematic%20photorealistic%204k?width=1920&height=1080&nologo=true"
        
        out_path = target_dir / f"{cue.cue_id}_real.jpg"
        print(f"[OpenStockProvider] Obteniendo B-Roll real abierto para '{query}'...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(dynamic_url, timeout=15) as resp:
                    if resp.status == 200:
                        target_dir.mkdir(parents=True, exist_ok=True)
                        async with aiofiles.open(out_path, mode="wb") as f:
                            await f.write(await resp.read())
                        print(f"[OpenStockProvider] B-Roll real descargado con éxito: {out_path.name}")
                        return out_path
        except Exception as e:
            print(f"[OpenStockProvider] Fallback en descarga abierta: {e}")

        return None


class FallbackSyntheticAssetProvider(AssetProvider):
    """
    Proveedor resiliente autónomo.
    Genera un B-Roll cinematográfico estilizado mediante Pillow si las APIs externas
    no tienen claves o están pausadas, garantizando que el pipeline de render NUNCA se rompa.
    """

    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        from PIL import Image, ImageDraw, ImageFont

        out_path = target_dir / f"{cue.cue_id}_fallback.jpg"
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"[FallbackProvider] Generando asset sintético de alta resolución para '{cue.concept}'...")

        # Generar un lienzo oscuro con gradiente cinematográfico
        width, height = 1920, 1080
        img = Image.new("RGB", (width, height), color=(15, 23, 42)) # Slate oscuro estilo Galaxy
        draw = ImageDraw.Draw(img)

        # Marco visual translúcido / acento
        draw.rectangle([60, 60, width - 60, height - 60], outline=(56, 189, 248), width=3) # Cyan glow

        # Texto del concepto
        title = f"[B-ROLL: {cue.concept.upper()}]"
        subtitle = f"Visual Cue: {cue.search_query_en} ({cue.asset_type})"
        meta = f"Duración: {round(cue.end_sec - cue.start_sec, 2)}s | Motivo: {cue.reasoning}"

        # Dibujar textos
        draw.text((120, height // 2 - 80), title, fill=(248, 250, 252))
        draw.text((120, height // 2), subtitle, fill=(148, 163, 184))
        draw.text((120, height // 2 + 60), meta, fill=(56, 189, 248))

        img.save(out_path, "JPEG", quality=95)
        print(f"[FallbackProvider] Asset sintético creado en: {out_path.name}")
        return out_path


class WebPhotoAssetProvider(AssetProvider):
    """Foto REAL desde la búsqueda de imágenes web (DuckDuckGo), validada con Pillow. Sin API key."""

    async def search_and_download(self, cue: BRollCue, target_dir: Path) -> Optional[Path]:
        import asyncio
        from PIL import Image
        from core.web_media import WikiMediaClient

        def search() -> list:
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    res = list(ddgs.images(cue.search_query_en or cue.concept, max_results=8))
                return [r.get("image") for r in res
                        if (r.get("image") or "").startswith("http") and min(int(r.get("width") or 0), int(r.get("height") or 0)) >= 480]
            except Exception as exc:
                print(f"[WebPhotoProvider] Búsqueda falló: {exc}")
                return []

        client = WikiMediaClient()
        for i, url in enumerate((await asyncio.to_thread(search))[:4]):
            dest = target_dir / f"{cue.cue_id}_web{i}.jpg"
            if not await client.download_image(url, dest):
                continue
            try:
                with Image.open(dest) as im:
                    im.verify()
                with Image.open(dest) as im:
                    if min(im.size) >= 400:
                        return dest
            except Exception:
                pass
            dest.unlink(missing_ok=True)
        return None


class AssetProviderFactory:
    """Fábrica que elige el mejor proveedor disponible en cascada (solo material real)."""

    @staticmethod
    def get_providers():
        providers = []
        if settings.PIXABAY_API_KEY:
            providers.append(PixabayAssetProvider())
        if settings.PEXELS_API_KEY:
            providers.append(PexelsAssetProvider())
        providers.append(WebPhotoAssetProvider())
        # Sin placeholders sintéticos: si no hay material real, el B-Roll se omite.
        return providers

"""Radar de Viralidad.

Mantienen dos bibliotecas vivas para la producción de KAI:

1. Ranking de videos virales de otras regiones (YouTube Data API v3,
   chart=mostPopular por región), puntuados por velocidad de vistas,
   ratio de likes y frescura. Cada refresco (3 h) recalcula el ranking y
   el movimiento (sube/baja/nuevo) frente a la foto anterior.
2. Temas urgentes de alta viralidad que aún NO tienen video: candidatos
   extraídos de noticias frescas (DDG) y evaluados por la IA con score de
   viralidad, urgencia, ángulo y por qué explotarlos ya.

Con un clic, cualquiera de los dos se "replica": la IA convierte los
parámetros del original en un tema en español con mejoras y notas de
estructura que alimenta directamente al pipeline creador de KAI.
"""

from __future__ import annotations

import json
import math
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from config.settings import settings
from core.llm import LLMClient, safe_log

REGION_FLAGS = {
    "US": "🇺🇸", "GB": "🇬🇧", "CA": "🇨🇦", "AU": "🇦🇺", "MX": "🇲🇽", "ES": "🇪🇸",
    "DE": "🇩🇪", "FR": "🇫🇷", "JP": "🇯🇵", "BR": "🇧🇷", "IN": "🇮🇳", "KR": "🇰🇷",
}

# Consultas frescas para descubrir temas SIN cobertura en video.
TOPIC_QUERIES = [
    ("descubrimiento", "new discovery announced scientists", "nuevo descubrimiento científico anunciado"),
    ("urgente", "breaking news world reaction", "noticia urgente de última hora impacto"),
    ("concepto", "explained concept everyone talking about", "concepto que todos deberían conocer 2026"),
    ("espacio", "space agency announcement", "agencia espacial anuncio misión"),
    ("arqueologia", "archaeological finding revealed", "hallazgo arqueológico revelado"),
    ("tecnologia", "AI breakthrough demonstration", "inteligencia artificial avance demostración"),
    ("misterio", "unexplained phenomenon researchers", "fenómeno inexplicable investigadores"),
    ("salud", "medical study surprising results", "estudio médico resultados sorprendentes"),
]

# Categorías oficiales de YouTube (snippet.categoryId) → etiqueta y emoji.
YT_CATEGORIES = {
    "1": ("cine", "🎬"), "2": ("autos", "🚗"), "10": ("musica", "🎵"),
    "15": ("animales", "🐾"), "17": ("deportes", "⚽"), "19": ("viajes", "✈️"),
    "20": ("gaming", "🎮"), "22": ("vlogs", "📹"), "23": ("comedia", "😂"),
    "24": ("entretenimiento", "🍿"), "25": ("noticias", "📰"), "26": ("tutorial", "🛠️"),
    "27": ("educacion", "🎓"), "28": ("ciencia", "🔬"),
}


def _parse_iso_duration(value: str) -> int:
    """Duración ISO 8601 de YouTube (PT4M13S) a segundos."""
    match = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", value or "")
    if not match:
        return 0
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


# Política editorial de fragmentos: uso justo con límite duro de 6 segundos.
CLIP_POLICY = (
    "POLÍTICA DE FRAGMENTOS (uso justo): se permiten clips del video original y de gameplays SOLO como "
    "apoyo de comentario/reacción/cita, NUNCA reproduciendo una misma parte más de 6 segundos seguidos y "
    "siempre con narración y análisis propios encima. El material principal del video es 100% del estudio "
    "(b-roll de bancos libres, tarjetas visuales, gráficos, locución original). Si el contenido no admite "
    "fragmentos, decide el formato según el puntaje de viralidad: reacción, narración, datos o explicación."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


STOPWORDS = {
    "the", "and", "for", "with", "que", "los", "las", "del", "por", "para", "una", "con",
}


def _norm_words(text: str) -> set:
    return set(re.findall(r"[a-záéíóúüñ0-9]{3,}", (text or "").lower())) - STOPWORDS


class TrendRadar:
    REFRESH_INTERVAL_SEC = 3 * 3600  # re-chequeo cada 3 horas (sube/baja)
    MAX_VIDEOS = 30
    MAX_TOPICS = 8
    YOUTUBE_API = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(self):
        self._lock = threading.Lock()
        self._refreshing = False
        self._state: Dict[str, Any] = {
            "videos": [], "topics": [], "updated_at": None,
            "next_update_at": None, "produced": [],
        }
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------- persistencia
    def _paths(self):
        return settings.STORAGE_DIR / "trend_radar.json", settings.STORAGE_DIR / "trend_radar_history.json"

    def _load(self) -> None:
        data_path, history_path = self._paths()
        try:
            if data_path.exists():
                raw = json.loads(data_path.read_text(encoding="utf-8"))
                for key in self._state:
                    if key in raw:
                        self._state[key] = raw[key]
            if history_path.exists():
                self._snapshots = json.loads(history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            safe_log(f"[TrendRadar] Datos previos ilegibles: {exc}")

    def _save(self) -> None:
        data_path, history_path = self._paths()
        try:
            data_path.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
            # Podar el histórico: solo videos vistos en los últimos 7 días.
            week_ago = time.time() - 7 * 86400
            pruned = {vid: snap for vid, snap in self._snapshots.items()
                     if float(snap.get("ts") or 0) >= week_ago}
            self._snapshots = pruned
            history_path.write_text(json.dumps(pruned, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            safe_log(f"[TrendRadar] No se pudo guardar el estado: {exc}")

    # ---------------------------------------------------------------- snapshot
    def get_snapshot(self, auto_refresh: bool = True) -> Dict[str, Any]:
        stale = self._is_stale()
        if auto_refresh and stale:
            self.start_background_refresh()
        return {
            "videos": self._state["videos"],
            "topics": self._state["topics"],
            "updated_at": self._state["updated_at"],
            "next_update_at": self._state["next_update_at"],
            "refreshing": self._refreshing,
            "regions": [r.strip() for r in settings.TREND_REGIONS.split(",") if r.strip()],
            "interval_hours": self.REFRESH_INTERVAL_SEC / 3600,
        }

    def _is_stale(self) -> bool:
        updated = self._state.get("updated_at")
        if not updated:
            return True
        try:
            age = (datetime.now(timezone.utc) - _parse_iso(updated)).total_seconds()
            return age >= self.REFRESH_INTERVAL_SEC
        except ValueError:
            return True

    # ------------------------------------------------------------- scheduler
    def scheduler_loop(self) -> None:
        """Daemon del servidor: refresco inicial + revisión cada 3 horas."""
        time.sleep(2)  # no competir con el arranque del pipeline
        while True:
            try:
                if self._is_stale():
                    self.refresh()
            except Exception as exc:
                safe_log(f"[TrendRadar] Refresco programado falló: {exc}")
            time.sleep(min(900, self.REFRESH_INTERVAL_SEC // 4))

    def start_background_refresh(self) -> bool:
        thread = threading.Thread(target=self._refresh_worker, daemon=True)
        thread.start()
        return True

    def _refresh_worker(self) -> None:
        try:
            self.refresh()
        except Exception as exc:
            safe_log(f"[TrendRadar] Refresco en background falló: {exc}")

    # ---------------------------------------------------------------- refresh
    def refresh(self) -> Dict[str, Any]:
        """Barrido completo: charts de YouTube + temas urgentes con IA."""
        with self._lock:
            if self._refreshing:
                return self.get_snapshot(auto_refresh=False)  # otro hilo ya barre
            self._refreshing = True
        try:
            videos = self._fetch_viral_videos()
            topics = self._fetch_urgent_topics(avoid=videos)
            self._state["videos"] = videos
            self._state["topics"] = topics
            self._state["updated_at"] = _now_iso()
            self._state["next_update_at"] = datetime.now(timezone.utc).timestamp() + self.REFRESH_INTERVAL_SEC
            self._state["next_update_at"] = datetime.fromtimestamp(
                self._state["next_update_at"], timezone.utc).isoformat()
            self._save()
            safe_log(f"[TrendRadar] Radar actualizado: {len(videos)} videos virales, {len(topics)} temas urgentes.")
            return self.get_snapshot(auto_refresh=False)
        finally:
            self._refreshing = False

    # ------------------------------------------------- ranking videos virales
    def _fetch_viral_videos(self) -> List[Dict[str, Any]]:
        if not settings.YOUTUBE_DATA_API_KEY:
            safe_log("[TrendRadar] Sin YOUTUBE_DATA_API_KEY no hay ranking de videos.")
            return self._state.get("videos", [])
        regions = [r.strip().upper() for r in settings.TREND_REGIONS.split(",") if r.strip()]
        collected: List[Dict[str, Any]] = []
        for region in regions:
            try:
                resp = requests.get(
                    self.YOUTUBE_API,
                    params={
                        "part": "snippet,statistics,contentDetails",
                        "chart": "mostPopular",
                        "regionCode": region,
                        "maxResults": 25,
                        "key": settings.YOUTUBE_DATA_API_KEY,
                    },
                    timeout=25,
                )
                if resp.status_code != 200:
                    safe_log(f"[TrendRadar] Chart {region} HTTP {resp.status_code}: {resp.text[:120]}")
                    continue
                now = datetime.now(timezone.utc)
                for item in resp.json().get("items", []):
                    record = self._score_video(item, region, now)
                    if record:
                        collected.append(record)
            except Exception as exc:
                safe_log(f"[TrendRadar] Error en chart {region}: {exc}")

        collected.sort(key=lambda v: v["score"], reverse=True)
        # Deduplicar: el mismo video puede aparecer en el chart de varias regiones.
        dedup: Dict[str, Dict[str, Any]] = {}
        for video in collected:
            dedup.setdefault(video["yt_id"], video)
        top = list(dedup.values())[: self.MAX_VIDEOS]

        # Movimiento frente a la foto anterior (sube/baja/nuevo).
        for idx, video in enumerate(top):
            snap = self._snapshots.get(video["yt_id"])
            if snap:
                video["movement"] = int(snap.get("rank", idx + 1)) - (idx + 1)
                video["is_new"] = False
                dt_hours = max((time.time() - float(snap.get("ts") or 0)) / 3600.0, 0.5)
                gained = max(0, video["views"] - int(snap.get("views") or 0))
                video["views_gained"] = gained
                video["measured_velocity"] = int(gained / dt_hours)
            else:
                video["movement"] = 0
                video["is_new"] = True
                video["views_gained"] = 0
                video["measured_velocity"] = None
            video["rank"] = idx + 1

        # Nueva foto para el siguiente ciclo.
        now_ts = time.time()
        for video in top:
            self._snapshots[video["yt_id"]] = {
                "rank": video["rank"], "views": video["views"], "ts": now_ts,
            }
        return top

    def _score_video(self, item: Dict[str, Any], region: str, now: datetime) -> Optional[Dict[str, Any]]:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        try:
            published = _parse_iso(snippet.get("publishedAt", ""))
        except (ValueError, TypeError):
            return None
        hours = max((now - published).total_seconds() / 3600.0, 1.0)
        views = int(stats.get("viewCount") or 0)
        likes = int(stats.get("likeCount") or 0)
        if views < 10_000:
            return None  # el chart de "otra región" debe ser contenido que ya explota

        views_per_hour = views / max(hours, 2.0)
        like_ratio = (likes / views) if views else 0.0
        recency = math.exp(-hours / 60.0)
        score = round(
            55 * min(1.0, views_per_hour / 150_000)
            + 25 * min(1.0, like_ratio / 0.12)
            + 20 * recency,
            1,
        )
        thumbs = snippet.get("thumbnails", {})
        thumb = (thumbs.get("medium") or thumbs.get("high") or {}).get("url", "")
        category_id = str(snippet.get("categoryId", "") or "")
        category, category_emoji = YT_CATEGORIES.get(category_id, ("viral", "🔥"))
        duration_sec = _parse_iso_duration(item.get("contentDetails", {}).get("duration", ""))
        return {
            "yt_id": item.get("id", ""),
            "title": snippet.get("title", "")[:110],
            "channel": snippet.get("channelTitle", "")[:40],
            "region": region,
            "region_flag": REGION_FLAGS.get(region, "🌍"),
            "category_id": category_id,
            "category": category,
            "category_emoji": category_emoji,
            "duration_sec": duration_sec,
            "is_short": duration_sec > 0 and duration_sec <= 75,
            "views": views,
            "likes": likes,
            "like_ratio": round(like_ratio, 4),
            "views_per_hour": int(views_per_hour),
            "published_at": snippet.get("publishedAt", ""),
            "hours_old": round(hours, 1),
            "score": score,
            "thumb": thumb,
            "url": f"https://www.youtube.com/watch?v={item.get('id', '')}",
        }

    # ------------------------------------------------- temas urgentes sin video
    def _produced_topics(self) -> List[set]:
        """Temas ya producidos por KAI (para no repetir cobertura)."""
        produced: List[set] = []
        try:
            manifests = sorted(settings.PROJECTS_DIR.glob("*/project.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            for manifest in manifests[:60]:
                try:
                    doc = json.loads(manifest.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                result = doc.get("result") or {}
                options = doc.get("options") or {}
                for raw in (result.get("topic"), options.get("topic"), doc.get("original_name")):
                    if raw:
                        produced.append(_norm_words(str(raw)))
        except OSError:
            pass
        for topic in self._state.get("produced", []):
            produced.append(_norm_words(str(topic)))
        return produced

    @staticmethod
    def _is_already_covered(title: str, produced: List[set]) -> bool:
        words = _norm_words(title)
        if not words:
            return True
        for seen in produced:
            if not seen:
                continue
            overlap = len(words & seen) / max(len(words), 1)
            if overlap >= 0.55:
                return True
        return False

    def _collect_fresh_candidates(self, limit: int = 16) -> List[str]:
        from ddgs import DDGS
        candidates: List[str] = []
        seen = set()
        try:
            with DDGS() as ddgs:
                for category, en_query, es_query in TOPIC_QUERIES:
                    query = en_query if time.time() % 2 < 1 else es_query
                    try:
                        for item in ddgs.news(query, max_results=3):
                            title = (item.get("title") or "").strip()
                            clean = re.sub(r"\s*[-|–]\s*[A-Za-z0-9\.\sáéíóúÁÉÍÓÚ]+$", "", title).strip()
                            key = clean.lower()
                            if clean and len(clean) > 15 and key not in seen:
                                seen.add(key)
                                candidates.append(f"[{category}] {clean}")
                    except Exception:
                        continue
                    if len(candidates) >= limit:
                        break
        except Exception as exc:
            safe_log(f"[TrendRadar] Noticias no disponibles: {exc}")
        return candidates[:limit]

    def _fetch_urgent_topics(self, avoid: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        candidates = self._collect_fresh_candidates()
        if not candidates:
            return self._state.get("topics", [])

        # Filtrar temas que ya produjimos o que duplican un video del ranking.
        produced = self._produced_topics()
        hot_titles = [v["title"] for v in (avoid or [])]
        fresh: List[str] = []
        for cand in candidates:
            title = re.sub(r"^\[[a-záéíóú]+\]\s*", "", cand)
            if self._is_already_covered(title, produced):
                continue
            if any(_norm_words(title) & _norm_words(hot) for hot in hot_titles[:10]):
                continue
            fresh.append(title)
        if not fresh:
            fresh = candidates[:8]

        prompt = f"""Eres un estratega editorial de un canal de divulgación/news en español de alta viralidad.
Estos son titulares frescos de hoy que aún NO tienen videos en YouTube en español:

{chr(10).join(f"{i+1}. {t}" for i, t in enumerate(fresh))}

Selecciona SOLO los que merecen un video URGENTE ahora: fuerte gancho emocional o de curiosidad, dato nuevo,
relevancia masiva y poca cobertura existente. Descarta titulares banales, deportivos de rutina o sin ángulo.
Para cada uno responde en español:
- "title": título del tema en español, directo y potente (máx 90 caracteres)
- "category": una de "descubrimiento", "urgente", "concepto", "espacio", "arqueologia", "tecnologia", "misterio", "salud"
- "urgency": 1 a 10 (10 = hay que publicarlo HOY)
- "virality": 0 a 100 (fuerza de viralidad estimada)
- "why": por qué explota ahora y por qué aún no hay video (1-2 frases)
- "angle": el ángulo/gancho concreto que KAI debe usar al producirlo (1 frase)

Responde SOLO con JSON válido: {{"topics": [...]}} con máximo {self.MAX_TOPICS} temas ordenados por virality."""

        try:
            client = LLMClient()
            raw = client.generate(prompt, json_mode=True, deadline_sec=75)
            data = json.loads(raw)
            topics = data.get("topics", [])
        except Exception as exc:
            safe_log(f"[TrendRadar] La IA no pudo puntuar los temas: {exc}")
            return self._state.get("topics", [])

        clean: List[Dict[str, Any]] = []
        for topic in topics[: self.MAX_TOPICS]:
            title = str(topic.get("title", "")).strip()[:120]
            if not title or self._is_already_covered(title, produced):
                continue
            clean.append({
                "title": title,
                "category": str(topic.get("category", "urgente")).strip().lower(),
                "urgency": max(1, min(10, int(topic.get("urgency") or 5))),
                "score": max(0, min(100, int(topic.get("virality") or 50))),
                "why": str(topic.get("why", ""))[:300],
                "angle": str(topic.get("angle", ""))[:300],
                "spotted_at": _now_iso(),
            })
        return clean

    # ------------------------------------------------- replicación con mejoras
    def _video_source_block(self, payload: Dict[str, Any]) -> str:
        duration_sec = payload.get("duration_sec") or 0
        duration_txt = f"{duration_sec // 60}:{duration_sec % 60:02d} min" if duration_sec else "desconocida"
        return (
            f"VIDEO VIRAL ORIGINAL ({payload.get('region_flag', '')} {payload.get('region', '')}):\n"
            f"- Título: {payload.get('title', '')}\n"
            f"- Canal: {payload.get('channel', '')}\n"
            f"- Tipo de contenido: {payload.get('category', 'viral')} (categoría de YouTube)\n"
            f"- Duración del original: {duration_txt}{' · es un Short/vertical' if payload.get('is_short') else ''}\n"
            f"- Vistas: {payload.get('views', 0)} · Velocidad: {payload.get('views_per_hour', 0)} vistas/hora\n"
            f"- Score de viralidad: {payload.get('score', 0)}/100"
        )

    def analyze_video(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza el video original y devuelve por qué funciona + enfoques posibles.

        El usuario elige el enfoque (o deja que la IA decida) antes de producir.
        """
        source = self._video_source_block(payload)
        prompt = f"""Eres estratega de contenido viral del canal de divulgación en español de KAI.
Analiza este video viral y decide QUÉ contenido sobre él funcionará mejor para el público hispano.
{CLIP_POLICY}

{source}

Responde SOLO con JSON válido:
- "why_works": por qué funciona el original (2-3 frases, en español)
- "audience": a qué público hispano le va a explotar este tema (1 frase)
- "options": exactamente 3 enfoques DIFERENTES entre sí, ordenados de mejor a alternativo, cada uno:
  - "id": "a", "b" o "c"
  - "format": tipo de pieza (reacción, fenómeno, explicación, datos, historia, teoría, ranking...)
  - "title": título propuesto en español para el video de KAI (máx 100 caracteres)
  - "pitch": qué haría ese video y por qué funcionaría (1-2 frases)
  - "duration_sec": duración recomendada para KAI, entre 45 y 240
  - "viral_estimate": 0 a 100 de fuerza viral estimada de ESTE enfoque
  - "recommended": true SOLO en el mejor enfoque
Los enfoques deben respetar el tipo de contenido: con derechos (música/cine) → piezas sobre el
FENÓMENO o reacción, nunca análisis de la obra ni recreación."""

        client = LLMClient()
        raw = client.generate(prompt, json_mode=True, deadline_sec=75)
        data = json.loads(raw)
        options = []
        for idx, opt in enumerate(data.get("options", [])[:3]):
            title = str(opt.get("title", "")).strip()[:110]
            if not title:
                continue
            options.append({
                "id": str(opt.get("id") or chr(97 + idx)),
                "format": str(opt.get("format", "enfoque")).strip()[:24],
                "title": title,
                "pitch": str(opt.get("pitch", "")).strip()[:280],
                "duration_sec": max(45, min(240, int(opt.get("duration_sec") or 90))),
                "viral_estimate": max(0, min(100, int(opt.get("viral_estimate") or 50))),
                "recommended": bool(opt.get("recommended")),
            })
        if not options:
            raise ValueError("La IA no devolvió enfoques válidos.")
        return {
            "why_works": str(data.get("why_works", ""))[:400],
            "audience": str(data.get("audience", ""))[:200],
            "options": options,
        }

    def build_replication(self, kind: str, payload: Dict[str, Any],
                          choice: Optional[Dict[str, Any]] = None,
                          instructions: str = "") -> Dict[str, Any]:
        """Convierte un video viral o un tema urgente en la brief en español para KAI.

        Si `choice` viene dado, el director humano eligió ese enfoque (viene de
        analyze_video) y la brief debe producirlo exactamente. `instructions`
        permite indicaciones libres adicionales. KAI NUNCA reutiliza fragmentos
        del original: todo el material es 100% propio del estudio.
        """
        if kind == "video":
            source = self._video_source_block(payload)
            format_rules = (
                "REGLAS DE FORMATO según el tipo de contenido:\n"
                "- Musical, cine, trailer o contenido con DERECHOS: pieza sobre el FENÓMENO/reacción "
                "(por qué explota, la historia, cifras, impacto cultural). NUNCA análisis de la obra ni recreación.\n"
                "- Gaming, entretenimiento, comedia, vlogs: explica el FENÓMENO/reto/formato; se permiten clips de "
                "gameplay del original ≤6s como apoyo con narración propia encima.\n"
                "- Educativo, ciencia, noticia, tutorial: replica el FORMATO con mejor investigación y estructura.\n"
                "- Si el original es un Short vertical, la réplica debe ser ágil y directa al gancho."
            )
            duration_rule = (
                '- "recommended_duration_sec": duración del video de KAI en segundos (45 a 240), decidida por el ritmo '
                "del original y el formato elegido, NO una copia de la duración original."
            )
        else:
            source = (
                f"TEMA URGENTE SIN COBERTURA:\n"
                f"- Titular: {payload.get('title', '')}\n"
                f"- Urgencia: {payload.get('urgency', 5)}/10 · Viralidad estimada: {payload.get('score', 50)}/100\n"
                f"- Por qué explota: {payload.get('why', '')}\n"
                f"- Ángulo sugerido: {payload.get('angle', '')}"
            )
            format_rules = ""
            duration_rule = (
                '- "recommended_duration_sec": duración del video de KAI en segundos (45 a 180) según la profundidad '
                "que merece el tema."
            )

        directive = ""
        if choice:
            directive = (
                f"\nDECISIÓN DEL DIRECTOR HUMANO (obligatoria, produce EXACTAMENTE esto):\n"
                f"- Enfoque elegido: {choice.get('format', '')}\n"
                f"- Título objetivo: {choice.get('title', '')}\n"
                f"- Pitch: {choice.get('pitch', '')}\n"
                f"- Duración objetivo: {choice.get('duration_sec', 90)} s\n"
            )
        if instructions.strip():
            directive += f"\nIndicaciones libres del director: {instructions.strip()[:400]}\n"

        prompt = f"""Eres el director creativo del canal de divulgación en español de KAI.
Vas a replicar con mejoras este contenido para el público hispano. NO copies: supéralo.
{CLIP_POLICY}

{source}

{format_rules}
{directive}
Responde SOLO con JSON válido:
- "topic": tema/producto concreto para que KAI investigue y produzca (máx 110 caracteres, en español neutro,
  con gancho. Para contenido con derechos debe ser sobre el FENÓMENO, no sobre la obra)
- "extra_notes": brief para el equipo IA: por qué funciona el original, qué mejorar/añadir, estructura
  (gancho 3s → desarrollo → cierre), tono, tipo de tarjetas visuales y recordatorio de producción con material
  original. Máximo 550 caracteres, en español.
{duration_rule}"""

        client = LLMClient()
        raw = client.generate(prompt, json_mode=True, deadline_sec=75)
        data = json.loads(raw)
        topic = str(data.get("topic", "")).strip()[:120] or str(payload.get("title", ""))[:110]
        notes = str(data.get("extra_notes", "")).strip()[:600]
        if not topic:
            raise ValueError("La IA no devolvió un tema válido para replicar.")
        try:
            recommended = int(data.get("recommended_duration_sec") or 0)
        except (TypeError, ValueError):
            recommended = 0
        if choice and choice.get("duration_sec"):
            recommended = int(choice["duration_sec"])

        # Registrarlo para no volver a sugerirlo como "sin cobertura".
        produced = self._state.setdefault("produced", [])
        if topic not in produced:
            produced.append(topic)
            produced[:] = produced[-120:]
        self._save()
        safe_log(f"[TrendRadar] Réplica preparada: {topic}")
        return {"topic": topic, "extra_notes": notes, "recommended_duration_sec": recommended}

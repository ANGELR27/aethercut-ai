"""Módulo de Selección Inteligente de Contenido y Curaduría Visual (SmartMediaCurator).

Implementa el protocolo de análisis, verificación, clasificación de procedencia
y alternativas visuales honestas para la producción de video con IA:
1. Identificación semántica de afirmaciones que requieren apoyo visual.
2. Búsqueda dirigida a entidades exactas (fechas, personas, lugares, acontecimientos).
3. Evaluación y verificación de concordancia temporal, geográfica y de contexto.
4. Preferencia por archivos documentales de alta fiabilidad (Wikimedia Commons, NASA, prensa editorial).
5. Distinción explícita de naturaleza visual: documental real, ilustrativo, reconstrucción 3D, generado por IA, o simbólico.
6. Registro de procedencia (URL de origen, fuente, autor, licencia y condiciones de uso).
7. Descarte de material con marcas de agua, baja resolución, clickbait o no coincidente.
8. Generación de alternativas visuales honestas (cifras, mapas, tipografía cinética, comparativas versus, diagramas conceptuales).
9. Temporización milimétrica para aparición y retiro oportuno sin saturar la pantalla.
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class VisualIntentType(str, Enum):
    """Categoría del apoyo visual requerido según lo narrado."""
    STAT_NUMBER = "stat_number"          # Cifra, porcentaje, métrica, récord
    GEO_LOCATION = "geo_location"        # Lugar, país, coordenadas, geografía
    VERSUS_COMPARISON = "versus_comparison" # Comparación A vs B, antes vs después
    IMPACT_PHRASE = "impact_phrase"      # Frase contundente, declaración clave
    HISTORICAL_EVENT = "historical_event" # Acontecimiento con fecha/hecho documentado
    PERSON_ENTITY = "person_entity"      # Persona o figura histórica concreta
    COMPLEX_CONCEPT = "complex_concept"  # Concepto técnico, proceso o sistema difícil
    GENERAL_BROLL = "general_broll"      # B-Roll contextual estándar


class VisualNature(str, Enum):
    """Naturaleza y grado de autenticidad del material visual."""
    DOCUMENTAL_REAL = "documental_real"     # Fotografía o metraje histórico/periodístico auténtico
    ILUSTRATIVO = "ilustrativo"             # Imagen contextualmente afín (no del momento exacto)
    RECONSTRUCCION = "reconstruccion"       # Recreación 3D, simulación o render CGI
    GENERADO_IA = "generado_ia"             # Arte sintético generado por IA (nunca pasar como real)
    SIMBOLICO = "simbolico"                 # Diagrama conceptual, mapa vectorial o icono


@dataclass
class VisualIntent:
    """Intención visual detectada a partir de la locución."""
    intent_type: VisualIntentType
    entity_name: str
    secondary_entity: str = ""
    year: Optional[int] = None
    location: str = ""
    stat_value: str = ""
    stat_label: str = ""
    raw_sentence: str = ""
    trigger_words: List[str] = field(default_factory=list)
    suggested_template: str = "auto"
    recommended_nature: VisualNature = VisualNature.DOCUMENTAL_REAL


@dataclass
class ResourceProvenance:
    """Registro de origen, metadatos y condiciones de uso de un recurso."""
    source_url: str
    source_name: str
    license_type: str = "Uso libre / Editorial"
    author_or_institution: str = "Archivo oficial"
    date_recorded: str = ""
    location_recorded: str = ""
    visual_nature: VisualNature = VisualNature.ILUSTRATIVO
    attribution_badge: str = "ARCHIVO DOCUMENTAL"
    context_note: str = ""
    verified_match: bool = False
    relevance_score: float = 0.5


class SmartMediaCurator:
    """Motor de curaduría inteligente, verificación de recursos y alternativas visuales honestas."""

    # Dominios de stock comercial con marcas de agua o restricciones severas a descartar
    WATERMARK_BLOCKLIST = (
        "dreamstime", "alamy", "shutterstock", "istockphoto", "istock",
        "gettyimages", "123rf", "adobestock", "depositphotos", "bigstockphoto",
        "freepik", "vectorstock", "pond5", "envato", "storyblocks", "motionelements",
        "canstockphoto", "clipart", "renderhub", "turbosquid", "cgtrader",
        "stock.adobe", "canva", "eyeem", "shutter"
    )

    # Coordenadas geográficas y sinónimos para detección de lugares
    GEO_REGIONS: Dict[str, Tuple[str, str]] = {
        "estados unidos": ("Estados Unidos", "EE.UU."),
        "ee.uu": ("Estados Unidos", "EE.UU."),
        "eeuu": ("Estados Unidos", "EE.UU."),
        "usa": ("Estados Unidos", "EE.UU."),
        "china": ("China", "Asia Oriental"),
        "argentina": ("Argentina", "Cono Sur"),
        "brasil": ("Brasil", "Sudamérica"),
        "brazil": ("Brasil", "Sudamérica"),
        "colombia": ("Colombia", "Andes"),
        "méxico": ("México", "Norteamérica"),
        "mexico": ("México", "Norteamérica"),
        "chile": ("Chile", "Pacífico Sur"),
        "perú": ("Perú", "Andes Centrales"),
        "peru": ("Perú", "Andes Centrales"),
        "españa": ("España", "Europa"),
        "espana": ("España", "Europa"),
        "francia": ("Francia", "Europa Occidental"),
        "alemania": ("Alemania", "Europa Central"),
        "reino unido": ("Reino Unido", "Islas Británicas"),
        "inglaterra": ("Inglaterra", "Reino Unido"),
        "rusia": ("Rusia", "Eurasia"),
        "ucrania": ("Ucrania", "Europa Oriental"),
        "japón": ("Japón", "Asia Pacífico"),
        "japon": ("Japón", "Asia Pacífico"),
        "israel": ("Israel", "Medio Oriente"),
        "estrecho de ormuz": ("Estrecho de Ormuz", "Golfo Pérsico"),
        "canal de panamá": ("Canal de Panamá", "Centroamérica"),
        "canal de panama": ("Canal de Panamá", "Centroamérica"),
        "canal de suez": ("Canal de Suez", "Egipto"),
        "amazonas": ("Amazonas", "Sudamérica"),
        "antártida": ("Antártida", "Polo Sur"),
        "antartida": ("Antártida", "Polo Sur"),
        "marte": ("Marte", "Sistema Solar"),
        "luna": ("La Luna", "Órbita Terrestre"),
        "monte ararat": ("Monte Ararat", "Turquía / Armenia"),
        "dyatlov": ("Paso Dyatlov", "Montes Urales"),
        "nazca": ("Líneas de Nazca", "Perú"),
        "cern": ("CERN / Gran Colisionador", "Ginebra, Suiza"),
    }

    # Conceptos técnicos de impacto
    TECHNICAL_KEYWORDS = (
        "algoritmo", "red neuronal", "inteligencia artificial", "modelo de lenguaje",
        "fusión nuclear", "fisión", "adn", "arn", "microchip", "semiconductor",
        "cuántico", "cuántica", "blockchain", "cifrado", "inflación", "pib",
        "gravedad", "relatividad", "nanotecnología", "satélite", "telescopio",
        "código", "software", "api", "compresión", "resolución", "frecuencia"
    )

    # Expresiones de impacto o gancho
    IMPACT_PATTERNS = (
        "el error que", "nadie te dice", "dato mata relato", "cifra mata discurso",
        "la verdad sobre", "lo que no sabías", "esto cambia todo", "se nos cayó la teoría",
        "ojo con esto", "paren las rotativas", "el secreto detrás", "punto de quiebre"
    )

    # --------------------------------------------------------------------------
    # 1. Identificar qué afirmación o concepto de la narración necesita apoyo
    # --------------------------------------------------------------------------
    @classmethod
    def analyze_narration_intent(cls, speech_text: str, scene_title: str = "") -> VisualIntent:
        """Examina el texto hablado de la escena y determina la necesidad visual prioritaria."""
        clean_text = (speech_text or "").strip()
        lower_text = clean_text.lower()
        title_low = (scene_title or "").lower()

        # 1. Detectar Comparación explícita (Lado A vs Lado B)
        vs_match = re.search(
            r"([a-zA-ZáéíóúÁÉÍÓÚñÑ\d\s]{2,20})\s+(?:vs\.?|contra|frente a|comparado con)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ\d\s]{2,20})",
            clean_text, re.IGNORECASE
        )
        if vs_match:
            side_a = vs_match.group(1).strip()
            side_b = vs_match.group(2).strip()
            # Validar que los lados no sean meras palabras gramaticales
            if len(side_a) >= 2 and len(side_b) >= 2 and side_a != side_b:
                return VisualIntent(
                    intent_type=VisualIntentType.VERSUS_COMPARISON,
                    entity_name=side_a,
                    secondary_entity=side_b,
                    raw_sentence=clean_text,
                    trigger_words=[side_a, "vs", side_b],
                    suggested_template="versus_split",
                    recommended_nature=VisualNature.SIMBOLICO,
                )

        # 2. Detectar Cifra, métrica o porcentaje clave
        stat_match = re.search(
            r"\b(\+?\$?\d+([.,]\d+)?\s*(?:%|x|mil millones|millones?|mil|billones?|veces|bpm|lufs|dólares|euros|km|kg|grados|segundos|minutos|horas)?)\b",
            clean_text, re.IGNORECASE
        )
        # Buscar contexto de la cifra
        if stat_match:
            val_str = stat_match.group(1).strip()
            # Asegurar que no sea solo un número suelto como '2' o un año de 4 cifras
            is_year_candidate = bool(re.match(r"^(18\d\d|19\d\d|20[0-3]\d)$", val_str))
            if not is_year_candidate and (any(c in val_str for c in "%x$€") or len(val_str) >= 2):
                # Extraer etiqueta breve y significativa (filtrar palabras vacías)
                stopwords = {
                    "de", "la", "el", "un", "una", "en", "por", "al", "los", "las", "del", "que", "se", "y", "o", "a",
                    "subió", "subio", "aumentó", "aumento", "bajó", "bajo", "creció", "crecio", "más", "mas", "menos",
                    "este", "esta", "estos", "estas", "con", "sin", "su", "sus", "como", "cuando", "donde", "sobre",
                    "entre", "hasta", "hacia", "desde", "para", "fue", "era", "son", "es", "han", "ha", "había", "habia",
                    "según", "segun", "casi", "alrededor", "aproximadamente", "esto"
                }
                match_start = stat_match.start()
                pre_text = clean_text[max(0, match_start - 45):match_start].strip()
                post_text = clean_text[stat_match.end():min(len(clean_text), stat_match.end() + 45)].strip()
                pre_words = [re.sub(r'^[^\w]+|[^\w]+$', '', w) for w in pre_text.split()]
                pre_meaningful = [w for w in pre_words if w and w.lower() not in stopwords and len(w) >= 3]
                post_words = [re.sub(r'^[^\w]+|[^\w]+$', '', w) for w in post_text.split()]
                post_meaningful = [w for w in post_words if w and w.lower() not in stopwords and len(w) >= 3]
                meaningful = pre_meaningful[-2:] + post_meaningful[:1]
                label_str = " ".join(meaningful).strip().title() if meaningful else (scene_title or "Métrica Clave")
                if len(label_str) < 4 or label_str.lower() in stopwords:
                    label_str = scene_title or "Métrica Clave"
                return VisualIntent(
                    intent_type=VisualIntentType.STAT_NUMBER,
                    entity_name=label_str,
                    stat_value=val_str,
                    stat_label=label_str,
                    raw_sentence=clean_text,
                    trigger_words=[val_str],
                    suggested_template="stat_counter",
                    recommended_nature=VisualNature.SIMBOLICO,
                )

        # 3. Detectar Acontecimiento histórico con año concreto en la locución (ej. 1959, 1969, 2020)
        year_match = re.search(r"\b(18\d\d|19\d\d|20[0-2]\d)\b", clean_text)
        if year_match:
            year_int = int(year_match.group(1))
            # Verificar si además se menciona un lugar geográfico en la narración
            geo_loc = ""
            ent_name = scene_title or f"Acontecimiento {year_int}"
            for geo_key, (geo_name, geo_region) in cls.GEO_REGIONS.items():
                if re.search(rf"\b{re.escape(geo_key)}\b", lower_text):
                    geo_loc = geo_region
                    ent_name = f"{geo_name} {year_int}"
                    break
            return VisualIntent(
                intent_type=VisualIntentType.HISTORICAL_EVENT,
                entity_name=ent_name,
                year=year_int,
                location=geo_loc,
                raw_sentence=clean_text,
                trigger_words=[str(year_int)],
                suggested_template="quote_evidence",
                recommended_nature=VisualNature.DOCUMENTAL_REAL,
            )

        # 4. Detectar Lugar geográfico / Mapa táctico mencionado en la locución
        for geo_key, (geo_name, geo_region) in cls.GEO_REGIONS.items():
            if re.search(rf"\b{re.escape(geo_key)}\b", lower_text):
                return VisualIntent(
                    intent_type=VisualIntentType.GEO_LOCATION,
                    entity_name=geo_name,
                    location=geo_region,
                    raw_sentence=clean_text,
                    trigger_words=[geo_key],
                    suggested_template="geointel_map",
                    recommended_nature=VisualNature.DOCUMENTAL_REAL,
                )

        # 5. Detectar Frase impactante o gancho de alta retención
        for pat in cls.IMPACT_PATTERNS:
            if pat in lower_text:
                return VisualIntent(
                    intent_type=VisualIntentType.IMPACT_PHRASE,
                    entity_name=pat.capitalize(),
                    raw_sentence=clean_text,
                    trigger_words=pat.split(),
                    suggested_template="alert_banner",
                    recommended_nature=VisualNature.SIMBOLICO,
                )

        # 6. Detectar Concepto técnico o científico complejo
        for tech_kw in cls.TECHNICAL_KEYWORDS:
            if re.search(rf"\b{re.escape(tech_kw)}\b", lower_text):
                return VisualIntent(
                    intent_type=VisualIntentType.COMPLEX_CONCEPT,
                    entity_name=tech_kw.title(),
                    raw_sentence=clean_text,
                    trigger_words=[tech_kw],
                    suggested_template="tech_card",
                    recommended_nature=VisualNature.SIMBOLICO,
                )

        # 7. Fallback si el título de escena menciona una región geográfica
        for geo_key, (geo_name, geo_region) in cls.GEO_REGIONS.items():
            if re.search(rf"\b{re.escape(geo_key)}\b", title_low):
                return VisualIntent(
                    intent_type=VisualIntentType.GEO_LOCATION,
                    entity_name=geo_name,
                    location=geo_region,
                    raw_sentence=clean_text,
                    trigger_words=[geo_key],
                    suggested_template="geointel_map",
                    recommended_nature=VisualNature.DOCUMENTAL_REAL,
                )

        # 8. Apoyo visual contextual general
        return VisualIntent(
            intent_type=VisualIntentType.GENERAL_BROLL,
            entity_name=scene_title or "Contexto Documental",
            raw_sentence=clean_text,
            suggested_template="bento",
            recommended_nature=VisualNature.ILUSTRATIVO,
        )

    # --------------------------------------------------------------------------
    # 2. Búsqueda y Enriquecimiento de Criterios Específicos
    # --------------------------------------------------------------------------
    @classmethod
    def build_targeted_search_query(cls, intent: VisualIntent, topic: str = "") -> str:
        """Construye un query en inglés hiper-específico anclado al tema real y a la entidad del caso."""
        stopwords_lower = {
            "más de", "mas de", "el error que", "según", "segun", "aumentó", "aumento",
            "era de", "fue de", "esto", "esta", "este", "métrica clave", "metrica clave", "contexto documental"
        }
        topic_str = (topic or "").strip()
        is_topic_meaningful = bool(
            topic_str
            and len(topic_str) >= 5
            and topic_str.lower() not in ("technology abstract", "video reaction", "broll", "video", "photo")
        )

        # Si el Director ya diseñó un visual_query concreto en inglés, preservarlo como base inmutable
        if is_topic_meaningful:
            clean_t = re.sub(r'[\.\,\;]+$', '', topic_str).strip()
            clean_words = dict.fromkeys(clean_t.split())
            clean_topic = " ".join(clean_words)

            if intent.intent_type == VisualIntentType.HISTORICAL_EVENT and intent.year:
                year_str = str(intent.year)
                y_part = f" {year_str}" if year_str not in clean_topic else ""
                loc_part = f" {intent.location}" if (intent.location and intent.location.lower() not in clean_topic.lower()) else ""
                return f"{clean_topic}{loc_part}{y_part} historical original archive photograph documentary 4k footage"

            if intent.intent_type == VisualIntentType.GEO_LOCATION and intent.location:
                loc_part = f" {intent.location}" if intent.location.lower() not in clean_topic.lower() else ""
                return f"{clean_topic}{loc_part} authentic landscape documentary footage 4k"

            if intent.intent_type == VisualIntentType.STAT_NUMBER and intent.stat_value:
                return f"{clean_topic} documentary footage 4k"

            return f"{clean_topic} documentary footage 4k"

        # Si no hubo topic del Director, recurrir a la entidad detectada asegurando que no sea stopword
        ent = (intent.entity_name or "").strip()
        if not ent or ent.lower() in stopwords_lower or len(ent) < 3:
            ent = topic_str or "scientific documentary investigation"

        ent_clean = re.sub(r'[\.\,\;]+$', '', ent).strip()

        if intent.intent_type == VisualIntentType.HISTORICAL_EVENT and intent.year:
            loc_part = f" {intent.location}" if intent.location else ""
            year_str = str(intent.year)
            year_part = f" {year_str}" if year_str not in ent_clean else ""
            return f"{ent_clean}{loc_part}{year_part} historical archive photograph documentary 4k"

        if intent.intent_type == VisualIntentType.GEO_LOCATION and intent.location:
            return f"{ent_clean} {intent.location} landscape documentary footage 4k"

        if intent.intent_type == VisualIntentType.VERSUS_COMPARISON and intent.secondary_entity:
            return f"{ent_clean} vs {intent.secondary_entity} comparison study documentary footage 4k"

        if intent.intent_type == VisualIntentType.COMPLEX_CONCEPT:
            return f"{ent_clean} scientific visualization documentary footage 4k"

        if intent.intent_type == VisualIntentType.STAT_NUMBER and intent.stat_value:
            return f"{ent_clean} documentary footage 4k"

        return f"{ent_clean} documentary footage 4k"

    # --------------------------------------------------------------------------
    # 3, 4, 5, 6, 7 & 8: Evaluación, Verificación, Distinción y Descarte
    # --------------------------------------------------------------------------
    @classmethod
    def verify_and_register_resource(
        cls,
        candidate_meta: Dict[str, Any],
        intent: VisualIntent,
    ) -> ResourceProvenance:
        """
        Evalúa la correspondencia entre el recurso encontrado y el contenido narrado:
        - Verifica concordancia de entidad, fecha y lugar.
        - Descarta marcas de agua, clickbait o material no coincidente.
        - Clasifica la naturaleza del material (documental real, ilustrativo, 3D, IA, simbólico).
        - Registra procedencia, fuente, licencia y genera el badge transparente de pantalla.
        """
        title = str(candidate_meta.get("title", "")).strip()
        url = str(candidate_meta.get("url", candidate_meta.get("page_url", ""))).strip()
        desc = str(candidate_meta.get("description", candidate_meta.get("extract", ""))).strip()
        source_domain = str(candidate_meta.get("source", candidate_meta.get("domain", ""))).lower()
        width = int(candidate_meta.get("width", 0))
        height = int(candidate_meta.get("height", 0))

        combo_text = f"{title} {desc} {url}".lower()

        # Descarte 1: Banco de stock con marcas de agua comerciales o render stock
        if any(bad in combo_text or bad in source_domain for bad in cls.WATERMARK_BLOCKLIST):
            return ResourceProvenance(
                source_url=url,
                source_name=source_domain or "Stock Comercial No Válido",
                verified_match=False,
                context_note="Descartado: banco de stock con marcas de agua o derechos incompatibles.",
                attribution_badge="DESCARTADO",
                relevance_score=0.1,
            )

        # Descarte 2: Calidad insuficiente si las dimensiones son conocidas
        if width > 0 and height > 0:
            if width < 800 or height < 450:
                return ResourceProvenance(
                    source_url=url,
                    source_name=source_domain or "Web",
                    verified_match=False,
                    context_note="Descartado: resolución por debajo de estándar mínimo HD (800x450).",
                    attribution_badge="BAJA RESOLUCIÓN",
                    relevance_score=0.2,
                )

        # Determinar Naturaleza Visual (Real, Ilustrativo, Reconstrucción 3D, IA)
        is_ai_generated = any(k in combo_text for k in ("midjourney", "stable diffusion", "dall-e", "ai generated", "generada por ia", "ai art"))
        is_3d_render = any(k in combo_text for k in ("3d render", "cgi", "simulación", "simulation", "reconstruction", "reconstrucción 3d", "recreación"))
        is_wikimedia = "commons.wikimedia" in url.lower() or "wikipedia" in url.lower() or "wikimedia" in source_domain
        is_nasa_gov = any(k in url.lower() for k in ("nasa.gov", ".gov", "esa.int", "cern.ch", "un.org"))

        if is_ai_generated:
            visual_nature = VisualNature.GENERADO_IA
            badge = "REPRESENTACIÓN DIGITAL / IA"
            license_str = "Sintético libre"
        elif is_3d_render:
            visual_nature = VisualNature.RECONSTRUCCION
            badge = "SIMULACIÓN / RECONSTRUCCIÓN 3D"
            license_str = "CGI Editorial"
        elif is_wikimedia or is_nasa_gov:
            visual_nature = VisualNature.DOCUMENTAL_REAL
            badge = "ARCHIVO HISTÓRICO VERIFICADO"
            license_str = candidate_meta.get("license", "Dominio Público / CC BY-SA")
        else:
            visual_nature = VisualNature.ILUSTRATIVO
            badge = "IMAGEN DOCUMENTAL ILUSTRATIVA"
            license_str = "Uso Editorial / Libre"

        # Verificación de Fechas
        year_conflict = False
        date_recorded = str(candidate_meta.get("date", ""))
        if intent.year:
            # Si la narración habla de 1959, verificar si el recurso menciona años totalmente distintos
            cand_years = re.findall(r"\b(18\d\d|19\d\d|20[0-2]\d)\b", combo_text)
            if cand_years:
                if str(intent.year) in cand_years:
                    badge = f"ARCHIVO HISTÓRICO · {intent.year}"
                    date_recorded = str(intent.year)
                else:
                    # Conflicto severo de fecha si habla de otra época
                    if abs(int(cand_years[0]) - intent.year) > 10:
                        year_conflict = True
                        visual_nature = VisualNature.ILUSTRATIVO
                        badge = "REFERENCIA ILUSTRATIVA (ÉPOCA DISTINTA)"

        # Verificación de Correspondencia Semántica
        entity_words = [w.lower() for w in re.findall(r"\w+", intent.entity_name) if len(w) > 3]
        match_count = sum(1 for w in entity_words if w in combo_text)
        relevance = match_count / max(1, len(entity_words))

        # Determinar si se aprueba
        passed = (relevance >= 0.35 or is_wikimedia or is_nasa_gov) and not year_conflict

        source_display = "Wikimedia Commons" if is_wikimedia else ("NASA / Archivo Oficial" if is_nasa_gov else (source_domain or "Archivo Web"))

        return ResourceProvenance(
            source_url=url,
            source_name=source_display,
            license_type=license_str,
            author_or_institution=candidate_meta.get("artist", candidate_meta.get("author", source_display)),
            date_recorded=date_recorded or str(intent.year or ""),
            location_recorded=intent.location,
            visual_nature=visual_nature,
            attribution_badge=badge,
            context_note=title or desc[:80],
            verified_match=passed,
            relevance_score=round(relevance, 2),
        )

    # --------------------------------------------------------------------------
    # 9. Generación de Alternativas Visuales Honestas (cuando no hay material fiable)
    # --------------------------------------------------------------------------
    @classmethod
    async def render_honest_alternative(
        cls,
        intent: VisualIntent,
        out_path: Path,
        web_renderer: Any,
        duration: float,
        bg_image_path: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Produce una representación visual honesta, elegante y contextual:
        - Cifras -> Stat Counter con medidor dinámico
        - Lugares -> Mapa geopolítico táctico GeoIntel
        - Frases de impacto -> Rótulo animado cinético / Alert Banner
        - Comparaciones -> Versus Split A vs B
        - Conceptos complejos -> Tarjeta técnica interactiva Tech Card
        - Acontecimientos -> Vox Style Quote / Registro histórico
        """
        if not web_renderer:
            return None

        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Comparación A vs B
            if intent.intent_type == VisualIntentType.VERSUS_COMPARISON:
                side_a = intent.entity_name
                side_b = intent.secondary_entity or "Referencia"
                res = web_renderer.render_visual_template(
                    template_name="versus_split",
                    out_png=out_path,
                    params={
                        "side_a": side_a,
                        "side_b": side_b,
                        "stat_a": "",
                        "stat_b": "",
                        "tag": "COMPARATIVA DIRECTA",
                    },
                    variant="orange_noir",
                )
                if res and res.exists():
                    return {"type": "versus_split", "path": out_path, "badge": "COMPARATIVA VISUAL"}

            # 2. Cifra o Estadística Clave
            elif intent.intent_type == VisualIntentType.STAT_NUMBER and intent.stat_value:
                res = web_renderer.render_visual_template(
                    template_name="stat_counter",
                    out_png=out_path,
                    params={
                        "stat_value": intent.stat_value,
                        "stat_label": intent.stat_label or intent.entity_name,
                        "headline": intent.entity_name,
                        "tag": "MÉTRICA VERIFICADA",
                    },
                    variant="orange_noir",
                )
                if res and res.exists():
                    return {"type": "stat_counter", "path": out_path, "badge": "DATO ESTADÍSTICO"}

            # 3. Lugar Geográfico / Mapa
            elif intent.intent_type == VisualIntentType.GEO_LOCATION:
                res = web_renderer.render_geointel_map_to_image(
                    location_title=intent.entity_name,
                    country_name=intent.location or "ZONA DE ANÁLISIS",
                    out_png=out_path,
                    coordinates_str="COORDENADAS TÁCTICAS",
                    notes="Ubicación geográfica clave referenciada en la investigación.",
                    badge="RECONOCIMIENTO GEOGRÁFICO",
                )
                if res and res.exists():
                    return {"type": "map", "path": out_path, "badge": "MAPA TÁCTICO"}

            # 4. Frase de Impacto
            elif intent.intent_type == VisualIntentType.IMPACT_PHRASE:
                res = web_renderer.render_visual_template(
                    template_name="alert_banner",
                    out_png=out_path,
                    params={
                        "headline": intent.entity_name,
                        "body": intent.raw_sentence[:100],
                        "tag": "PUNTO DE RETENCIÓN",
                    },
                    variant="crimson_hazard",
                )
                if res and res.exists():
                    return {"type": "alert_banner", "path": out_path, "badge": "PUNTO CLAVE"}

            # 5. Concepto Técnico Complejo
            elif intent.intent_type == VisualIntentType.COMPLEX_CONCEPT:
                res = web_renderer.render_visual_template(
                    template_name="tech_card",
                    out_png=out_path,
                    params={
                        "title": intent.entity_name,
                        "subtitle": intent.raw_sentence[:90],
                    },
                    variant="cyber_cyan",
                )
                if res and res.exists():
                    return {"type": "tech_card", "path": out_path, "badge": "ANÁLISIS CONCEPTUAL"}

            # 6. Acontecimiento con Registro Histórico
            elif intent.intent_type == VisualIntentType.HISTORICAL_EVENT and intent.year:
                res = web_renderer.render_visual_template(
                    template_name="quote_evidence",
                    out_png=out_path,
                    params={
                        "quote_text": intent.raw_sentence[:120],
                        "source": f"Registro Oficial ({intent.year})",
                    },
                    variant="royal_gold",
                )
                if res and res.exists():
                    return {"type": "quote_evidence", "path": out_path, "badge": f"REGISTRO {intent.year}"}

            # 7. Fallback honesto: Bento Card con imagen de fondo si existe
            web_renderer.render_to_image(
                headline=intent.entity_name,
                out_png=out_path,
                stat_value=intent.stat_value or "DATOS CLAVE",
                stat_label=intent.stat_label or "Informe Oficial",
                body=intent.raw_sentence[:110],
                badge="SÍNTESIS VISUAL",
                source="Registro Documental",
                style="auto",
                image_path=bg_image_path,
            )
            if out_path.exists():
                return {"type": "bento", "path": out_path, "badge": "SÍNTESIS VISUAL"}

        except Exception as exc:
            print(f"[SmartMediaCurator] Fallback en alternativa visual: {exc}")

        return None

    # --------------------------------------------------------------------------
    # 10. Temporización Dinámica: Aparición y Retiro Oportuno
    # --------------------------------------------------------------------------
    @classmethod
    def calculate_smart_timing(
        cls,
        intent: VisualIntent,
        sentence_boundaries: List[Tuple[float, float, str]],
        scene_duration: float,
    ) -> Tuple[float, float]:
        """
        Calcula el momento exacto en que la afirmación se pronuncia (start_time)
        y la duración idónea para que el elemento se retire cuando deja de ser relevante:
        - Mínimo 2.5s, máximo 4.5s (nunca se congela toda la escena).
        - Sale suavemente antes de que acabe la escena.
        """
        start_t = 0.5
        found = False

        if sentence_boundaries and intent.trigger_words:
            trig_words = [w.lower() for w in intent.trigger_words if len(w) >= 2]
            for s_start, _s_end, s_txt in sentence_boundaries:
                low_s = s_txt.lower()
                if any(tw in low_s for tw in trig_words):
                    start_t = max(0.4, min(scene_duration - 2.5, round(s_start, 2)))
                    found = True
                    break

        # Duración concisa adaptada al tipo de elemento
        if intent.intent_type in (VisualIntentType.IMPACT_PHRASE, VisualIntentType.STAT_NUMBER):
            ideal_dur = 3.0
        elif intent.intent_type in (VisualIntentType.GEO_LOCATION, VisualIntentType.VERSUS_COMPARISON):
            ideal_dur = 4.0
        else:
            ideal_dur = 3.5

        # Garantizar que el elemento se retire al menos 0.6s antes de que termine la escena
        max_allowed_dur = max(2.0, scene_duration - start_t - 0.6)
        display_dur = min(ideal_dur, max_allowed_dur)

        return round(start_t, 2), round(display_dur, 2)

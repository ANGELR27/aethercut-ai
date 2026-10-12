"""
AI Remotion Dynamic Generator
Permite a modelos de IA (Gemini / NVIDIA NIM) generar y adaptar componentes React
en Remotion al vuelo según el guion y contenido de cada escena.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings
from core.llm import LLMClient
from core.remotion_engine import RemotionEngine

logger = logging.getLogger("aethercut.remotion_ai")


class AIStyleDirector:
    """Director de Estilo Audiovisual: define automáticamente la paleta de colores,
    tipografía y tono base del video según su temática y potencia."""

    PALETTES: Dict[str, Dict[str, str]] = {
        "cyber_cyan": {
            "name": "cyber_cyan",
            "primary": "#00E5FF",
            "accent": "#38BDF8",
            "bg": "#09121A",
            "card_theme": "cyber_cyan",
            "sub_style": "cyber_glow",
            "font_family": "Montserrat",
            "vibe": "Ciencia, astronomía, IA, tecnología y futuro",
        },
        "emerald_matrix": {
            "name": "emerald_matrix",
            "primary": "#00F5A0",
            "accent": "#10B981",
            "bg": "#0A130E",
            "card_theme": "emerald_matrix",
            "sub_style": "viral",
            "font_family": "Plus Jakarta Sans",
            "vibe": "Cripto, finanzas, productividad, crecimiento y negocios",
        },
        "crimson_hazard": {
            "name": "crimson_hazard",
            "primary": "#FF3366",
            "accent": "#EF4444",
            "bg": "#140A0E",
            "card_theme": "crimson_hazard",
            "sub_style": "hormozi",
            "font_family": "Segoe UI Black",
            "vibe": "Urgente, alertas, breaking news, impacto, polémica o peligro",
        },
        "royal_gold": {
            "name": "royal_gold",
            "primary": "#FFB703",
            "accent": "#F59E0B",
            "bg": "#141009",
            "card_theme": "royal_gold",
            "sub_style": "cinema",
            "font_family": "Playfair Display",
            "vibe": "Historia, misterio antiguo, cine, filosofía y prestigio",
        },
        "orange_noir": {
            "name": "orange_noir",
            "primary": "#FF9436",
            "accent": "#FFE14D",
            "bg": "#0C0D12",
            "card_theme": "orange_noir",
            "sub_style": "viral",
            "font_family": "Outfit",
            "vibe": "Divulgación de alto impacto, curiosidades, ciencia cotidiana y narrativa viral",
        },
        "frosted_white": {
            "name": "frosted_white",
            "primary": "#FFFFFF",
            "accent": "#94A3B8",
            "bg": "#12141C",
            "card_theme": "frosted_white",
            "sub_style": "minimal",
            "font_family": "Inter",
            "vibe": "Minimalista, diseño elegante, sobrio y documental frío",
        },
    }

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def determine_style(self, topic: str, style_mode: str = "divulgacion", extra_notes: str = "") -> Dict[str, Any]:
        """Analiza el tema y extrae la paleta, tipografía y estilo visual de forma inteligente."""
        t_low = (topic + " " + style_mode + " " + extra_notes).lower()

        detected_palette = "orange_noir"
        if any(w in t_low for w in ["nasa", "espacio", "telescopio", "astronom", "galaxia", "universo", "ia", "inteligencia artificial", "cyber", "robot", "quantum", "ciencia"]):
            detected_palette = "cyber_cyan"
        elif any(w in t_low for w in ["dinero", "cripto", "bitcoin", "millon", "finanz", "econom", "negocio", "inversi", "dolar", "empresa"]):
            detected_palette = "emerald_matrix"
        elif any(w in t_low for w in ["urgente", "alerta", "breaking", "guerra", "peligro", "escandalo", "crisis", "muerte", "amenaza"]):
            detected_palette = "crimson_hazard"
        elif any(w in t_low for w in ["historia", "antiguo", "arqueolog", "imperio", "siglo", "filosof", "arte", "misterio", "secreto"]):
            detected_palette = "royal_gold"
        elif any(w in t_low for w in ["minimal", "elegante", "documental sobrio", "blanco"]):
            detected_palette = "frosted_white"

        spec = dict(self.PALETTES[detected_palette])
        spec["topic"] = topic
        return spec


class AIRemotionGenerator:
    """Generador y orquestador de componentes React dinámicos para Remotion."""

    def __init__(self, remotion_engine: Optional[RemotionEngine] = None):
        self.remotion = remotion_engine or RemotionEngine()
        self.llm = LLMClient()
        self.style_director = AIStyleDirector(self.llm)

    def decide_overlay_for_scene(
        self,
        scene_name: str,
        speech_text: str,
        duration: float,
        vertical: bool = False,
        theme_spec: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Analiza el discurso de la escena para determinar si requiere un overlay animado
        de alto impacto (MetricCounter, VersusComparison o Callout) y genera sus props en React,
        utilizando la paleta de colores y tono definidos por el Director de Estilos.
        """
        prompt = f"""Eres el Director de Motion Graphics en Remotion (React + TypeScript).
Analiza el fragmento hablado de esta escena y determina si se beneficia de un gráfico animado clave en pantalla.

Información de la escena:
- Nombre: {scene_name}
- Duración: {duration:.1f}s
- Discurso hablado: "{speech_text}"
- Orientación: {"Vertical 9:16 (TikTok/Shorts)" if vertical else "Horizontal 16:9"}

Tipos de componentes disponibles en React:
1. "MetricCounter": Para cifras, estadísticas, porcentajes, montos económicos, años o récords (ej: "+250%", "$10M", "99%").
2. "VersusComparison": Para contrastes, mitos vs verdades, antes vs ahora, o dos bandos enfrentados.
3. null: Si la escena es puramente narrativa y los subtítulos bastan.

Responde ÚNICAMENTE con un objeto JSON sin formato markdown extra:
{{
  "should_render": true | false,
  "component": "MetricCounter" | "VersusComparison",
  "props": {{
    // Si es MetricCounter:
    // "title": "TITULO CORTO",
    // "fromValue": 0,
    // "toValue": 250,
    // "prefix": "+",
    // "suffix": "%",
    // "subtitle": "ACLARACIÓN CORTA"
    
    // Si es VersusComparison:
    // "tagA": "ANTES", "labelA": "TEXTO",
    // "tagB": "AHORA", "labelB": "TEXTO",
    // "category": "CATEGORIA"
  }}
}}
"""
        try:
            raw_resp = self.llm.generate(prompt, json_mode=True)
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_resp.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            if data.get("should_render") and data.get("component") in ("MetricCounter", "VersusComparison"):
                props = data.get("props", {})
                props["durationSec"] = round(min(duration, 3.8), 2)
                props["width"] = 1080 if vertical else 1920
                props["height"] = 1920 if vertical else 1080
                props["fps"] = 30
                props["vertical"] = vertical
                # Inyectar paleta cromática del Director de Estilos
                if theme_spec:
                    props["theme"] = {
                        "primary": theme_spec.get("primary", "#00E5FF"),
                        "accent": theme_spec.get("accent", "#FFE14D"),
                    }
                data["props"] = props
                return data
        except Exception as e:
            logger.warning("[AIRemotionGenerator] Fallback en decisión IA: %s", e)
        return None

    async def render_ai_overlay(
        self,
        scene_name: str,
        speech_text: str,
        duration: float,
        out_dir: Path,
        vertical: bool = False,
        theme_spec: Optional[Dict[str, Any]] = None,
    ) -> Optional[Path]:
        """Ejecuta la decisión de la IA y renderiza el componente React en Remotion con alpha."""
        if not self.remotion.available():
            return None

        spec = self.decide_overlay_for_scene(scene_name, speech_text, duration, vertical, theme_spec=theme_spec)
        if not spec:
            return None

        comp_id = spec["component"]
        props = spec["props"]
        logger.info("[AIRemotionGenerator] ⚛️ Renderizando overlay React Remotion '%s' con paleta %s para '%s'",
                    comp_id, props.get("theme", {}), scene_name)
        return await self.remotion.render_overlay(comp_id, props, out_dir)


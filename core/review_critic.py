"""Auditor y Revisor Crítico Autónomo con GLM-5.3-flash.

GLM-5.3-flash audita y optimiza a velocidad ultra-rápida:
1. El guión y las escenas (coherencia, dicción para TTS, hooks, datos falsos o clichés).
2. Los términos visuales y beats (especificidad en inglés, eliminación de términos genéricos).
3. Los subtítulos dinámicos (ortografía, puntuación, longitud de líneas para no saturar la pantalla).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from core.llm import safe_log
from core.multiagent.models import get_implementer_model


class FlashContentReviewer:
    """Inspector de calidad y optimizador automático con GLM-5.3-flash."""

    def __init__(self):
        try:
            self.model = get_implementer_model()
            self.available = bool(self.model.api_key)
        except Exception as e:
            safe_log(f"[FlashReviewer] No disponible: {e}")
            self.model = None
            self.available = False

    def review_and_optimize_plan(self, plan_dict: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """Audita el plan del director: pule la locución TTS, afina queries visuales y corrige incoherencias."""
        if not self.available or not self.model:
            safe_log("[FlashReviewer] GLM-5.3-flash no configurado, manteniendo plan original.")
            return plan_dict

        scenes = plan_dict.get("scenes", [])
        if not scenes:
            return plan_dict

        safe_log(f"[FlashReviewer] ⚡ GLM-5.3-flash auditando guión y recursos de {len(scenes)} escenas...")

        prompt_review = f"""Eres el Auditor y Editor Jefe de Producción Audiovisual (GLM-5.3-flash).
Tu objetivo es elevar la calidad de este plan de video sobre el tema: "{topic}".

REVISA Y OPTIMIZA CADA ESCENA:
1. "speech" (Locución para síntesis de voz):
   - Elimina muletillas o frases acartonadas.
   - Corrige puntuación y ritmo para que la voz neuronal suene natural, fluida y sin frenazos.
   - Si una escena tiene números o siglas complejas, escríbelas en formato fonético fácil para locución (ej: "diez por ciento" en vez de "10%", "la N-A-S-A" en vez de "NASA" si conviene).
2. "visual_query" y "visual_query2":
   - Asegura que estén en inglés, sean HIPER-ESPECÍFICOS (evita términos vagos como 'abstract 4k' o 'cinematic background').
   - Deben reflejar exactamente la entidad, lugar o acción concreta mencionada en ese segundo.
3. "visual_beats":
   - Comprueba que el 'trigger' sea una subcadena literal que sí existe dentro del 'speech'. Si no coincide, ajústalo.

PLAN ACTUAL:
{json.dumps(scenes, ensure_ascii=False, indent=2)}

RESPONDE EXCLUSIVAMENTE CON UN JSON VÁLIDO conteniendo el array de escenas optimizadas:
{{
  "optimized_scenes": [ ... ]
}}
"""

        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    self.model.generate,
                    system_prompt="Eres un auditor editorial experto. Devuelve únicamente JSON válido.",
                    user_prompt=prompt_review,
                    temperature=0.2,
                    json_mode=True,
                )
                raw = fut.result(timeout=12.0)
            cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            opt_scenes = data.get("optimized_scenes")
            if opt_scenes and isinstance(opt_scenes, list) and len(opt_scenes) == len(scenes):
                safe_log(f"[FlashReviewer] ✓ {len(opt_scenes)} escenas auditadas y optimizadas exitosamente por GLM-5.3-flash.")
                plan_dict["scenes"] = opt_scenes
                plan_dict["reviewed_by"] = "z-ai/glm-5.3-flash"
            else:
                safe_log("[FlashReviewer] La respuesta no coincidió en número de escenas, conservando plan original.")
        except concurrent.futures.TimeoutError:
            safe_log("[FlashReviewer] Timeout de 12s alcanzado, continuando con el plan actual.")
        except Exception as err:
            safe_log(f"[FlashReviewer] Fallback suave: {err}")

        return plan_dict

    def review_captions(self, captions_text: List[str]) -> List[str]:
        """Pule la ortografía y quiebres de línea de los subtítulos."""
        if not self.available or not self.model or not captions_text:
            return captions_text

        prompt = f"""Corrige y pule estos textos de subtítulos en español.
Mantén las mismas líneas en el mismo orden exacto.
Corrige tildes, signos de puntuación y capitalización adecuada.
Lista:
{json.dumps(captions_text, ensure_ascii=False)}

Devuelve solo JSON:
{{
  "polished_captions": [ ... ]
}}
"""
        try:
            raw = self.model.generate(
                system_prompt="Pule subtítulos. Devuelve solo JSON válido.",
                user_prompt=prompt,
                temperature=0.1,
                json_mode=True,
            )
            cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            polished = data.get("polished_captions")
            if polished and len(polished) == len(captions_text):
                return polished
        except Exception:
            pass

        return captions_text

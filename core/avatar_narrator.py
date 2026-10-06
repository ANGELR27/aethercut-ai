"""Módulo de narración y voz con Inteligencia Artificial para el avatar asistente (KAI).

Combina modelos de lenguaje de última generación (Gemini) para redactar intervenciones
argumentadas, hiper-humanas y dinámicas, con tecnología Microsoft Edge Neural TTS (edge-tts),
100% gratuita, ilimitada y de código abierto para la síntesis de voz broadcast en español.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Optional, Tuple

import edge_tts

from core.models import InfoCard

DEFAULT_VOICE = "es-CO-GonzaloNeural"  # Voz ultra-natural, conversacional y neutra (sin tono robótico)
VOICE_LATINO = "es-US-AlonsoNeural"    # Voz neutra estilo locutor internacional
VOICE_FEMALE = "es-MX-DaliaNeural"     # Voz femenina cálida y amigable
VOICE_SPAIN = "es-ES-AlvaroNeural"      # Voz estilo divulgación tecnológica España


class AvatarNarrator:
    """Generador de diálogos hablados con IA y síntesis neural de voz para el avatar."""

    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice

    @staticmethod
    def craft_dialogue(card: InfoCard) -> str:
        """Redacta una intervención conversacional, humana y empática de respaldo."""
        verdict = (card.verdict or "").lower()
        headline = (card.headline or "").strip()
        clean_headline = re.sub(r'[\.\,\;]+$', '', headline)

        if verdict == "contradicted":
            correction = (card.corrected_value or card.correction or "").strip()
            if correction:
                corr_words = correction.split()[:16]
                corr_short = " ".join(corr_words).rstrip(".")
                return f"Bueno, mira: lo que acaba de plantear suena lógico, pero en realidad {corr_short}."
            return "Ojo con esa conclusión: los registros oficiales no coinciden con lo que acaba de decir."

        if card.stat_value:
            stat = card.stat_value.strip()
            return f"Un dato clave aquí: la cifra real confirmada es {stat}, cambiando bastante el panorama."

        if verdict == "supported":
            kind = (card.kind or "dato").lower()
            if kind in ("ley", "normativa"):
                return f"Punto clave y totalmente acertado: {clean_headline}, plenamente respaldada por la ley vigente."
            return f"Exacto, punto clave aquí: {clean_headline}, tal como confirman los registros oficiales."

        if verdict == "insufficient":
            return "Ojo con esa afirmación: no encontramos datos oficiales concluyentes que respalden lo que acaba de decir."

        return f"Un apunte rápido sobre {clean_headline}: los datos confirman este punto."

    async def craft_dialogue_with_ai(
        self,
        card: InfoCard,
        surrounding_context: str = "",
        llm: Optional[Any] = None
    ) -> str:
        """Formula una intervención argumentada, hiper-humana, con datos y conversacional con Gemini."""
        prompt = f"""Eres KAI, el copiloto y analista de video inteligente en vivo. Eres perspicaz, carismático y hablas de forma 100% humana, natural y conversacional (como un analista o podcaster experto que interviene en la conversación en vivo).

SITUACIÓN EN EL VIDEO:
El orador en pantalla está exponiendo o cerrando el siguiente argumento:
"{card.claim}"

Subtítulos/contexto exacto de lo que se acaba de hablar en el video:
"{surrounding_context[:300] if surrounding_context else 'Debate en video'}"

EVIDENCIA Y DATOS TÉCNICOS VERIFICADOS:
- Tema / Entidad: {card.headline}
- Muestreo, hechos o explicación: {card.body or card.note or 'Registro y marco oficial'}
- Cifra o corrección clave: {card.corrected_value or card.stat_value or card.correction or 'Respaldado por datos oficiales'}
- Veredicto de los datos: {card.verdict}

TU MISIÓN:
Formular una intervención hablada CORTA, ARGUMENTADA, MUY HUMANA Y DINÁMICA (entre 16 y 28 palabras, 1 o 2 oraciones) donde intervengas comentando directamente lo que la persona acaba de decir, explicando con datos, muestreos o matices para aclarar el punto antes de que se cierre el argumento.

PAUTAS DE ESTILO (CRÍTICO):
1. Suena 100% humano y fluido, refiriéndote de manera directa a la persona o argumento en pantalla. Por ejemplo:
   - "Bueno, mira: lo que acaba de plantear esta persona tiene algo de lógica, pero no hay que mirarlo simplemente desde ese lado; si vemos el muestreo oficial..."
   - "Ojo con ese argumento: suena convincente a primera vista, pero si nos vamos a los datos y estadísticas reales..."
   - "Exacto, un punto clave aquí: aunque suene polémico, los registros y muestreos demuestran claramente que..."
   - "Cuidado con esa conclusión: parece un debate cerrado, pero falta un dato clave..."
2. Sé intervencionista, ágil y fundamentado con datos o cifras reales.
3. Máximo 28 palabras. Evita sonar como un locutor acartonado o un bot de lectura de tarjetas.
4. Devuelve ÚNICAMENTE la frase exacta que KAI pronunciará en voz alta, sin comillas, sin prefijos ni explicaciones."""

        try:
            from core.llm import LLMClient
            client = llm or LLMClient()
            loop = asyncio.get_running_loop()
            raw_text = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: client.generate(prompt, max_models=2)),
                timeout=10.0
            )
            cleaned = re.sub(r'^["\'«»]+|["\'«»]+$', '', raw_text.strip())
            # Validar que no devolvió texto vacío o error genérico
            if len(cleaned.split()) >= 4 and not cleaned.startswith("{"):
                return cleaned
        except Exception as exc:
            print(f"[AvatarNarrator] Fallback a redacción local para {card.card_id}: {exc}")

        return self.craft_dialogue(card)

    async def synthesize(self, text: str, out_path: Path, voice: Optional[str] = None) -> Tuple[Path, float]:
        """Genera el archivo de audio MP3 y devuelve su duración exacta en segundos."""
        chosen_voice = voice or self.voice
        out_path.parent.mkdir(parents=True, exist_ok=True)

        communicate = edge_tts.Communicate(text, chosen_voice, rate="+0%")
        await communicate.save(str(out_path))

        duration = self.get_audio_duration(out_path)
        return out_path, duration

    @staticmethod
    def get_audio_duration(path: Path) -> float:
        """Lee la duración exacta del audio usando ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json", str(path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            data = json.loads(res.stdout)
            return float(data["format"]["duration"])
        except Exception as exc:
            print(f"[AvatarNarrator] No se pudo leer duración de {path}: {exc}")
            return 3.5

"""Módulo de narración y voz con Inteligencia Artificial para el avatar asistente.

Utiliza tecnología Microsoft Edge Neural TTS (edge-tts), 100% gratuita, ilimitada
y de código abierto, para generar intervenciones habladas en español con calidad
de estudio broadcast sin requerir claves de API ni consumir cuotas de pago.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import edge_tts

from core.models import InfoCard

DEFAULT_VOICE = "es-CO-GonzaloNeural"  # Voz ultra-natural, conversacional y neutra (sin tono robótico)
VOICE_LATINO = "es-US-AlonsoNeural"    # Voz neutra estilo locutor internacional
VOICE_FEMALE = "es-MX-DaliaNeural"     # Voz femenina cálida y amigable
VOICE_SPAIN = "es-ES-AlvaroNeural"      # Voz estilo divulgación tecnológica España


class AvatarNarrator:
    """Generador de diálogos hablados y síntesis neural de voz para el avatar."""

    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice

    @staticmethod
    def craft_dialogue(card: InfoCard) -> str:
        """Redacta una intervención concisa, dinámica y natural (10-20 palabras)."""
        verdict = (card.verdict or "").lower()
        headline = (card.headline or "").strip()
        
        # Limpiar puntuación excesiva
        clean_headline = re.sub(r'[\.\,\;]+$', '', headline)

        if verdict == "contradicted":
            correction = (card.corrected_value or card.correction or "").strip()
            if correction:
                # Acortar a máximo 18 palabras
                corr_words = correction.split()[:18]
                corr_short = " ".join(corr_words).rstrip(".")
                return f"¡Ojo con esto! En realidad, {corr_short}."
            return f"Atención: los datos oficiales no coinciden con esta afirmación."

        if card.stat_value:
            stat = card.stat_value.strip()
            return f"Dato clave confirmado: la cifra exacta es {stat}. {clean_headline}."

        if verdict == "supported":
            kind = (card.kind or "dato").lower()
            if kind in ("ley", "normativa"):
                return f"Normativa confirmada: {clean_headline}, plenamente respaldada por fuentes oficiales."
            if kind in ("persona", "organizacion", "organización"):
                return f"Referencia confirmada: {clean_headline}."
            return f"Dato verificado: {clean_headline}."

        if verdict == "insufficient":
            return f"Un detalle importante: no hay evidencia concluyente sobre este dato en registros oficiales."

        return f"Apunte clave sobre {clean_headline}."

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

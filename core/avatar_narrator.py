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
        """Redacta una intervención amigable, chistosa, irónica y enriquecedora con datos de peso."""
        verdict = (card.verdict or "").lower()
        headline = (card.headline or "").strip()
        clean_headline = re.sub(r'[\.\,\;]+$', '', headline)

        # 1. Contradicción / Dato falso
        if verdict == "contradicted":
            correction = (card.corrected_value or card.correction or card.note or "").strip()
            if correction:
                corr_clean = re.sub(r'[\.\,]+$', '', correction)
                templates = [
                    f"¡Ojo amiguito! Se te acaba de escapar un dato que no es tan cierto: sobre {clean_headline}, los registros oficiales demuestran que {corr_clean}. ¡Dato mata relato!",
                    f"¡Ojo amiguito, suena poético el discurso, pero la realidad tiene otros planes! Para {clean_headline}, los datos confirman que {corr_clean}. ¡Se nos cayó la teoría en vivo!",
                    f"¡Ojo ahí, frenemos los caballos un segundo! Venía invicto el argumento, pero la evidencia oficial prueba que {corr_clean}. ¡Dato mata relato!",
                ]
                idx = abs(hash(card.card_id or clean_headline)) % len(templates)
                return templates[idx]
            return f"¡Ojo amiguito! Se te escapó un dato que no es tan cierto: sobre {clean_headline}, los registros oficiales desmienten totalmente esa conclusión. ¡Dato mata relato!"

        # 2. Cifra o estadística clave
        if card.stat_value:
            stat = card.stat_value.strip()
            detail = card.body or card.claim
            detail_short = " ".join(detail.split()[:14]).rstrip(".,;") if detail else ""
            templates = [
                f"¡Paren las rotativas un segundo! El número real que define esto es {stat}: {detail_short}. Un dato demoledor que cambia toda la película.",
                f"Ojo con el cálculo ahí: las métricas oficiales confirman {stat} para {clean_headline}. Cifra mata discurso, mi gente.",
            ]
            idx = abs(hash(card.card_id or stat)) % len(templates)
            return templates[idx]

        # 3. Confirmado / Ley / Ciencia
        if verdict == "supported":
            kind = (card.kind or "dato").lower()
            if kind in ("ley", "normativa", "articulo"):
                return f"¡Bien ahí! Por fin alguien que le atina a las normas: {clean_headline} está 100% blindado por el marco legal vigente. Punto para el expositor."
            return f"¡Exacto amigazo! Punto clavado y con sustento: los estudios técnicos y registros oficiales respaldan plenamente {clean_headline}. Así da gusto debatir."

        # 4. Evidencia insuficiente / mito sin sustento
        if verdict == "insufficient":
            templates = [
                f"¡Ojo amiguito! Suena muy convincente en el micrófono, pero no hay ni un solo estudio ni registro oficial que sustente {clean_headline}. Pura fe y cero evidencia.",
                f"Mucho entusiasmo en esa frase, pero cuidado: ni en los reportes oficiales encontramos sustento para semejante afirmación. Quedó en jaque la teoría.",
            ]
            idx = abs(hash(card.card_id or clean_headline)) % len(templates)
            return templates[idx]

        return f"¡Un apunte clave ahí, mi gente! Sobre {clean_headline}, los datos y análisis técnicos confirman la jugada. Seguimos atentos."

    async def craft_dialogue_with_ai(
        self,
        card: InfoCard,
        surrounding_context: str = "",
        llm: Optional[Any] = None
    ) -> str:
        """Formula una intervención amigable, chistosa, irónica y cargada de datos increíbles con Gemini."""
        prompt = f"""Eres KAI, el copiloto y analista de video en vivo. Eres muy carismático, súper amigable, chistoso, con una chispa de sana ironía y picardía (como un podcaster o streamer divulgador brillante que interviene en vivo con mucho humor y onda).

TU SELLO DISTINTIVO:
No te limitas a decir "esto es falso" o "la ley dice". Tu especialidad es soltar DATOS INCREÍBLES, enriquecedores y de alto impacto (citas a entidades de peso como la NASA, OIT, tribunales supremos, estudios científicos, comparativas internacionales o normas exactas) que dejen al espectador diciendo: "¡Wow, qué tremendo dato!".

SITUACIÓN EN EL VIDEO:
El orador en pantalla acaba de decir:
"{card.claim}"

Contexto inmediato de lo que se venía hablando:
"{surrounding_context[:300] if surrounding_context else 'Debate en video'}"

EVIDENCIA Y DATOS TÉCNICOS VERIFICADOS:
- Tema / Entidad: {card.headline}
- Muestreo, hechos o explicación: {card.body or card.note or 'Marco y registros oficiales'}
- Cifra o corrección clave: {card.corrected_value or card.stat_value or card.correction or 'Respaldado por datos oficiales'}
- Veredicto de los datos: {card.verdict}

TU MISIÓN:
Crear una intervención hablada CORTA, AMIGABLE, CHISTOSA, IRÓNICA Y MUY ENRIQUECEDORA (entre 20 y 35 palabras, 1 o 2 oraciones).

ESTRUCTURA OBLIGATORIA (CON CHISPA Y JUEGUITO):
1. GANCHO IRÓNICO O AMIGABLE (humor cómplice):
   - "¡Ojo amiguito! Se te acaba de escapar un dato que no es tan cierto..."
   - "Suena poético el discurso, pero la realidad y los números tienen otros planes..."
   - "¡Paren las rotativas un segundo! Venía invicto el argumento hasta que revisamos los datos..."
   - "Mucho entusiasmo en esa frase, pero cuidado: los números acaban de dejar el punto en jaque..."
2. EL DATO INCREÍBLE / ENRIQUECEDOR:
   - Introduce un dato contundente, una cifra reveladora o una fuente de peso que sustente el punto (ej. citar estudios técnicos, la NASA, organismos oficiales, el Código Penal, muestreos internacionales o la cifra exacta).
3. REMATE CON JUEGUITO / PUNTADA FINAL:
   - "¡Dato mata relato, mi gente!"
   - "Así que mejor chequear la fuente antes de prometer tanto."
   - "¡Se nos cayó la teoría en vivo!"
   - "Punto para la ciencia y el rigor."

REGLAS ESTRICTAS:
- No seas acartonado, formal ni aburrido. Usa lenguaje fresco, amigable y con picardía.
- Máximo 35 palabras.
- Devuelve ÚNICAMENTE la frase exacta que KAI dirá en voz alta, sin comillas, sin explicaciones ni prefijos."""

        try:
            from core.llm import LLMClient
            client = llm or LLMClient()
            loop = asyncio.get_running_loop()
            raw_text = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: client.generate(prompt, max_models=2)),
                timeout=15.0
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

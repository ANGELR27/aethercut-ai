import re
import subprocess
import threading
from pathlib import Path
from typing import Iterable, List, Optional

from core.models import CaptionItem

_MODEL = None
_LOCK = threading.Lock()

PROFANITY = {"mierda", "puta", "puto", "carajo", "joder", "coño", "culo", "suicidio", "muerte", "sangre", "asesinato", "matar", "estúpido", "pendejo", "cabrón"}


def _model(size: str = "base"):
    global _MODEL
    with _LOCK:
        if _MODEL is None:
            from faster_whisper import WhisperModel
            _MODEL = WhisperModel(size, device="cpu", compute_type="int8")
        return _MODEL


class WhisperTranscriber:
    """
    Transcripción local con faster-whisper y marcas de tiempo POR PALABRA.
    Se transcribe el video YA RECORTADO, así los subtítulos quedan sincronizados sin remapeos.
    """

    def __init__(self, language: str = "es", max_words: int = 6, max_dur: float = 2.6):
        self.language = language
        self.max_words = max_words
        self.max_dur = max_dur

    def _extract_audio(self, video: Path) -> Path:
        wav = video.with_suffix(".16k.wav")
        subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                       capture_output=True, check=True)
        return wav

    def transcribe(self, video: Path, highlight_terms: Iterable[str] = ()) -> List[CaptionItem]:
        wav = self._extract_audio(video)
        try:
            segments, _info = _model().transcribe(
                str(wav), language=self.language, word_timestamps=True,
                vad_filter=True, beam_size=1, condition_on_previous_text=False,
            )
            words = [w for seg in segments for w in (seg.words or []) if w.word.strip()]
        finally:
            wav.unlink(missing_ok=True)

        terms = {t.lower() for t in highlight_terms if t and len(t) > 3}
        captions: List[CaptionItem] = []
        chunk: list = []
        
        # Estado para Diarización simulada
        speaker_state = {"id": 1, "last_end": 0.0}

        def flush():
            if not chunk:
                return
            
            # Diarización: si hay pausa > 0.8s, asumimos cambio de locutor
            if chunk[0].start - speaker_state["last_end"] > 0.8:
                speaker_state["id"] = 2 if speaker_state["id"] == 1 else 1
                
            text = " ".join(w.word.strip() for w in chunk)
            hl = [w.word.strip(" .,;:!?¡¿\"'") for w in chunk
                  if w.word.strip(" .,;:!?¡¿\"'").lower() in terms]
                  
            # Detección de censura
            cw = [w.word.strip(" .,;:!?¡¿\"'") for w in chunk
                  if w.word.strip(" .,;:!?¡¿\"'").lower() in PROFANITY]

            captions.append(CaptionItem(
                start_sec=round(chunk[0].start, 3),
                end_sec=round(max(chunk[-1].end, chunk[0].start + 0.3), 3),
                text=text, 
                highlight_words=hl[:2],
                speaker_id=speaker_state["id"],
                censor_words=cw
            ))
            speaker_state["last_end"] = chunk[-1].end
            chunk.clear()

        for w in words:
            if chunk and (len(chunk) >= self.max_words or w.end - chunk[0].start > self.max_dur
                          or w.start - chunk[-1].end > 0.6):
                flush()
            chunk.append(w)
            if re.search(r"[.!?]$", w.word.strip()):
                flush()
        flush()
        return captions


def highlight_terms_from_plan(plan) -> List[str]:
    """Palabras a resaltar: las que Gemini marcó + palabras de los titulares de las tarjetas."""
    terms = set()
    for c in plan.captions:
        terms.update(c.highlight_words)
    for card in plan.info_cards:
        terms.update(w for w in re.findall(r"\w+", card.headline) if len(w) > 4)
    return list(terms)

import time
from pathlib import Path
from typing import Callable, Optional

from google.genai import types

from config.settings import settings
from core.llm import LLMClient, safe_log
from core.models import VideoEditingPlan
from core.prompt_templates import build_editor_prompt
from utils.json_validator import JSONValidator, JSONParsingError

__all__ = ["GeminiVideoAnalyzer", "safe_log"]


class GeminiVideoAnalyzer:
    """
    Sube el video a la File API de Gemini y obtiene el plan de edición estructurado (JSON validado).
    Usa LLMClient: reintentos con espera y modelos de respaldo ante 503/429.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None,
                 llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient(api_key=api_key, primary_model=model_name)
        self.client = self.llm.client

    def _upload_and_wait(self, file_path: Path, progress: Optional[Callable[[str], None]] = None):
        if not file_path.exists():
            raise FileNotFoundError(f"El archivo de video no existe en: {file_path}")

        say = progress or (lambda _m: None)
        safe_log(f"[GeminiAnalyzer] Subiendo {file_path.name}...")
        say("Subiendo el video a Gemini...")
        uploaded = self.client.files.upload(file=str(file_path))

        waited = 0
        while uploaded.state == types.FileState.PROCESSING:
            time.sleep(4)
            waited += 4
            say(f"Gemini está procesando el video ({waited}s)...")
            uploaded = self.client.files.get(name=uploaded.name)
            if waited > 1200:
                raise TimeoutError("Gemini tardó más de 20 minutos procesando el video.")

        if uploaded.state == types.FileState.FAILED:
            raise RuntimeError(f"Gemini no pudo procesar el video: {uploaded.error}")
        safe_log(f"[GeminiAnalyzer] Video listo ({uploaded.state}).")
        return uploaded

    def analyze_video(
        self,
        video_path: Path,
        silence_threshold: Optional[float] = None,
        max_cards: int = 8,
        progress: Optional[Callable[[str], None]] = None,
        transcript: str = None,
    ) -> VideoEditingPlan:
        threshold = silence_threshold or settings.MAX_SILENCE_DURATION_SEC
        uploaded = None
        try:
            uploaded = self._upload_and_wait(video_path, progress)
            if progress:
                progress("Gemini está analizando el contenido del video...")

            prompt = build_editor_prompt(silence_threshold=threshold, max_cards=max_cards, transcript=transcript)
            raw = self.llm.generate([uploaded, prompt], json_mode=True)
            safe_log(f"[GeminiAnalyzer] Respuesta recibida de {self.llm.last_model_used}. Validando JSON...")

            plan = JSONValidator.validate_editing_plan(raw)
            safe_log(
                f"[GeminiAnalyzer] Plan: {len(plan.timeline)} segmentos, {len(plan.b_rolls)} B-Rolls, "
                f"{len(plan.info_cards)} datos a verificar, {len(plan.highlights)} clips cortos."
            )
            return plan
        except JSONParsingError as exc:
            safe_log(f"[GeminiAnalyzer] JSON inválido de Gemini: {exc}")
            raise
        finally:
            if uploaded:
                try:
                    self.client.files.delete(name=uploaded.name)
                except Exception as exc:
                    safe_log(f"[GeminiAnalyzer] No se pudo borrar el archivo remoto: {exc}")

import sys
import time
from typing import Any, List, Optional

from google import genai
from google.genai import types

from config.settings import settings

# Modelos de respaldo actualizados (Gemini 1.5 y 2.5 fueron deprecados).
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]


def safe_log(msg: str) -> None:
    """Imprime sin romper la consola de Windows con emojis u otros caracteres Unicode."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


import itertools
import threading

class LLMClient:
    """
    Cliente de Gemini con reintentos con espera, cadena de modelos de respaldo,
    y ROTACIÓN DE API KEYS para saltarse los límites gratuitos (Rate Limit 429).
    """
    _key_cycle = None
    _key_lock = threading.Lock()

    def __init__(self, api_key: Optional[str] = None, primary_model: Optional[str] = None):
        raw_keys = api_key or settings.GEMINI_API_KEY
        if not raw_keys or raw_keys == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY no configurada. Defínela en el archivo .env")
        
        # Split by comma for multiple keys
        self.api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        
        with LLMClient._key_lock:
            if LLMClient._key_cycle is None:
                LLMClient._key_cycle = itertools.cycle(self.api_keys)
        
        # We don't initialize a single client, we will initialize it per request 
        # or grab the next one to distribute the load.
        
        primary = primary_model or settings.GEMINI_MODEL or "gemini-3.8-flash"
        self.models: List[str] = [primary] + [m for m in FALLBACK_MODELS if m != primary]
        self.last_model_used: Optional[str] = None
        
    def _get_next_client(self):
        with LLMClient._key_lock:
            next_key = next(LLMClient._key_cycle)
        return genai.Client(api_key=next_key)
        
    @property
    def client(self):
        return self._get_next_client()

    @staticmethod
    def _status_of(exc: Exception) -> Optional[int]:
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if isinstance(code, int):
            return code
        text = str(exc)
        for token in ("503", "429", "500", "404", "400", "401", "403"):
            if text.startswith(token):
                return int(token)
        return None

    def generate(self, contents: Any, json_mode: bool = False, attempts_per_model: int = 5, use_search: bool = False) -> str:
        config = types.GenerateContentConfig(
            response_mime_type="application/json" if json_mode else None,
            tools=[{"google_search": {}}] if use_search else None
        )
        last_exc: Optional[Exception] = None

        for model in self.models:
            for attempt in range(1, attempts_per_model + 1):
                try:
                    client = self._get_next_client()
                    response = client.models.generate_content(model=model, contents=contents, config=config)
                    text = response.text
                    if not text:
                        raise ValueError("respuesta vacía")
                    self.last_model_used = model
                    return text
                except Exception as exc:
                    last_exc = exc
                    status = self._status_of(exc)
                    safe_log(f"[LLM] {model} intento {attempt}/{attempts_per_model} falló ({status or 'error'}): {str(exc)[:110]}")
                    if status in (404, 400):
                        break  # el modelo no existe o la petición es inválida para este modelo
                    if status in (401, 403):
                        continue # La llave actual falló, probar inmediatamente con la siguiente
                    time.sleep(2 * attempt)
        raise RuntimeError(f"Ningún modelo de Gemini respondió. Último error: {last_exc}")

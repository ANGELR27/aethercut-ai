import re
import sys
import time
from typing import Any, Callable, List, Optional

from google import genai
from google.genai import types

from config.settings import settings
from cancellation import CancellationRequested

# El orden se ha comprobado contra los proyectos configurados. Empezamos por el
# modelo que respondió y conservamos los demás para recuperarnos de una caída.
# 3.8 agotó el tiempo incluso con una consulta mínima durante la comprobación
# del 2026-10-05. Se excluye del camino crítico para no atascar cada proyecto.
FALLBACK_MODELS = ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.6-flash"]


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
    y rotación entre claves para repartir solicitudes. Las claves no eliminan
    cuotas: Gemini las aplica por proyecto.
    """
    # Una petición multimodal sana responde antes de este límite. Si el modelo
    # queda en espera, se intenta 3.7 y luego otro proyecto en lugar de mostrar
    # una edición aparentemente congelada durante varios minutos.
    RESPONSE_TIMEOUT_MS = 35_000
    UPLOAD_TIMEOUT_MS = 180_000
    REQUEST_DEADLINE_SEC = 50
    PROJECT_FAILOVER_STATUSES = {401, 403, 408, 429, 500, 502, 503, 504}
    _key_cycles = {}
    _key_lock = threading.Lock()

    def __init__(self, api_key: Optional[str] = None, primary_model: Optional[str] = None):
        raw_keys = api_key or settings.GEMINI_API_KEY
        if not raw_keys or raw_keys == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY no configurada. Defínela en el archivo .env")
        
        # Split by comma for multiple keys
        self.api_keys = list(dict.fromkeys(k.strip() for k in raw_keys.split(",") if k.strip()))
        
        self._pool_id = tuple(self.api_keys)
        with LLMClient._key_lock:
            if self._pool_id not in LLMClient._key_cycles:
                LLMClient._key_cycles[self._pool_id] = itertools.cycle(self.api_keys)
        
        # We don't initialize a single client, we will initialize it per request 
        # or grab the next one to distribute the load.
        
        primary = primary_model or settings.GEMINI_MODEL or "gemini-3.6-flash"
        self.models: List[str] = [primary] + [m for m in FALLBACK_MODELS if m != primary]
        self.last_model_used: Optional[str] = None
        self._active_client = None
        self._active_api_key: Optional[str] = None
        
    def _get_next_client(self, timeout_ms: int):
        with LLMClient._key_lock:
            next_key = next(LLMClient._key_cycles[self._pool_id])
        self._active_api_key = next_key
        return genai.Client(api_key=next_key, http_options=types.HttpOptions(timeout=timeout_ms))

    def ordered_api_keys(self) -> List[str]:
        """Return the configured projects starting from the next round-robin key."""
        with LLMClient._key_lock:
            first = next(LLMClient._key_cycles[self._pool_id])
        start = self.api_keys.index(first)
        return self.api_keys[start:] + self.api_keys[:start]

    def client_for_key(self, api_key: str):
        """Create a client explicitly bound to one project's API key."""
        self._active_api_key = api_key
        self._active_client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=self.UPLOAD_TIMEOUT_MS),
        )
        return self._active_client

    def _client_with_timeout(self, client, timeout_ms: int):
        """Keep the upload's project identity when a request references its file."""
        if client is None:
            return self._get_next_client(timeout_ms)
        api_key = self._active_api_key or getattr(client, "api_key", None)
        if api_key:
            return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_ms))
        # SDK clients may not expose their key; retain the original client rather
        # than silently switching projects for a file uploaded through it.
        return client
        
    @property
    def client(self):
        self._active_client = self._get_next_client(self.UPLOAD_TIMEOUT_MS)
        return self._active_client

    @staticmethod
    def _status_of(exc: Exception) -> Optional[int]:
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if isinstance(code, int):
            return code
        text = str(exc)
        match = re.search(r"(?:^|HTTP\s+|code['\"]?\s*[:=]\s*)(504|503|502|500|429|408|404|403|401|400)\b", text, re.I)
        if match:
            return int(match.group(1))
        markers = {
            "RESOURCE_EXHAUSTED": 429,
            "PERMISSION_DENIED": 403,
            "UNAUTHENTICATED": 401,
            "UNAVAILABLE": 503,
        }
        for marker, status in markers.items():
            if marker in text.upper():
                return status
        return None

    def generate(self, contents: Any, json_mode: bool = False, attempts_per_model: int = 1,
                 use_search: bool = False, progress: Optional[Callable[[str], None]] = None,
                 client=None, cancel_event=None, max_models: Optional[int] = None) -> str:
        def report(message: str) -> None:
            if progress:
                try:
                    progress(message)
                except Exception as exc:
                    safe_log(f"[LLM] No se pudo actualizar el progreso: {exc}")

        config = types.GenerateContentConfig(
            response_mime_type="application/json" if json_mode else None,
            tools=[{"google_search": {}}] if use_search else None
        )
        last_exc: Optional[Exception] = None
        deadline = time.monotonic() + self.REQUEST_DEADLINE_SEC

        models = self.models[:max_models] if max_models else self.models
        for model in models:
            for attempt in range(1, attempts_per_model + 1):
                if cancel_event is not None and cancel_event.is_set():
                    raise CancellationRequested()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError(f"Gemini no respondió dentro del límite de {self.REQUEST_DEADLINE_SEC // 60} minutos.") from last_exc
                try:
                    report(f"Enviando solicitud a Gemini ({model}, intento {attempt}/{attempts_per_model}).")
                    request_client = self._client_with_timeout(
                        client, min(self.RESPONSE_TIMEOUT_MS, int(remaining * 1000)))
                    response = request_client.models.generate_content(model=model, contents=contents, config=config)
                    text = response.text
                    if not text:
                        raise ValueError("respuesta vacía")
                    self.last_model_used = model
                    return text
                except Exception as exc:
                    if isinstance(exc, CancellationRequested):
                        raise
                    if cancel_event is not None and cancel_event.is_set():
                        raise CancellationRequested() from exc
                    last_exc = exc
                    status = self._status_of(exc)
                    safe_log(f"[LLM] {model} intento {attempt}/{attempts_per_model} falló ({status or 'error'}): {str(exc)[:110]}")
                    if status in (404, 400):
                        report(f"Gemini rechazó {model}; probando el siguiente modelo disponible.")
                        break  # el modelo no existe o la petición es inválida para este modelo
                    if status in (401, 403):
                        if client is not None:
                            raise GeminiAPIError(status, str(exc)) from exc
                        report(f"La clave actual no fue aceptada por Gemini; probando otra clave.")
                        continue # La llave actual falló, probar inmediatamente con la siguiente
                    if status == 429:
                        if client is not None:
                            raise GeminiAPIError(status, str(exc)) from exc
                        report("Este proyecto alcanzó su cuota temporal; probando el siguiente proyecto.")
                        continue
                    if client is not None and status in (500, 502, 503, 504):
                        # Cuando Google devuelve 503 (alta demanda), el proyecto completo o su cuota está congestionado.
                        # Rotar de inmediato a la siguiente clave/proyecto evita demoras innecesarias entre modelos.
                        raise GeminiAPIError(status, str(exc)) from exc
                    if client is not None and status is None:
                        raise GeminiAPIError(503, str(exc)) from exc
                    delay = min(2 * attempt, 4)
                    report(f"Gemini devolvió un error temporal; reintento en {delay} s.")
                    time.sleep(delay)
        status = self._status_of(last_exc) if last_exc else None
        if status is not None:
            raise GeminiAPIError(status, str(last_exc)) from last_exc
        raise RuntimeError(f"Ningún modelo de Gemini respondió. Último error: {last_exc}")


class GeminiAPIError(RuntimeError):
    """API failure retaining its HTTP status for safe project failover."""

    def __init__(self, status: int, detail: str):
        self.status = status
        # Do not include request details that might contain file URIs or credentials.
        labels = {
            401: "la clave no fue aceptada",
            403: "el proyecto no tiene permiso para esta operación",
            429: "se alcanzó la cuota temporal de este proyecto",
            500: "Gemini devolvió un error interno",
            502: "Gemini devolvió un error de puerta de enlace",
            503: "el modelo está temporalmente saturado",
            504: "Gemini agotó el tiempo de respuesta",
        }
        super().__init__(labels.get(status, f"Gemini respondió HTTP {status}"))

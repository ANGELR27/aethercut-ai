"""Módulo de integración para síntesis de voz y preescucha con Speechify API.

Soporta múltiples claves de API con conmutación automática ante agotamiento
de créditos (failover), validación de saldo disponible y generación de audio MP3.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("speechify_tts")

SPEECHIFY_API_KEYS = [
    "sk_0chj8g0ja0w5y3ex117x3q24749wctcdeq0sxnfvck7",
    "sk_eza006vswwwqe6fye7qrxkm55knrq2cx6dpyt9qakbt",
]

_active_key_index: int = 0
_credits_available: bool = True
_exhausted_keys: set[int] = set()

# Catálogo oficial de voces Speechify integradas en Lumen Studio
SPEECHIFY_VOICES: List[Dict[str, Any]] = [
    {
        "id": "speechify:alejandro",
        "voice_id": "alejandro",
        "name": "Alejandro · Speechify",
        "desc": "Cálida · 1.0×",
        "provider": "speechify",
        "locale": "es-MX",
        "sample_file": "speechify_alejandro.mp3",
    },
    {
        "id": "speechify:aitana",
        "voice_id": "aitana",
        "name": "Aitana · Speechify",
        "desc": "Brillante · 1.0×",
        "provider": "speechify",
        "locale": "es-MX",
        "sample_file": "speechify_aitana.mp3",
    },
    {
        "id": "speechify:alejandra",
        "voice_id": "alejandra",
        "name": "Alejandra · Speechify",
        "desc": "Narrativa · 0.95×",
        "provider": "speechify",
        "locale": "es-MX",
        "sample_file": "speechify_alejandra.mp3",
    },
    {
        "id": "speechify:alexa",
        "voice_id": "alexa",
        "name": "Alexa · Speechify",
        "desc": "Estudio · 1.0×",
        "provider": "speechify",
        "locale": "es-MX",
        "sample_file": "speechify_alexa.mp3",
    },
    {
        "id": "speechify:alondra",
        "voice_id": "alondra",
        "name": "Alondra · Speechify",
        "desc": "Documental · 0.95×",
        "provider": "speechify",
        "locale": "es-MX",
        "sample_file": "speechify_alondra.mp3",
    },
]


def has_speechify_credits() -> bool:
    """Verifica si aún existen créditos utilizables en alguna de las API keys."""
    global _credits_available
    return _credits_available and len(_exhausted_keys) < len(SPEECHIFY_API_KEYS)


def get_speechify_status() -> Dict[str, Any]:
    return {
        "has_credits": has_speechify_credits(),
        "active_key_index": _active_key_index + 1,
        "total_keys": len(SPEECHIFY_API_KEYS),
        "exhausted_keys": list(_exhausted_keys),
    }


def synthesize_speechify(text: str, voice_id: str) -> Optional[bytes]:
    """Sintetiza texto usando Speechify probando la clave activa y conmutando si se agotan créditos."""
    global _active_key_index, _credits_available, _exhausted_keys

    clean_voice = voice_id.replace("speechify:", "").strip()
    clean_text = text.strip()
    if not clean_text:
        return None

    # Envolver en tag SSML speak requerido por Speechify
    if not clean_text.startswith("<speak>"):
        clean_text = f"<speak>{clean_text}</speak>"

    payload = json.dumps({
        "input": clean_text,
        "voice_id": clean_voice,
        "audio_format": "mp3"
    }).encode("utf-8")

    for attempt in range(len(SPEECHIFY_API_KEYS)):
        current_idx = (_active_key_index + attempt) % len(SPEECHIFY_API_KEYS)
        if current_idx in _exhausted_keys:
            continue

        api_key = SPEECHIFY_API_KEYS[current_idx]
        url = "https://api.sws.speechify.com/v1/audio/speech"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if len(data) > 200:
                        _active_key_index = current_idx
                        return data
        except urllib.error.HTTPError as err:
            err_body = ""
            try:
                err_body = err.read().decode("utf-8", errors="ignore")
            except Exception:
                pass

            logger.warning(
                f"[Speechify] Error HTTP {err.code} en clave #{current_idx + 1}: {err_body}"
            )

            # 402 = Payment Required (Sin créditos) / 429 = Rate Limit / 403 = Forbidden
            if err.code in (402, 403, 429) or "credit" in err_body.lower() or "quota" in err_body.lower() or "balance" in err_body.lower():
                _exhausted_keys.add(current_idx)
                logger.error(f"[Speechify] Créditos agotados en clave #{current_idx + 1}. Conmutando...")
            else:
                # Otro error puntual (ej. formato o voice_id)
                pass
        except Exception as exc:
            logger.error(f"[Speechify] Excepción conectando a API: {exc}")

    # Si todas las claves se agotaron
    if len(_exhausted_keys) >= len(SPEECHIFY_API_KEYS):
        _credits_available = False
        logger.critical("[Speechify] TODAS las claves de Speechify han agotado sus créditos. Bloqueando selección.")

    return None

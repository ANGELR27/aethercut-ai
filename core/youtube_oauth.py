"""Publicación directa en YouTube (OAuth 2.0 + Data API v3).

Flujo de código de autorización con PKCE (el client_secret es opcional),
subida resumable con progreso y asignación de miniatura personalizada.
El token se guarda en storage/youtube_token.json y se renueva solo.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests

from config.settings import settings
from core.llm import safe_log

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
CHANNEL_ENDPOINT = "https://www.googleapis.com/youtube/v3/channels"
UPLOAD_ENDPOINT = "https://www.googleapis.com/upload/youtube/v3/videos"
THUMBNAIL_ENDPOINT = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB por petición del protocolo resumable


def _token_path() -> Path:
    return settings.STORAGE_DIR / "youtube_token.json"


def _pending_path() -> Path:
    return settings.STORAGE_DIR / "youtube_oauth_pending.json"


def is_configured() -> bool:
    return bool(settings.YOUTUBE_CLIENT_ID)


def redirect_uri() -> str:
    return f"http://localhost:{settings.YOUTUBE_REDIRECT_PORT}/api/publish/youtube/callback"


class YouTubeAuthError(RuntimeError):
    pass


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def begin_authorization() -> Dict[str, str]:
    """Genera la URL de consentimiento de Google con PKCE."""
    if not is_configured():
        raise YouTubeAuthError("YOUTUBE_CLIENT_ID no está configurado en .env")
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    _save_json(_pending_path(), {"state": state, "verifier": verifier, "created_at": time.time()})

    params = {
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    from urllib.parse import urlencode
    return {"auth_url": f"{AUTH_ENDPOINT}?{urlencode(params)}", "state": state}


def complete_authorization(code: str, state: str) -> Dict[str, Any]:
    """Intercambia el código por tokens y guarda la sesión del canal."""
    pending = json.loads(_pending_path().read_text(encoding="utf-8"))
    if not pending or pending.get("state") != state:
        raise YouTubeAuthError("Estado OAuth no válido: reinicia la conexión desde el estudio de publicación.")
    verifier = pending["verifier"]
    _pending_path().unlink(missing_ok=True)

    data: Dict[str, str] = {
        "code": code,
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "code_verifier": verifier,
        "redirect_uri": redirect_uri(),
        "grant_type": "authorization_code",
    }
    if settings.YOUTUBE_CLIENT_SECRET:
        data["client_secret"] = settings.YOUTUBE_CLIENT_SECRET
    response = requests.post(TOKEN_ENDPOINT, data=data, timeout=30)
    if response.status_code != 200:
        raise YouTubeAuthError(f"Google rechazó el intercambio de código ({response.status_code}): {response.text[:300]}")
    tokens = response.json()
    if not tokens.get("refresh_token"):
        raise YouTubeAuthError("Google no devolvió refresh_token. Revoca el acceso en myaccount.google.com/permissions e inténtalo de nuevo.")
    session = {
        "refresh_token": tokens["refresh_token"],
        "access_token": tokens.get("access_token", ""),
        "expires_at": time.time() + int(tokens.get("expires_in", 3600)),
        "connected_at": time.time(),
    }
    _save_json(_token_path(), session)
    return session


def disconnect() -> None:
    _token_path().unlink(missing_ok=True)


def is_connected() -> bool:
    token = _token_path()
    if not token.exists():
        return False
    try:
        session = json.loads(token.read_text(encoding="utf-8"))
        return bool(session.get("refresh_token"))
    except (OSError, json.JSONDecodeError):
        return False


def _valid_access_token() -> str:
    session = json.loads(_token_path().read_text(encoding="utf-8"))
    if time.time() < float(session.get("expires_at", 0)) - 60 and session.get("access_token"):
        return session["access_token"]
    data: Dict[str, str] = {
        "refresh_token": session["refresh_token"],
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "grant_type": "refresh_token",
    }
    if settings.YOUTUBE_CLIENT_SECRET:
        data["client_secret"] = settings.YOUTUBE_CLIENT_SECRET
    response = requests.post(TOKEN_ENDPOINT, data=data, timeout=30)
    if response.status_code != 200:
        raise YouTubeAuthError(f"No se pudo renovar el token de YouTube ({response.status_code}): {response.text[:300]}")
    refreshed = response.json()
    session["access_token"] = refreshed.get("access_token", "")
    session["expires_at"] = time.time() + int(refreshed.get("expires_in", 3600))
    _save_json(_token_path(), session)
    return session["access_token"]


def get_channel_info() -> Optional[Dict[str, Any]]:
    """Datos del canal autenticado (nombre, avatar, suscriptores)."""
    if not is_connected():
        return None
    try:
        response = requests.get(
            CHANNEL_ENDPOINT,
            params={"part": "snippet,statistics", "mine": "true"},
            headers={"Authorization": f"Bearer {_valid_access_token()}"},
            timeout=30,
        )
        if response.status_code != 200:
            safe_log(f"[YouTube] Canal no disponible ({response.status_code}): {response.text[:160]}")
            return None
        items = response.json().get("items") or []
        if not items:
            return None
        snippet = items[0].get("snippet", {})
        stats = items[0].get("statistics", {})
        return {
            "channel_id": items[0].get("id", ""),
            "title": snippet.get("title", ""),
            "thumbnail": (snippet.get("thumbnails", {}).get("default", {}) or {}).get("url", ""),
            "subscribers": stats.get("subscriberCount", "0"),
        }
    except Exception as exc:
        safe_log(f"[YouTube] Error leyendo canal: {exc}")
        return None


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    privacy: str = "public",
    *,
    category_id: str = "27",
    made_for_kids: bool = False,
    notify_subscribers: bool = True,
    progress: Optional[Callable[[float, str], None]] = None,
) -> Dict[str, Any]:
    """Sube el video con el protocolo resumable de YouTube.

    Devuelve {"video_id", "video_url"}. progress recibe (0..1, mensaje).
    """
    access_token = _valid_access_token()
    report = progress or (lambda frac, msg: None)
    total = video_path.stat().st_size

    metadata = {
        "snippet": {
            "title": title[:100],
            "description": (description or "")[:5000],
            "tags": [t[:100] for t in tags][:30],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy if privacy in ("public", "unlisted", "private") else "public",
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    report(0.02, "Iniciando sesión de subida en YouTube...")
    session_response = requests.post(
        f"{UPLOAD_ENDPOINT}?uploadType=resumable&part=snippet,status"
        f"{'&notifySubscribers=false' if not notify_subscribers else ''}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(total),
            "X-Upload-Content-Type": "video/mp4",
        },
        data=json.dumps(metadata),
        timeout=60,
    )
    if session_response.status_code not in (200, 201):
        raise YouTubeAuthError(f"YouTube rechazó la subida ({session_response.status_code}): {session_response.text[:300]}")
    session_uri = session_response.headers.get("Location")
    if not session_uri:
        raise YouTubeAuthError("YouTube no devolvió la URL de sesión resumable.")

    report(0.05, f"Subiendo video ({total / 1024 / 1024:.1f} MB)...")
    with video_path.open("rb") as handle:
        offset = 0
        while offset < total:
            chunk = handle.read(UPLOAD_CHUNK_SIZE)
            chunk_end = offset + len(chunk) - 1
            headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {offset}-{chunk_end}/{total}",
            }
            put = requests.put(session_uri, data=chunk, headers=headers, timeout=600)
            if put.status_code not in (200, 201, 202):
                raise YouTubeAuthError(f"Fallo durante la subida ({put.status_code}): {put.text[:300]}")
            offset = chunk_end + 1
            report(0.05 + 0.9 * (offset / total), f"Subiendo video... {offset / total * 100:.0f}%")
            if put.status_code in (200, 201):
                video = put.json()
                video_id = video.get("id", "")
                report(1.0, "Video recibido por YouTube.")
                return {"video_id": video_id, "video_url": f"https://youtu.be/{video_id}"}

    raise YouTubeAuthError("La subida terminó sin confirmación de YouTube.")


def set_thumbnail(video_id: str, thumbnail_path: Path) -> bool:
    """Asigna la miniatura personalizada (requiere canal verificado)."""
    if not video_id or not thumbnail_path.exists():
        return False
    try:
        access_token = _valid_access_token()
        with thumbnail_path.open("rb") as handle:
            response = requests.post(
                f"{THUMBNAIL_ENDPOINT}?videoId={video_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                files={"media": (thumbnail_path.name, handle, "image/jpeg")},
                timeout=120,
            )
        if response.status_code in (200, 201):
            return True
        safe_log(f"[YouTube] Miniatura personalizada rechazada ({response.status_code}): {response.text[:200]}")
        return False
    except Exception as exc:
        safe_log(f"[YouTube] Error subiendo miniatura: {exc}")
        return False

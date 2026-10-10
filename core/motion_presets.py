"""Librería de Presets de Motion Design y Animación inspirados en Jitter.video.

Proporciona estilos visuales pre-diseñados listos para producción:
- Bento Grid Glassmorphism (Negro Mate + Sombras Suaves)
- Kinetic Typography (Títulos dinámicos de alto impacto)
- Clean Minimal Lower-Thirds (Cintillos de autor y fuentes)
- Stat Callouts (Métricas y porcentajes con acento moderno)
"""

from typing import Dict, Any

JITTER_PRESETS: Dict[str, Dict[str, Any]] = {
    "jitter_bento_matte": {
        "name": "Bento Matte Dark (Jitter Style)",
        "description": "Estilo negro mate con desenfoque de fondo y borde sutil de 1px.",
        "bg_color": [15, 20, 28, 235],
        "border_color": [255, 255, 255, 45],
        "border_width": 2,
        "corner_radius": 20,
        "title_color": [255, 255, 255, 255],
        "body_color": [203, 213, 225, 255],
        "accent_color": [56, 189, 248, 255],
        "shadow_blur": 16,
        "shadow_offset": [0, 8],
        "animation": {
            "enter": "fade_slide_up",
            "duration": 0.45,
            "easing": "cubic_bezier(0.16, 1, 0.3, 1)"
        }
    },
    "jitter_lower_third": {
        "name": "Cinematic Lower Third (Jitter Style)",
        "description": "Cintillo minimalista para nombres, citas o fuentes periodísticas.",
        "bg_color": [10, 14, 22, 220],
        "border_color": [56, 189, 248, 80],
        "border_width": 1,
        "corner_radius": 12,
        "title_color": [255, 255, 255, 255],
        "body_color": [148, 163, 184, 255],
        "accent_color": [56, 189, 248, 255],
        "animation": {
            "enter": "wipe_right",
            "duration": 0.35,
            "easing": "ease_out"
        }
    },
    "jitter_stat_callout": {
        "name": "Stat Highlight (Jitter Style)",
        "description": "Caja destacada con número gigante y etiqueta inferior.",
        "bg_color": [18, 24, 38, 240],
        "border_color": [255, 255, 255, 50],
        "border_width": 2,
        "corner_radius": 24,
        "title_color": [56, 189, 248, 255],
        "body_color": [241, 245, 249, 255],
        "accent_color": [16, 185, 129, 255],
        "animation": {
            "enter": "pop_bounce",
            "duration": 0.4,
            "easing": "ease_out_back"
        }
    }
}


def get_preset(name: str) -> Dict[str, Any]:
    """Obtiene la configuración de un preset por su clave."""
    return JITTER_PRESETS.get(name, JITTER_PRESETS["jitter_bento_matte"])

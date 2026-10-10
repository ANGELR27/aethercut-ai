import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno desde .env si existe
load_dotenv(BASE_DIR / ".env")

class Settings:
    """Configuración global del sistema con inicialización de rutas y variables."""

    BASE_DIR: Path = BASE_DIR

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")
    PIXABAY_API_KEY: str = os.getenv("PIXABAY_API_KEY", "")
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "moonshotai/kimi-k3")

    # Multi-Agent Specialized Triad
    GLM_API_KEY: str = os.getenv("GLM_API_KEY", "")
    GLM_FLASH_API_KEY: str = os.getenv("GLM_FLASH_API_KEY", "")
    KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")

    # Modelo principal activo de Gemini para análisis y redacción
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    # Parámetros de edición
    MAX_SILENCE_DURATION_SEC: float = float(os.getenv("MAX_SILENCE_DURATION_SEC", "1.5"))
    MIN_SPEECH_SEGMENT_SEC: float = float(os.getenv("MIN_SPEECH_SEGMENT_SEC", "0.4"))
    DEFAULT_VIDEO_FPS: int = int(os.getenv("DEFAULT_VIDEO_FPS", "30"))

    # Rutas de almacenamiento
    STORAGE_DIR: Path = BASE_DIR / "storage"
    INPUTS_DIR: Path = STORAGE_DIR / "inputs"
    OUTPUTS_DIR: Path = STORAGE_DIR / "outputs"
    TEMP_DIR: Path = STORAGE_DIR / "temp"
    ASSETS_DIR: Path = STORAGE_DIR / "assets"
    PROJECTS_DIR: Path = STORAGE_DIR / "projects"

    @classmethod
    def ensure_directories(cls) -> None:
        """Crea automáticamente los directorios requeridos si no existen."""
        for path in [cls.STORAGE_DIR, cls.INPUTS_DIR, cls.OUTPUTS_DIR, cls.TEMP_DIR, cls.ASSETS_DIR, cls.PROJECTS_DIR]:
            path.mkdir(parents=True, exist_ok=True)

# Instancia singleton accesible
settings = Settings()
settings.ensure_directories()

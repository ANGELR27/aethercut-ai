import sys
import json
from pathlib import Path
from config.settings import settings
from core.models import VideoEditingPlan, TimelineSegment, BRollCue, CaptionItem, HighlightClip, ActionType
from core.gemini_analyzer import GeminiVideoAnalyzer
from core.prompt_templates import build_editor_prompt
from utils.file_manager import FileManager
from utils.json_validator import JSONValidator

def run_fase_1_verification():
    """Comprueba directorios, dependencias y variables de entorno."""
    print("=" * 60)
    print("FASE 1: VERIFICACIÓN DEL ENTORNO Y ESTRUCTURA")
    print("=" * 60)
    settings.ensure_directories()
    
    print(f"[OK] Directorio Base: {settings.STORAGE_DIR.parent}")
    print(f"[OK] Inputs Dir:      {settings.INPUTS_DIR} (Existe: {settings.INPUTS_DIR.exists()})")
    print(f"[OK] Outputs Dir:     {settings.OUTPUTS_DIR} (Existe: {settings.OUTPUTS_DIR.exists()})")
    print(f"[OK] Temp Dir:        {settings.TEMP_DIR} (Existe: {settings.TEMP_DIR.exists()})")
    print(f"[OK] Assets Dir:      {settings.ASSETS_DIR} (Existe: {settings.ASSETS_DIR.exists()})")
    
    # Comprobar estado de API Key
    has_gemini_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")
    print(f"[INFO] GEMINI_API_KEY configurada: {'SI' if has_gemini_key else 'NO (Pendiente en .env)'}")
    print(f"[INFO] Modelo seleccionado: {settings.GEMINI_MODEL}")
    print(f"[INFO] Umbral silencio máx: {settings.MAX_SILENCE_DURATION_SEC} segundos")
    print()

def run_fase_2_schema_validation():
    """Valida la integridad del prompt y la deserialización del modelo Pydantic."""
    print("=" * 60)
    print("FASE 2: VALIDACIÓN DE PROMPTS Y ESQUEMA JSON")
    print("=" * 60)
    
    prompt = build_editor_prompt(silence_threshold=1.5)
    print(f"[OK] System Prompt generado ({len(prompt)} caracteres).")
    
    # Prueba de deserialización con un JSON sintético representativo
    mock_payload = {
        "video_summary": "Explicación sobre inteligencia artificial y las cataratas del Niágara.",
        "total_original_duration_sec": 45.2,
        "timeline": [
            {"start_sec": 0.0, "end_sec": 12.4, "action": "KEEP", "reasoning": "Introducción y bienvenida."},
            {"start_sec": 12.4, "end_sec": 14.8, "action": "CUT_SILENCE", "reasoning": "Pausa silenciosa de 2.4s."},
            {"start_sec": 14.8, "end_sec": 30.5, "action": "KEEP", "reasoning": "Mención de las Cataratas del Niágara."},
            {"start_sec": 30.5, "end_sec": 32.2, "action": "CUT_SILENCE", "reasoning": "Duda y respiración de 1.7s."},
            {"start_sec": 32.2, "end_sec": 45.2, "action": "KEEP", "reasoning": "Conclusión y llamado a la acción."}
        ],
        "b_rolls": [
            {
                "cue_id": "broll_1",
                "start_sec": 18.0,
                "end_sec": 22.5,
                "concept": "Cataratas del Niágara",
                "search_query_en": "niagara falls aerial drone shot",
                "asset_type": "video",
                "transition": "fade",
                "reasoning": "El orador ejemplifica el poder natural citando las cataratas."
            }
        ],
        "captions": [
            {
                "start_sec": 0.0,
                "end_sec": 3.2,
                "text": "Bienvenidos al futuro del video.",
                "highlight_words": ["futuro", "video"]
            },
            {
                "start_sec": 18.0,
                "end_sec": 22.0,
                "text": "Tan impresionante como las cataratas del Niágara.",
                "highlight_words": ["cataratas", "Niágara"]
            }
        ],
        "highlights": [
            {
                "clip_id": "short_1",
                "start_sec": 14.8,
                "end_sec": 30.5,
                "title": "¿El poder de la naturaleza o la IA?",
                "hook": "Imagina comparar una cascada gigante con un algoritmo.",
                "virality_score": 92
            }
        ]
    }
    
    mock_raw_str = f"```json\n{json.dumps(mock_payload, indent=2)}\n```"
    plan = JSONValidator.validate_editing_plan(mock_raw_str)
    
    print("[OK] JSONValidator saneó los bloques markdown y validó con éxito:")
    print(f"     -> Segmentos en Timeline: {len(plan.timeline)}")
    print(f"     -> Cues de B-Roll:        {len(plan.b_rolls)}")
    print(f"     -> Subtítulos dinámicos:  {len(plan.captions)}")
    print(f"     -> Clips destacados:     {len(plan.highlights)}")
    print()

def run_fase_2_live_gemini(video_filename: str):
    """Ejecuta el análisis en vivo contra la API de Gemini si se provee un video."""
    video_path = settings.INPUTS_DIR / video_filename
    if not video_path.exists():
        print(f"[ERROR] No se encontró el archivo de video en: {video_path}")
        return

    meta = FileManager.get_media_metadata(video_path)
    print(f"[INFO] Metadatos del video: {meta}")

    analyzer = GeminiVideoAnalyzer()
    plan = analyzer.analyze_video(video_path)
    
    out_file = settings.OUTPUTS_DIR / f"{video_path.stem}_editing_plan.json"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(plan.model_dump_json(indent=2))
        
    print(f"[ÉXITO] Plan de edición guardado en: {out_file}")

if __name__ == "__main__":
    run_fase_1_verification()
    run_fase_2_schema_validation()
    
    if len(sys.argv) > 1:
        video_arg = sys.argv[1]
        print(f"Ejecutando análisis en vivo para: {video_arg}")
        run_fase_2_live_gemini(video_arg)
    else:
        print("[TIP] Para ejecutar un análisis en vivo con Gemini 1.5 Pro:")
        print("  1. Agrega tu GEMINI_API_KEY en .env")
        print("  2. Coloca tu video en storage/inputs/mi_video.mp4")
        print("  3. Ejecuta: python main_fase2_test.py mi_video.mp4")

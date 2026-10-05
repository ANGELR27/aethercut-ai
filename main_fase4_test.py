from pathlib import Path
from config.settings import settings
from core.models import VideoEditingPlan, TimelineSegment, BRollCue, CaptionItem, HighlightClip, ActionType
from core.render_engine import VideoRenderEngine
from core.orchestrator import AssetOrchestrator

def progress_logger(msg: str, pct: float):
    print(f"[{int(pct*100)}%] {msg}")

def test_phase_4_pipeline():
    print("=" * 65)
    print("FASE 4: MOTOR DE RENDERIZADO (MoviePy + FFmpeg)")
    print("=" * 65)

    sample_vid = settings.TEMP_DIR / "test_sample.mp4"
    if not sample_vid.exists():
        print("El video sintético de prueba no existe.")
        return

    # Plan de edición: Cortar silencio entre segundo 2.0 y 4.0 (Poda de 2s)
    plan = VideoEditingPlan(
        video_summary="Video de prueba sintético",
        total_original_duration_sec=6.0,
        timeline=[
            TimelineSegment(start_sec=0.0, end_sec=2.0, action=ActionType.KEEP, reasoning="Discurso 1"),
            TimelineSegment(start_sec=2.0, end_sec=4.0, action=ActionType.CUT_SILENCE, reasoning="Silencio detectado"),
            TimelineSegment(start_sec=4.0, end_sec=6.0, action=ActionType.KEEP, reasoning="Discurso 2")
        ],
        b_rolls=[
            BRollCue(
                cue_id="broll_test",
                start_sec=0.5,
                end_sec=1.8,
                concept="Innovación Tecnológica",
                search_query_en="technology glowing matrix",
                asset_type="photo",
                reasoning="Apoyo al discurso inicial"
            )
        ],
        captions=[
            CaptionItem(start_sec=0.0, end_sec=1.8, text="Editor impulsado por IA", highlight_words=["IA", "Editor"]),
            CaptionItem(start_sec=4.0, end_sec=5.8, text="Corte automático y dinámico", highlight_words=["dinámico"])
        ],
        highlights=[
            HighlightClip(clip_id="h1", start_sec=0.0, end_sec=2.0, title="Momento Clave", hook="Atención total", virality_score=95)
        ]
    )

    # 1. Resolver B-Rolls con el orquestador
    orchestrator = AssetOrchestrator()
    plan = orchestrator.run_sync(plan)

    # 2. Renderizar cortes y B-roll
    engine = VideoRenderEngine(fps=30)
    assembled_path = settings.TEMP_DIR / "assembled_preview.mp4"
    final_output = settings.OUTPUTS_DIR / "final_edited_video.mp4"

    engine.render_smart_cut_and_brolls(sample_vid, plan, assembled_path, progress_callback=progress_logger)

    # 3. Quemar subtítulos con FFmpeg
    engine.burn_subtitles_ffmpeg(assembled_path, plan.captions, final_output, progress_callback=progress_logger)

    # 4. Extraer Short vertical 9:16
    short_path = engine.extract_vertical_short(sample_vid, plan.highlights[0], settings.OUTPUTS_DIR)

    print()
    print("[ÉXITO FASE 4] Renderizado completado con éxito:")
    print(f" -> Video Final Editado: {final_output} (Existe: {final_output.exists()})")
    print(f" -> Short 9:16 Extraído: {short_path} (Existe: {short_path.exists()})")
    print("=" * 65)

if __name__ == "__main__":
    test_phase_4_pipeline()

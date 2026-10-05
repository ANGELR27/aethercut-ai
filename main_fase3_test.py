import asyncio
import time
from pathlib import Path
from config.settings import settings
from core.models import VideoEditingPlan, TimelineSegment, BRollCue, CaptionItem, HighlightClip, ActionType
from core.orchestrator import AssetOrchestrator

def progress_listener(event: str, data: dict):
    """Callback en tiempo real de eventos de orquestación."""
    if event == "broll_downloading":
        print(f"  [EVENTO] Descargando B-Roll: '{data.get('concept')}' (ID: {data.get('cue_id')})...")
    elif event == "broll_completed":
        print(f"  [EVENTO] Asset listo: {Path(data.get('path')).name} | Proveedor: {data.get('provider')}")
    elif event == "broll_failed":
        print(f"  [ALERTA] Falló descarga para {data.get('cue_id')}")

async def run_fase_3_demo():
    print("=" * 65)
    print("FASE 3: ORQUESTACIÓN CONCURRENTE MULTI-AGENTE & ASSETS")
    print("=" * 65)

    # Creamos un plan con 3 B-Roll cues simultáneos
    test_plan = VideoEditingPlan(
        video_summary="Demostración de edición multi-agente con B-Roll concurrente",
        total_original_duration_sec=30.0,
        timeline=[
            TimelineSegment(start_sec=0.0, end_sec=10.0, action=ActionType.KEEP, reasoning="Segmento 1"),
            TimelineSegment(start_sec=10.0, end_sec=12.0, action=ActionType.CUT_SILENCE, reasoning="Silencio"),
            TimelineSegment(start_sec=12.0, end_sec=30.0, action=ActionType.KEEP, reasoning="Segmento 2")
        ],
        b_rolls=[
            BRollCue(
                cue_id="broll_1",
                start_sec=2.0,
                end_sec=6.0,
                concept="Cataratas del Niágara",
                search_query_en="niagara falls waterfall nature",
                asset_type="photo",
                reasoning="Apoyo visual sobre fuerza de la naturaleza"
            ),
            BRollCue(
                cue_id="broll_2",
                start_sec=7.0,
                end_sec=10.0,
                concept="Inteligencia Artificial y Redes Neuronales",
                search_query_en="artificial intelligence technology network",
                asset_type="photo",
                reasoning="Demostración de algoritmos"
            ),
            BRollCue(
                cue_id="broll_3",
                start_sec=15.0,
                end_sec=19.5,
                concept="Criptomonedas y Bitcoin",
                search_query_en="bitcoin cryptocurrency finance",
                asset_type="photo",
                reasoning="Contexto económico"
            )
        ]
    )

    orchestrator = AssetOrchestrator()
    print(f"Proveedores registrados en el orquestador: {[p.__class__.__name__ for p in orchestrator.providers]}")
    print()

    start_time = time.time()
    updated_plan = await orchestrator.process_all_brolls(test_plan, progress_callback=progress_listener)
    elapsed = time.time() - start_time

    print()
    print(f"[REPORTE FASE 3] Descarga concurrente finalizada en {round(elapsed, 2)} segundos.")
    print("-" * 65)
    for cue in updated_plan.b_rolls:
        print(f" -> Cue [{cue.cue_id}]: {cue.concept} | Estado: {cue.download_status} | Ruta: {cue.local_file_path}")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_fase_3_demo())

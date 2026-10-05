import asyncio
from pathlib import Path
from typing import List, Callable, Optional, Dict, Any
from config.settings import settings
from core.models import VideoEditingPlan, BRollCue
from core.asset_providers import AssetProviderFactory, AssetProvider

class AssetOrchestrator:
    """
    Orquestador concurrente multi-agente para la resolución, búsqueda y descarga
    en paralelo de todos los recursos visuales (B-Roll) requeridos en el plan de edición.
    """

    def __init__(self, target_dir: Optional[Path] = None):
        self.target_dir = target_dir or settings.ASSETS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.providers: List[AssetProvider] = AssetProviderFactory.get_providers()

    async def _resolve_single_cue(
        self,
        cue: BRollCue,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> BRollCue:
        """Intenta descargar el asset para un cue iterando por la cadena de proveedores."""
        cue.download_status = "DOWNLOADING"
        if progress_callback:
            progress_callback("broll_downloading", {"cue_id": cue.cue_id, "concept": cue.concept})

        for provider in self.providers:
            try:
                local_path = await provider.search_and_download(cue, self.target_dir)
                if local_path and local_path.exists():
                    cue.local_file_path = str(local_path)
                    cue.download_status = "COMPLETED"
                    if progress_callback:
                        progress_callback("broll_completed", {
                            "cue_id": cue.cue_id,
                            "path": str(local_path),
                            "provider": provider.__class__.__name__
                        })
                    return cue
            except Exception as e:
                print(f"[AssetOrchestrator] Error en {provider.__class__.__name__} para {cue.cue_id}: {e}")

        cue.download_status = "FAILED"
        if progress_callback:
            progress_callback("broll_failed", {"cue_id": cue.cue_id})
        return cue

    async def process_all_brolls(
        self,
        plan: VideoEditingPlan,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> VideoEditingPlan:
        """
        Ejecuta la descarga paralela y no bloqueante de todos los B-Rolls del plan.
        """
        if not plan.b_rolls:
            print("[AssetOrchestrator] No hay B-Rolls definidos en el plan de edición.")
            return plan

        print(f"[AssetOrchestrator] Iniciando descarga concurrente de {len(plan.b_rolls)} B-Roll cues...")

        # Lanzar todas las descargas concurrentemente
        tasks = [
            self._resolve_single_cue(cue, progress_callback)
            for cue in plan.b_rolls
        ]
        
        updated_cues = await asyncio.gather(*tasks)
        plan.b_rolls = list(updated_cues)

        completed_count = sum(1 for c in plan.b_rolls if c.download_status == "COMPLETED")
        print(f"[AssetOrchestrator] Proceso completado: {completed_count}/{len(plan.b_rolls)} assets listos.")
        return plan

    def run_sync(
        self,
        plan: VideoEditingPlan,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> VideoEditingPlan:
        """Wrapper síncrono conveniente para llamadas desde hilos de renderizado."""
        return asyncio.run(self.process_all_brolls(plan, progress_callback))

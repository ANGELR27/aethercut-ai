"""Persistencia local de un proyecto de edición.

El render puede tardar, pero la decisión editorial no debe desaparecer cuando el
servidor se reinicia. Cada proyecto conserva el plan, las fuentes, los assets y
las versiones exportadas para poder revisarlo y volver a renderizarlo.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings
from core.models import VideoEditingPlan


class ProjectStore:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.root = settings.PROJECTS_DIR / project_id
        self.workdir = self.root / "work"
        self.manifest_path = self.root / "project.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.workdir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def read(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"No existe el proyecto {self.project_id}.")
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def write(self, document: Dict[str, Any]) -> Dict[str, Any]:
        document["updated_at"] = self._now()
        temp = self.manifest_path.with_suffix(".tmp")
        temp.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.manifest_path)
        return document

    def create(self, *, source_file: Path, original_name: str, options: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        return self.write({
            "id": self.project_id,
            "created_at": now,
            "source_file": str(source_file.resolve()),
            "original_name": original_name,
            "options": options,
            "status": "queued",
            "plan": None,
            "result": None,
            "preview_file": None,
        })

    def set_status(self, status: str, **extra: Any) -> Dict[str, Any]:
        doc = self.read()
        doc["status"] = status
        doc.update(extra)
        return self.write(doc)

    def save_plan(self, plan: VideoEditingPlan, **extra: Any) -> Dict[str, Any]:
        doc = self.read()
        doc["plan"] = plan.model_dump(mode="json")
        doc.update(extra)
        return self.write(doc)

    def load_plan(self) -> VideoEditingPlan:
        doc = self.read()
        if not doc.get("plan"):
            raise ValueError("El proyecto aún no tiene un plan de edición.")
        return VideoEditingPlan.model_validate(doc["plan"])


def editor_snapshot(plan: VideoEditingPlan) -> Dict[str, Any]:
    """Versión compacta y segura para actualizar el editor en el navegador."""
    return {
        "summary": plan.video_summary,
        "duration": plan.total_original_duration_sec,
        "cuts": [s.model_dump(mode="json") for s in plan.timeline if s.action != "KEEP"],
        "cards": [
            {
                "id": c.card_id, "start": c.start_sec, "end": c.end_sec,
                "duration": c.display_duration_sec, "headline": c.headline,
                "kind": c.kind, "claim": c.claim, "verdict": c.verdict,
                "note": c.note, "body": c.body, "position": c.screen_position,
                "enabled": c.enabled, "sources": [s.model_dump() for s in c.sources],
            }
            for c in plan.info_cards
        ],
        "brolls": [
            {
                "id": b.cue_id, "start": b.start_sec, "end": b.end_sec,
                "concept": b.concept, "status": b.download_status,
                "enabled": b.enabled,
            }
            for b in plan.b_rolls
        ],
        "shorts": [
            {
                "id": h.clip_id, "start": h.start_sec, "end": h.end_sec,
                "title": h.title, "hook": h.hook, "score": h.virality_score,
            }
            for h in plan.highlights
        ],
    }

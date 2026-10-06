"""Pruebas locales de piezas críticas que no requieren Gemini ni una carga web."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from core.card_renderer import InfoCardRenderer
from core.models import ActionType, InfoCard, SourceRef, TimelineSegment, VideoEditingPlan
from core.render_engine import VideoRenderEngine
from core.silence_detector import SilenceDetector
from core.timeline import TimelineMapper
from core.visual_analysis import VisualAnalyzer


class LocalPipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="aethercut-smoke-"))
        self.video = self.temp / "input.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=854x480:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
            "-t", "6", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(self.video),
        ], check=True)

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_audio_visual_and_render(self):
        timeline = SilenceDetector().build_timeline(self.video, 6.0, 1.5)
        self.assertTrue(timeline)
        self.assertTrue(any(segment.action == ActionType.KEEP for segment in timeline))

        scenes = VisualAnalyzer().detect_scene_cuts(self.video)
        self.assertIsInstance(scenes, list)

        card = InfoCard(
            card_id="test-card", start_sec=0.5, end_sec=5.0, kind="dato",
            headline="Prueba de tarjeta", claim="El render incorpora una tarjeta.", search_query="prueba",
            verdict="supported", body="La composición local finalizó correctamente.",
            sources=[SourceRef(title="Fuente de prueba", url="https://example.com", domain="example.com")],
            screen_position="lower_left", display_duration_sec=4.5,
        )
        InfoCardRenderer(854, 480).render_all([card], self.temp / "cards")
        plan = VideoEditingPlan(
            video_summary="Prueba local", total_original_duration_sec=6.0,
            timeline=[TimelineSegment(start_sec=0, end_sec=6, action=ActionType.KEEP)], info_cards=[card],
        )
        mapper = TimelineMapper.from_plan_segments(plan.timeline, 6.0)
        output = self.temp / "result.mp4"
        result = VideoRenderEngine().render(self.video, plan, mapper, self.temp / "new-workdir", output)
        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 30_000)
        self.assertEqual(len(result["overlays"]), 1)


if __name__ == "__main__":
    unittest.main()

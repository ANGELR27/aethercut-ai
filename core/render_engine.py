import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from config.settings import settings
from core.models import CaptionItem, HighlightClip, VideoEditingPlan
from core.subtitle_generator import SubtitleGenerator
from core.timeline import TimelineMapper

ProgressCb = Optional[Callable[[str, float], None]]

VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv")
# Para hardware AMD Ryzen/Radeon, usamos AMF. Si fallara por drivers, se puede revertir a libx264.
ENC_FINAL = ["-c:v", "h264_amf", "-quality", "speed", "-rc", "cqp", "-qp_i", "21", "-qp_p", "21", "-pix_fmt", "yuv420p"]
ENC_INTERMEDIATE = ["-c:v", "h264_amf", "-quality", "speed", "-rc", "cqp", "-qp_i", "17", "-qp_p", "17", "-pix_fmt", "yuv420p"]


def probe_size(path: Path) -> Tuple[int, int]:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
             "-of", "json", str(path)], capture_output=True, text=True, timeout=30,
        ).stdout
        s = json.loads(out)["streams"][0]
        return int(s["width"]), int(s["height"])
    except Exception:
        return 1920, 1080


def _ff_path(p: Path) -> str:
    """Ruta escapada para filtros de FFmpeg (ass=...) en Windows."""
    return str(p.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


class VideoRenderEngine:
    """
    Motor de render 100% FFmpeg (sin MoviePy):
      Pasada 1: Smart Cut (trim + concat) -> intermedio de alta calidad.
      Pasada 2: overlays animados (tarjetas, fotos, B-Roll de video) + subtítulos ASS opcionales.
    Cada overlay se desplaza en el tiempo con setpts, así su fade-in/out ocurre en el momento exacto.
    """

    def __init__(self, fps: int = 30):
        self.fps = fps

    @staticmethod
    def _run(cmd: List[str], desc: str) -> bool:
        print(f"[RenderEngine] {desc}...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            print(f"[RenderEngine] {desc} falló:\n{proc.stderr[-1200:]}")
            return False
        return True

    # ------------------------------------------------------------------ pasada 1
    def cut_silences(self, input_video: Path, mapper: TimelineMapper, out: Path) -> Path:
        keep = mapper.keep
        if len(keep) <= 1:
            seg = keep[0] if keep else None
            cmd = ["ffmpeg", "-y", "-i", str(input_video)]
            if seg:
                cmd = ["ffmpeg", "-y", "-ss", f"{seg.start_sec:.3f}", "-i", str(input_video),
                       "-t", f"{seg.end_sec - seg.start_sec:.3f}"]
            cmd += [*ENC_INTERMEDIATE, "-c:a", "aac", "-b:a", "192k", str(out)]
            return out if self._run(cmd, "Normalizando video (sin silencios que cortar)") else input_video

        # El grafo se escribe en un archivo: con cientos de cortes la línea de comandos excede el límite de Windows.
        parts, pairs = [], []
        for i, seg in enumerate(keep):
            s, e = max(0.0, seg.start_sec), max(seg.start_sec + 0.05, seg.end_sec)
            parts.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}]")
            parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}]")
            pairs.append(f"[v{i}][a{i}]")
        parts.append(f"{''.join(pairs)}concat=n={len(keep)}:v=1:a=1[vc][ac]")
        script = out.with_suffix(".cut.txt")
        script.write_text(";\n".join(parts), encoding="utf-8")

        cmd = ["ffmpeg", "-y", "-i", str(input_video), "-filter_complex_script", str(script),
               "-map", "[vc]", "-map", "[ac]", *ENC_INTERMEDIATE, "-c:a", "aac", "-b:a", "192k", str(out)]
        ok = self._run(cmd, f"Smart Cut de {len(keep)} tramos")
        script.unlink(missing_ok=True)
        return out if ok and out.exists() else input_video

    # ------------------------------------------------------------------ overlays
    @staticmethod
    def collect_overlays(plan: VideoEditingPlan, mapper: TimelineMapper) -> List[Dict]:
        total = mapper.total_duration
        items: List[Dict] = []

        for card in plan.info_cards:
            if card.verdict not in ("supported", "contradicted", "insufficient") or not card.card_path:
                continue
            
            # Comprobar que todos los paths existan (para el mito vs realidad hay dos separados por |)
            paths = str(card.card_path).split("|")
            if any(not Path(p).exists() for p in paths):
                continue
                
            placed = mapper.map_first(card.start_sec, card.end_sec)
            if placed:
                s = placed[0]
                d = min(max(placed[1] - s, 4.5), 7.0, total - s)
                if d >= 2.5:
                    if len(paths) == 2:
                        items.append({"kind": "card", "path": paths[0], "start": s, "dur": 1.5})
                        items.append({"kind": "card", "path": paths[1], "start": s + 1.5, "dur": d - 1.5})
                    else:
                        items.append({"kind": "card", "path": paths[0], "start": s, "dur": d})

        for cue in plan.b_rolls:
            if cue.download_status != "COMPLETED" or not cue.local_file_path:
                continue
            path = Path(cue.local_file_path)
            if not path.exists():
                continue
            placed = mapper.map_first(cue.start_sec, cue.end_sec)
            if placed:
                s = placed[0]
                d = min(max(placed[1] - s, 3.0), 5.0, total - s)
                if d >= 1.5:
                    is_video = path.suffix.lower() in VIDEO_EXT
                    # las fotos ya llegan enmarcadas como tarjeta (photo_frame_path)
                    p = cue.local_file_path if is_video else (getattr(cue, "frame_path", None) or "")
                    if p and Path(p).exists():
                        items.append({"kind": "video" if is_video else "photo", "path": p, "start": s, "dur": d})

        # Sin choques: dos elementos en la misma zona de pantalla no se pisan.
        items.sort(key=lambda x: x["start"])
        zone_free: Dict[str, float] = {}
        final = []
        for it in items:
            zone = "full" if it["kind"] == "video" else ("right" if it["kind"] == "card" else "left")
            blockers = [zone, "full"] if zone != "full" else ["full", "right", "left"]
            if any(zone_free.get(z, -1) > it["start"] for z in blockers):
                continue
            zone_free[zone] = it["start"] + it["dur"] + 0.6
            final.append(it)
        return final

    def compose(self, base_video: Path, overlays: List[Dict], ass_file: Optional[Path], out: Path, zoom_segments: Optional[List[Dict]] = None, censor_segments: Optional[List[Dict]] = None) -> bool:
        W, H = probe_size(base_video)
        margin_x, margin_y = int(W * 0.025), int(H * 0.05)
        cmd = ["ffmpeg", "-y", "-i", str(base_video)]
        chains, cur = [], "0:v"
        audio_map = "0:a?"
        
        # 1. Dynamic Zoom (Punch-ins)
        if zoom_segments:
            chains.append(f"[0:v]scale={int(W*1.2)}:{int(H*1.2)},crop={W}:{H},setsar=1[v_zoom]")
            for i, z in enumerate(zoom_segments):
                nxt = f"z{i}"
                chains.append(
                    f"[{cur}][v_zoom]overlay=x=0:y=0:eof_action=pass:"
                    f"enable='between(t,{z['start']:.3f},{z['start'] + z['dur']:.3f})'[{nxt}]"
                )
                cur = nxt

        for i, it in enumerate(overlays, start=1):
            s, d = it["start"], it["dur"]
            fo = max(0.0, d - 0.35)
            if it["kind"] == "video":
                cmd += ["-t", f"{d:.2f}", "-i", it["path"]]
                chains.append(
                    f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={self.fps},"
                    f"format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={fo:.2f}:d=0.35:alpha=1,"
                    f"setpts=PTS-STARTPTS+{s:.3f}/TB[o{i}]"
                )
                pos_x, pos_y = "0", "0"
            else:
                cmd += ["-loop", "1", "-framerate", str(self.fps), "-t", f"{d:.2f}", "-i", it["path"]]
                chains.append(
                    f"[{i}:v]format=rgba,fade=t=in:st=0:d=0.35:alpha=1,fade=t=out:st={fo:.2f}:d=0.35:alpha=1,"
                    f"setpts=PTS-STARTPTS+{s:.3f}/TB[o{i}]"
                )
                slide = int(W * 0.04)
                ease = f"pow(1-min((t-{s:.3f})/0.45\\,1)\\,3)"  # ease-out cúbico
                if it["kind"] == "card":
                    pos_x = f"W-w-{margin_x}+{slide}*{ease}"
                else:
                    pos_x = f"{margin_x}-{slide}*{ease}"
                pos_y = str(margin_y)
            nxt = f"b{i}"
            chains.append(
                f"[{cur}][o{i}]overlay=x='{pos_x}':y='{pos_y}':eof_action=pass:"
                f"enable='between(t,{s:.3f},{s + d:.3f})'[{nxt}]"
            )
            cur = nxt

        if ass_file and ass_file.exists():
            chains.append(f"[{cur}]ass='{_ff_path(ass_file)}'[vout]")
            cur = "vout"
            
        # Audio Bleep (Censorship)
        if censor_segments:
            # Silence original audio in censor windows
            mute_expr = "+".join(f"between(t,{c['start']:.3f},{c['start']+c['dur']:.3f})" for c in censor_segments)
            chains.append(f"[0:a]volume='1-min(1,({mute_expr}))':eval=frame[a_muted]")
            # Generate continuous 1000Hz sine wave and only unmute during censor windows
            chains.append("sine=f=1000[bleep]")
            chains.append(f"[bleep]volume='0.15*min(1,({mute_expr}))':eval=frame[bleep_vol]")
            # Mix them together
            chains.append(f"[a_muted][bleep_vol]amix=inputs=2:duration=first[aout]")
            audio_map = "[aout]"

        if not chains:
            shutil.copy(base_video, out)
            return True

        script = out.with_suffix(".fx.txt")
        script.write_text(";\n".join(chains), encoding="utf-8")
        cmd += ["-filter_complex_script", str(script), "-map", f"[{cur}]", "-map", audio_map,
                *ENC_FINAL, "-c:a", "aac", "-movflags", "+faststart", str(out)]
        ok = self._run(cmd, f"Componiendo {len(overlays)} overlays" + (" + subtítulos" if ass_file else ""))
        script.unlink(missing_ok=True)
        return ok and out.exists()

    # ------------------------------------------------------------------ API principal
    def render(self, input_video: Path, plan: VideoEditingPlan, mapper: TimelineMapper, workdir: Path,
               out: Path, captions_provider: Optional[Callable[[Path], List[CaptionItem]]] = None,
               progress: ProgressCb = None) -> Dict:
        say = progress or (lambda m, p: None)

        say("Smart Cut con FFmpeg (eliminando silencios)...", 0.05)
        cut = self.cut_silences(input_video, mapper, workdir / "cut.mp4")

        captions: List[CaptionItem] = []
        ass_file = None
        if captions_provider:
            say("Transcribiendo audio para subtítulos sincronizados...", 0.30)
            captions = captions_provider(cut) or []
            if captions:
                W, H = probe_size(cut)
                ass_file = SubtitleGenerator.generate_ass(captions, workdir / "subs.ass", W, H)

        overlays = self.collect_overlays(plan, mapper)
        
        # Extraer segmentos de zoom y de censura basados en captions importantes
        zoom_segments = []
        censor_segments = []
        for cap in captions:
            dur = cap.end_sec - cap.start_sec
            if cap.highlight_words and dur >= 0.4:
                zoom_segments.append({"start": cap.start_sec, "dur": min(dur, 2.5)})
            if getattr(cap, "censor_words", None):
                censor_segments.append({"start": cap.start_sec, "dur": dur})
                
        say(f"Componiendo {len(overlays)} overlays, {len(zoom_segments)} jump-cuts y {len(censor_segments)} censuras...", 0.55)
        ok = self.compose(cut, overlays, ass_file, out, zoom_segments=zoom_segments, censor_segments=censor_segments)
        if not ok and ass_file:
            say("Reintentando sin subtítulos...", 0.8)
            ok = self.compose(cut, overlays, None, out, zoom_segments=zoom_segments, censor_segments=censor_segments)
        if not ok:
            say("Reintentando sin overlays...", 0.85)
            ok = self.compose(cut, [], ass_file, out)
        if not ok:
            shutil.copy(cut, out)
        return {"overlays": overlays, "captions": len(captions)}

    # ------------------------------------------------------------------ shorts
    def extract_vertical_short(self, video_path: Path, highlight: HighlightClip, output_dir: Path) -> Optional[Path]:
        duration = max(1.0, highlight.end_sec - highlight.start_sec)
        out_path = output_dir / f"short_{highlight.clip_id}_{video_path.stem[:40]}.mp4"
        fc = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,boxblur=22:6,crop=1080:1920[bg];"
              "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
              "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]")
        cmd = ["ffmpeg", "-y", "-ss", f"{highlight.start_sec:.2f}", "-i", str(video_path), "-t", f"{duration:.2f}",
               "-filter_complex", fc, "-map", "[v]", "-map", "0:a?", *ENC_FINAL, "-c:a", "aac",
               "-movflags", "+faststart", str(out_path)]
        return out_path if self._run(cmd, f"Short 9:16 '{highlight.title}'") and out_path.exists() else None

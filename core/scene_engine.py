"""Motor de Escenas (Scene Engine) para KAI Streamer.

Renderiza cada escena diseñada por el AI Director de forma modular:
- Modulación emocional de voz y entonación por escena (excited, surprised, serious, skeptical).
- Layouts de cámara reactivos:
    * "avatar_cam": Plano principal de KAI hablando al espectador.
    * "video_reaction": Video / B-Roll 100% en pantalla con KAI en PIP en esquina reaccionando en vivo.
    * "card_focus": Tarjeta Bento destacada con datos clave verificados y KAI en PIP.
    * "chat_debate": Pantalla de debate con overlay de chat y preguntas de la comunidad.
- Ensamble y concatenación instantánea y estable sin desbordamiento de memoria de FFmpeg.
"""

from __future__ import annotations

import asyncio
import math
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from config.settings import settings
from core.avatar_narrator import AvatarNarrator, DEFAULT_VOICE
from core.avatar_renderer import AvatarRenderer
from core.card_renderer import InfoCardRenderer
from core.chat_renderer import LiveChatRenderer
from core.director import DirectorBroadcastPlan, DirectorScene, SceneCard
from core.models import InfoCard
from core.orchestrator import AssetOrchestrator
from core.llm import safe_log


EMOTION_VOICE_MODULATION: Dict[str, Tuple[str, str]] = {
    "excited": ("+6%", "+3Hz"),
    "surprised": ("+4%", "+4Hz"),
    "serious": ("-4%", "-2Hz"),
    "skeptical": ("-3%", "-1Hz"),
    "confident": ("+0%", "+0Hz"),
    "humor": ("+5%", "+2Hz"),
}


class SceneEngine:
    """Motor de composición y renderizado escena por escena."""

    def __init__(
        self,
        workdir: Path,
        aspect_ratio: str = "16:9",
        voice: str = DEFAULT_VOICE,
        card_theme: str = "dark",
        cancel_event: Optional[Any] = None,
    ):
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.aspect_ratio = aspect_ratio
        self.is_vertical = aspect_ratio == "9:16"
        self.W, self.H = (1080, 1920) if self.is_vertical else (1920, 1080)
        self.voice = voice
        self.card_theme = card_theme
        self.cancel_event = cancel_event
        self.narrator = AvatarNarrator(voice=voice)
        self.card_renderer = InfoCardRenderer(self.W, self.H, theme=card_theme)
        self.chat_renderer = LiveChatRenderer(width=340 if not self.is_vertical else 300)
        self.orchestrator = AssetOrchestrator(target_dir=self.workdir / "assets")

    async def render_scene(
        self,
        scene: DirectorScene,
        avatar_clip: Optional[Path] = None,
        avatar_webm: Optional[Path] = None,
        bgm_path: Optional[Path] = None,
        chat_overlay_path: Optional[Path] = None,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> Path:
        """Renderiza una escena individual en su propio archivo MP4."""
        scene_dir = self.workdir / f"scene_{scene.scene_id}"
        scene_dir.mkdir(parents=True, exist_ok=True)
        scene_out = scene_dir / f"scene_{scene.scene_id}.mp4"

        if status_cb:
            status_cb(f"Dirigiendo Escena {scene.scene_id}: {scene.name} ({scene.type})")

        # 1. Síntesis de voz neural con modulación emocional
        speech_text = scene.speech.strip()
        if not speech_text:
            speech_text = "Dato mata relato, analicemos este punto a fondo."

        rate_mod, pitch_mod = EMOTION_VOICE_MODULATION.get(scene.emotion, ("+0%", "+0Hz"))
        audio_path = scene_dir / "voice.mp3"

        import edge_tts
        communicate = edge_tts.Communicate(speech_text, self.voice, rate=rate_mod, pitch=pitch_mod)
        sentence_boundaries = []
        with open(audio_path, "wb") as f_audio:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f_audio.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    s_sec = chunk["offset"] / 10_000_000
                    d_sec = chunk["duration"] / 10_000_000
                    sentence_boundaries.append((s_sec, s_sec + d_sec, chunk["text"].strip()))

        # Medir duración exacta del audio de la escena
        tts_duration = self._get_audio_duration(audio_path)
        # Usar el máximo entre la duración del TTS y el target del director
        # para garantizar que el video final respete la duración solicitada
        target_scene_dur = max(3.5, scene.duration_est) if scene.duration_est > 0 else tts_duration
        duration = max(tts_duration + 0.6, target_scene_dur)
        dur_str = f"{duration:.2f}"

        # 2. Descargar o seleccionar B-Roll temático para la escena
        broll_img = None
        if scene.type == "avatar_cam" or scene.camera == "hero_center":
            # Para planos de estudio donde el streamer habla de frente (intro, conclusiones y directos),
            # usar el cuarto/setup de estudio del streamer con desenfoque de profundidad realista
            studio_blur_path = Path("assets/streamer_studio_blur_9_16.jpg" if self.is_vertical else "assets/streamer_studio_blur_16_9.jpg")
            if studio_blur_path.exists():
                broll_img = studio_blur_path
            elif Path("assets/streamer_studio_room.jpg").exists():
                broll_img = Path("assets/streamer_studio_room.jpg")

        if not broll_img:
            broll_img = await self._get_scene_visual(scene.visual_query, scene_dir)

        # Si no se pudo obtener B-Roll o falló la descarga, NUNCA dejar la pantalla en negro:
        # Usar el fondo de estudio ambiental desenfocado en alta definición
        if not broll_img or not broll_img.exists():
            studio_blur_path = Path("assets/streamer_studio_blur_9_16.jpg" if self.is_vertical else "assets/streamer_studio_blur_16_9.jpg")
            if studio_blur_path.exists():
                broll_img = studio_blur_path
            elif Path("assets/streamer_studio_room.jpg").exists():
                broll_img = Path("assets/streamer_studio_room.jpg")

        # Generar clip de avatar con sincronización reactiva labial a la voz de la escena
        scene_avatar_clip = scene_dir / "kai_avatar_synced.mov"
        try:
            from core.avatar_renderer import AvatarRenderer
            rnd = AvatarRenderer()
            await asyncio.to_thread(
                rnd.render_reaction_clip,
                duration_sec=duration,
                out_path=scene_avatar_clip,
                audio_path=audio_path,
                fps=24
            )
        except Exception as exc:
            safe_log(f"[SceneEngine] Fallback a avatar clip base: {exc}")
            scene_avatar_clip = None

        # 3. Preparar tarjeta Bento si aplica
        card_img_path = None
        if scene.card:
            card_obj = InfoCard(
                card_id=f"sc_card_{scene.scene_id}",
                headline=scene.card.headline,
                claim=scene.card.body or scene.card.headline,
                search_query=scene.card.headline,
                body=scene.card.body,
                start_sec=0.8,
                end_sec=max(3.0, duration - 0.5),
                stat_value=scene.card.stat or "",
                verdict="supported",
                kind="cifra" if scene.card.stat else "dato",
            )
            card_img_path = scene_dir / f"card_{scene.scene_id}.png"
            self.card_renderer.render(card_obj, card_img_path)

        # 4. Generar subtítulos para la escena
        srt_path = self._generate_scene_subtitles(speech_text, duration, scene_dir, sentence_boundaries)

        # 5. Montar filtergraph de FFmpeg específico para el layout de la escena
        inputs: List[str] = []
        filter_parts: List[str] = []
        num_in = 0

        # Fondo
        if broll_img and broll_img.exists():
            if broll_img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(broll_img)])
            else:
                inputs.extend(["-t", dur_str, "-r", "25", "-stream_loop", "-1", "-i", str(broll_img)])
            filter_parts.append(
                f"[0:v]scale={self.W}:{self.H}:force_original_aspect_ratio=increase,crop={self.W}:{self.H},setsar=1[v_bg]"
            )
        else:
            inputs.extend(["-f", "lavfi", "-i", f"color=c=0x0a0a0c:s={self.W}x{self.H}:d={dur_str}:r=25"])
            filter_parts.append("[0:v]format=yuva420p[v_bg]")
        num_in += 1
        cur_v = "v_bg"

        # Aplicar velo oscuro sutil según layout
        dim_alpha = "0.45" if scene.type == "card_focus" else "0.20"
        filter_parts.append(f"[{cur_v}]drawbox=x=0:y=0:w={self.W}:h={self.H}:color=black@{dim_alpha}:t=fill[v_dim]")
        cur_v = "v_dim"

        # Avatar según layout de cámara
        av_file = scene_avatar_clip if (scene_avatar_clip and scene_avatar_clip.exists()) else (avatar_clip or avatar_webm)
        if av_file and Path(av_file).exists():
            inputs.extend(["-t", dur_str, "-r", "25", "-stream_loop", "-1", "-i", str(av_file)])
            av_idx = num_in
            num_in += 1

            if scene.camera == "hero_center" or scene.type == "avatar_cam":
                # Avatar protagonista (centro o primer plano dinámico)
                av_w = int(self.W * (0.55 if not self.is_vertical else 0.70))
                av_x = int((self.W - av_w) / 2)
                av_y = int(self.H - av_w + 30)
                filter_parts.append(
                    f"[{av_idx}:v]scale={av_w}:{av_w},format=rgba[avatar];"
                    f"[{cur_v}][avatar]overlay={av_x}:{av_y}:shortest=1[v_av]"
                )
            else:
                # Avatar en recuadro PIP en la esquina inferior derecha
                av_w = int(self.W * (0.26 if not self.is_vertical else 0.40))
                av_x = int(self.W - av_w - (45 if not self.is_vertical else 30))
                av_y = int(self.H - av_w - (45 if not self.is_vertical else 110))
                filter_parts.append(
                    f"[{av_idx}:v]scale={av_w}:{av_w},format=rgba[avatar];"
                    f"[{cur_v}][avatar]overlay={av_x}:{av_y}:shortest=1[v_av]"
                )
            cur_v = "v_av"

        # Overlay adicional según tipo de escena o si tiene tarjeta HUD
        if card_img_path and card_img_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(card_img_path)])
            c_idx = num_in
            num_in += 1
            card_x = 60 if not self.is_vertical else 40
            card_y = 60 if not self.is_vertical else int(self.H * 0.55)
            filter_parts.append(f"[{cur_v}][{c_idx}:v]overlay={card_x}:{card_y}:enable='between(t,0.5,{duration-0.4:.2f})'[v_card]")
            cur_v = "v_card"

        elif scene.type == "chat_debate" and chat_overlay_path and chat_overlay_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(chat_overlay_path)])
            ch_idx = num_in
            num_in += 1
            cx = 60 if not self.is_vertical else 30
            cy = int(self.H - 330) if not self.is_vertical else int(self.H * 0.72)
            filter_parts.append(f"[{cur_v}][{ch_idx}:v]overlay={cx}:{cy}:enable='between(t,0.5,{duration-0.3:.2f})'[v_chat]")
            cur_v = "v_chat"

        # Subtítulos con libass (Tamaño ergonómico y margen óptimo para no chocar con avatar PIP)
        if srt_path and srt_path.exists():
            esc_srt = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
            sub_size = 18 if self.is_vertical else 14
            margin_v = 40 if self.is_vertical else 20
            filter_parts.append(
                f"[{cur_v}]subtitles='{esc_srt}':force_style='FontName=Segoe UI,FontSize={sub_size},Bold=1,PrimaryColour=&H00FFFFFF,BorderStyle=3,OutlineColour=&HB2000000,MarginV={margin_v}'[v_sub]"
            )
            cur_v = "v_sub"

        # Título superior / HUD y Marca de Agua Ángel R sutil
        font_path = "C\\:/Windows/Fonts/segoeuib.ttf"
        clean_tag = re.sub(r"[^\w\s-]", "", scene.name).strip()[:30] or "EN VIVO"
        hud_fontsize = 18 if self.is_vertical else 20
        wm_fontsize = 16 if self.is_vertical else 18
        filter_parts.append(
            f"[{cur_v}]drawtext=fontfile='{font_path}':text='● EN VIVO  |  {clean_tag.upper()}':fontcolor=white:fontsize={hud_fontsize}:x=44:y=34:box=1:boxcolor=black@0.65:boxborderw=8,"
            f"drawtext=fontfile='{font_path}':text='Ángel R':fontcolor=white@0.35:fontsize={wm_fontsize}:x=w-tw-44:y=34[v_out]"
        )

        # Audio mix: voz de la escena + BGM sutil + SFX de transición
        # Aseguramos que la pista de voz llene la duración si es necesario con apad
        inputs.extend(["-i", str(audio_path)])
        voice_in_idx = num_in
        num_in += 1
        audio_filter_parts = [
            f"[{voice_in_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,apad=whole_dur={dur_str}[a_voice]"
        ]
        audio_mix_inputs = ["[a_voice]"]

        if bgm_path and bgm_path.exists():
            inputs.extend(["-t", dur_str, "-stream_loop", "-1", "-i", str(bgm_path)])
            bgm_idx = num_in
            num_in += 1
            audio_filter_parts.append(f"[{bgm_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=0.06[a_bgm]")
            audio_mix_inputs.append("[a_bgm]")

        sfx_path = self._get_sfx_path(scene.sfx)
        if sfx_path and sfx_path.exists():
            inputs.extend(["-i", str(sfx_path)])
            sfx_idx = num_in
            num_in += 1
            audio_filter_parts.append(f"[{sfx_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,adelay=delays=150:all=1,volume=0.35[a_sfx]")
            audio_mix_inputs.append("[a_sfx]")

        inputs_tags = "".join(audio_mix_inputs)
        # Usamos duration=longest o first según los inputs, pero con dur_str acotado en -t dur_str
        audio_filter_parts.append(f"{inputs_tags}amix=inputs={len(audio_mix_inputs)}:duration=longest:dropout_transition=2[a_out]")

        full_filter = ";\n".join(filter_parts + audio_filter_parts)
        filter_file = scene_dir / "scene_filter.txt"
        filter_file.write_text(full_filter, encoding="utf-8")

        cmd = [
            "ffmpeg", "-y",
            "-threads", "2",
            *inputs,
            "-filter_complex_script", str(filter_file),
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-x264-params", "threads=3:rc-lookahead=10",
            "-c:a", "aac",
            "-b:a", "256k",
            "-t", dur_str,
            str(scene_out),
        ]

        if self.cancel_event and self.cancel_event.is_set():
            raise asyncio.CancelledError("Render cancelado.")

        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await proc.communicate()
        except asyncio.CancelledError:
            try:
                proc.kill()
            except Exception:
                pass
            raise

        if self.cancel_event and self.cancel_event.is_set():
            raise asyncio.CancelledError("Render cancelado tras ejecución de escena.")

        if not scene_out.exists() or scene_out.stat().st_size < 10000:
            err_msg = stderr.decode(errors="replace") if stderr else "No stderr"
            print(f"[SceneEngine] ERROR FFmpeg escena {scene.scene_id}:\n{err_msg}")
            raise RuntimeError(f"Fallo al renderizar la escena {scene.scene_id}: {err_msg[-300:]}")

        safe_log(f"[SceneEngine] Escena {scene.scene_id} ({scene.name}) lista: {duration:.1f}s")
        return scene_out

    async def assemble_broadcast(
        self,
        plan: DirectorBroadcastPlan,
        avatar_clip: Optional[Path] = None,
        avatar_webm: Optional[Path] = None,
        output_file: Optional[Path] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """Renderiza todas las escenas y las concatena en el master broadcast final."""
        bgm_path = Path("assets/audio/bgm_streamer.wav")

        # Chat overlay pre-generado
        chat_overlay_path = self.workdir / "chat_overlay.png"
        raw_comments = plan.chat_comments or [
            {"user": "TechFan", "badge": "VIP", "text": "¡Increíble análisis KAI!"},
            {"user": "DevLucas", "badge": "SUB", "text": "Dato mata relato siempre."},
        ]
        formatted = [
            (f"[{c.get('badge', 'VIP')}] @{c.get('user', 'Viewer')}", "cyan" if i % 2 == 0 else "amber", c.get("text", "¡Gran dato!"))
            for i, c in enumerate(raw_comments[:3])
        ]
        self.chat_renderer.render(formatted, chat_overlay_path)

        scene_files: List[Path] = []
        total_scenes = len(plan.scenes)

        for i, scene in enumerate(plan.scenes):
            if self.cancel_event and self.cancel_event.is_set():
                safe_log(f"[SceneEngine] Cancelación solicitada antes de la escena {scene.scene_id}. Abortando render.")
                raise asyncio.CancelledError("Render de transmisión cancelado por el usuario.")

            pct = 70.0 + (float(i) / max(1, total_scenes)) * 18.0
            if progress_cb:
                progress_cb(pct, f"Grabando Escena {scene.scene_id}/{total_scenes}: {scene.name} ({scene.type})...")

            sc_file = await self.render_scene(
                scene=scene,
                avatar_clip=avatar_clip,
                avatar_webm=avatar_webm,
                bgm_path=bgm_path,
                chat_overlay_path=chat_overlay_path,
            )
            scene_files.append(sc_file)

        # Concatenación final instantánea
        if progress_cb:
            progress_cb(90.0, "Concatenando y masterizando transmisión final...")

        concat_list_file = self.workdir / "concat_scenes.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for sc in scene_files:
                f.write(f"file '{sc.resolve().as_posix()}'\n")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(output_file),
        ]

        proc = await asyncio.create_subprocess_exec(*concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()

        if not output_file.exists() or output_file.stat().st_size < 50000:
            raise RuntimeError("Error al concatenar las escenas de la transmisión.")

        safe_log(f"[SceneEngine] Transmisión completa masterizada con {total_scenes} escenas en: {output_file}")
        return output_file

    def _get_audio_duration(self, audio_path: Path) -> float:
        try:
            res = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
                capture_output=True, text=True, check=True
            )
            return float(res.stdout.strip())
        except Exception:
            return 8.0

    async def _get_scene_visual(self, query: str, scene_dir: Path) -> Optional[Path]:
        """Obtiene un recurso visual de stock abierto para la escena."""
        try:
            from core.models import BRollCue
            cue = BRollCue(
                cue_id=f"scene_cue_{abs(hash(query)) % 10000}",
                start_sec=0.0,
                end_sec=10.0,
                concept=query or "technology abstract",
                search_query_en=query or "technology abstract",
                reasoning="Escena visual de fondo",
            )
            res = await self.orchestrator._resolve_single_cue(cue)
            if res.local_file_path and Path(res.local_file_path).exists():
                return Path(res.local_file_path)
        except Exception as exc:
            safe_log(f"[SceneEngine] No se pudo descargar visual para '{query}': {exc}")
        return None

    def _get_sfx_path(self, sfx_name: str) -> Optional[Path]:
        sfx_map = {
            "whoosh": Path("assets/audio/whoosh.wav"),
            "chime": Path("assets/audio/chime.wav"),
            "impact": Path("assets/audio/whoosh.wav"),
        }
        return sfx_map.get(sfx_name.lower())

    def _generate_scene_subtitles(
        self,
        speech: str,
        duration: float,
        scene_dir: Path,
        boundaries: Optional[List[tuple]] = None
    ) -> Optional[Path]:
        srt_path = scene_dir / "scene_subtitles.srt"
        srt_lines = []

        def _fmt_srt(t: float) -> str:
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t - int(t)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        # 1. Si tenemos timestamps precisos de Edge TTS por oración
        if boundaries and len(boundaries) > 0:
            idx = 1
            for st, en, text in boundaries:
                # Subdividir frases largas si tienen más de 7 palabras para que no ocupen toda la pantalla
                w_list = text.split()
                if len(w_list) > 6:
                    mid = len(w_list) // 2
                    dur_half = (en - st) / 2
                    sub1 = " ".join(w_list[:mid]).strip().replace(":", "")
                    sub2 = " ".join(w_list[mid:]).strip().replace(":", "")
                    srt_lines.append(f"{idx}\n{_fmt_srt(st)} --> {_fmt_srt(st + dur_half)}\n{sub1}\n")
                    idx += 1
                    srt_lines.append(f"{idx}\n{_fmt_srt(st + dur_half)} --> {_fmt_srt(en)}\n{sub2}\n")
                    idx += 1
                else:
                    clean = text.strip().replace(":", "")
                    srt_lines.append(f"{idx}\n{_fmt_srt(st)} --> {_fmt_srt(en)}\n{clean}\n")
                    idx += 1
            srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
            return srt_path

        # 2. Fallback ponderado por caracteres
        words = speech.split()
        if not words:
            return None
        chunk_size = 4
        sub_chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        if not sub_chunks:
            return None

        start_lead = 0.12
        total_chars = sum(len(c) for c in sub_chunks) or 1
        active_speech_time = max(2.0, duration - 0.45)

        curr_t = start_lead
        for idx, chunk in enumerate(sub_chunks):
            chunk_weight = len(chunk) / total_chars
            chunk_dur = max(0.85, active_speech_time * chunk_weight)
            st = curr_t
            en = min(duration - 0.1, curr_t + chunk_dur)
            curr_t = en

            clean = chunk.strip().replace(":", "")
            srt_lines.append(f"{idx + 1}\n{_fmt_srt(st)} --> {_fmt_srt(en)}\n{clean}\n")

        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
        return srt_path

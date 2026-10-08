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
    "excited": ("+1%", "+2Hz"),
    "surprised": ("+0%", "+2Hz"),
    "serious": ("-2%", "-1Hz"),
    "skeptical": ("-2%", "-1Hz"),
    "confident": ("+0%", "+0Hz"),
    "humor": ("+1%", "+1Hz"),
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

        # 0. Cache inteligente de escenas (Reanudar sin rehacer lo que ya está listo)
        thumb_path = scene_dir / "scene_thumb.jpg"
        if scene_out.exists() and scene_out.stat().st_size > 50000:
            if not thumb_path.exists():
                try:
                    import subprocess
                    subprocess.run([
                        "ffmpeg", "-y", "-ss", "0.5", "-i", str(scene_out),
                        "-vframes", "1", "-q:v", "3", str(thumb_path)
                    ], capture_output=True, timeout=5)
                except Exception:
                    pass
            safe_log(f"[SceneEngine] Reusando escena {scene.scene_id} ({scene.name}) ya renderizada.")
            if status_cb:
                status_cb(f"Escena {scene.scene_id} restaurada desde caché.")
            return scene_out

        if status_cb:
            status_cb(f"Dirigiendo Escena {scene.scene_id}: {scene.name} ({scene.type})")

        # 1. Síntesis de voz neural con modulación emocional y pronunciación fluida
        speech_text = scene.speech.strip()
        if not speech_text:
            speech_text = "Dato mata relato, analicemos este punto a fondo."

        from utils.speech_normalizer import normalize_speech_for_tts
        tts_speech_text = normalize_speech_for_tts(speech_text)

        rate_mod, pitch_mod = EMOTION_VOICE_MODULATION.get(scene.emotion, ("+0%", "+0Hz"))
        audio_path = scene_dir / "voice.mp3"

        import edge_tts
        communicate = edge_tts.Communicate(tts_speech_text, self.voice, rate=rate_mod, pitch=pitch_mod)
        sentence_boundaries = []
        with open(audio_path, "wb") as f_audio:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f_audio.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    s_sec = chunk["offset"] / 10_000_000
                    d_sec = chunk["duration"] / 10_000_000
                    sentence_boundaries.append((s_sec, s_sec + d_sec, chunk["text"].strip()))

        # Medir duración inicial y aplicar silenceremove inteligente para eliminar pausas muertas y silencios largos
        trimmed_audio_path = scene_dir / "voice_trimmed.mp3"
        try:
            trim_cmd = [
                "ffmpeg", "-y", "-i", str(audio_path),
                "-af", "silenceremove=stop_periods=-1:stop_duration=0.22:stop_threshold=-32dB:start_periods=1:start_duration=0.01:start_threshold=-32dB",
                str(trimmed_audio_path),
            ]
            res_trim = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=15)
            if res_trim.returncode == 0 and trimmed_audio_path.exists() and trimmed_audio_path.stat().st_size > 1000:
                audio_path = trimmed_audio_path
        except Exception as exc_trim:
            safe_log(f"[SceneEngine] Fallback silenceremove: {exc_trim}")

        # Medir duración exacta del audio real de la escena (sin silencios muertos)
        tts_duration = self._get_audio_duration(audio_path)
        # La escena se ajusta de forma milimétrica al audio hablado para evitar silencios y pausas vacías
        duration = max(3.0, round(tts_duration + 0.15, 2))
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
            # Priorizar video en movimiento para todas las escenas con B-Roll, reacción, noticias o contexto
            is_video_reaction = (scene.type != "avatar_cam") or ("video" in (scene.visual_query or "").lower())
            broll_img = await self._get_scene_visual(scene.visual_query, scene_dir, is_video_scene=is_video_reaction)

        # 2b. Descargar segundo clip o ángulo complementario si está especificado en la escena
        broll_img2 = None
        vq2 = getattr(scene, "visual_query2", "") or (scene.visual_queries[1] if len(getattr(scene, "visual_queries", [])) > 1 else "")
        if vq2 and vq2.strip() and vq2.strip().lower() != (scene.visual_query or "").strip().lower():
            try:
                broll_img2 = await self._get_scene_visual(vq2, scene_dir, is_video_scene=True)
            except Exception as _e:
                safe_log(f"[SceneEngine] Fallback en segundo clip: {_e}")

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

        # 3b. Preparar chips / pastillas referenciales dinámicas (países, marcas, entidades)
        chips_img_path = None
        if getattr(scene, "chips", None) and scene.chips:
            out_chip_path = scene_dir / f"chips_{scene.scene_id}.png"
            chips_img_path = self._render_chips_overlay(scene.chips, out_chip_path)

        # 4. Generar subtítulos para la escena
        srt_path = self._generate_scene_subtitles(speech_text, duration, scene_dir, sentence_boundaries)

        # 5. Montar filtergraph de FFmpeg específico para el layout de la escena
        inputs: List[str] = []
        filter_parts: List[str] = []
        num_in = 0

        # Fondo con soporte de 1 o 2 videos secuenciales en la misma escena
        has_two_clips = bool(broll_img2 and broll_img2.exists())
        mid_cut_sec = round(duration * 0.5, 2) if has_two_clips else 0.0

        if broll_img and broll_img.exists():
            if broll_img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(broll_img)])
            else:
                inputs.extend(["-t", dur_str, "-r", "25", "-stream_loop", "-1", "-i", str(broll_img)])
            filter_parts.append(
                f"[0:v]scale={self.W}:{self.H}:force_original_aspect_ratio=increase,crop={self.W}:{self.H},setsar=1[v_bg1]"
            )
            cur_v = "v_bg1"
        else:
            inputs.extend(["-f", "lavfi", "-i", f"color=c=0x0a0a0c:s={self.W}x{self.H}:d={dur_str}:r=25"])
            filter_parts.append("[0:v]format=yuva420p[v_bg1]")
            cur_v = "v_bg1"
        num_in += 1

        if has_two_clips:
            # Segundo clip complementario que entra en la segunda mitad de la escena
            if broll_img2.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(broll_img2)])
            else:
                inputs.extend(["-t", dur_str, "-r", "25", "-stream_loop", "-1", "-i", str(broll_img2)])
            broll2_idx = num_in
            num_in += 1
            filter_parts.append(
                f"[{broll2_idx}:v]scale={self.W}:{self.H}:force_original_aspect_ratio=increase,crop={self.W}:{self.H},setsar=1[v_bg2];"
                f"[{cur_v}][v_bg2]overlay=0:0:enable='gte(t,{mid_cut_sec})'[v_bg_combined]"
            )
            cur_v = "v_bg_combined"

        # Desenfoque temporal dinámico: si hay tarjeta, solo desenfocar durante su aparición (máx 5.0s)
        # para que después el video de fondo se vea 100% nítido en todo su esplendor
        card_duration = min(5.0, duration - 0.8) if (card_img_path and card_img_path.exists()) else 0.0

        if card_duration > 0:
            # Fondo nítido + capa desenfocada activa solo durante los 5s de la tarjeta
            filter_parts.append(f"[{cur_v}]split[v_crisp][v_to_blur];[v_to_blur]boxblur=5:2,drawbox=x=0:y=0:w={self.W}:h={self.H}:color=black@0.45:t=fill[v_blurred];[v_crisp][v_blurred]overlay=0:0:enable='between(t,0.4,{0.4 + card_duration:.2f})'[v_dim]")
        else:
            filter_parts.append(f"[{cur_v}]drawbox=x=0:y=0:w={self.W}:h={self.H}:color=black@0.15:t=fill[v_dim]")
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

        # Overlay adicional según tipo de escena o si tiene tarjeta HUD (máximo 5 segundos de visibilidad)
        if card_img_path and card_img_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(card_img_path)])
            c_idx = num_in
            num_in += 1
            card_x = 85 if not self.is_vertical else 30
            card_y = 190 if not self.is_vertical else int(self.H * 0.40)
            card_end = 0.5 + card_duration
            filter_parts.append(f"[{cur_v}][{c_idx}:v]overlay={card_x}:{card_y}:enable='between(t,0.5,{card_end:.2f})'[v_card]")
            cur_v = "v_card"

        elif scene.type == "chat_debate" and chat_overlay_path and chat_overlay_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(chat_overlay_path)])
            ch_idx = num_in
            num_in += 1
            cx = 60 if not self.is_vertical else 30
            cy = int(self.H - 330) if not self.is_vertical else int(self.H * 0.72)
            filter_parts.append(f"[{cur_v}][{ch_idx}:v]overlay={cx}:{cy}:enable='between(t,0.5,{duration-0.3:.2f})'[v_chat]")
            cur_v = "v_chat"

        # Overlay de chips / pastillas referenciales dinámicas sincronizadas con la tarjeta (máximo 5s)
        if chips_img_path and chips_img_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(chips_img_path)])
            chp_idx = num_in
            num_in += 1
            chip_x = 85 if not self.is_vertical else 30
            chip_y = (190 + 330 + 16) if (card_img_path and not self.is_vertical) else (190 if not self.is_vertical else int(self.H * 0.45))
            chip_end = (0.5 + card_duration) if card_duration > 0 else (duration - 0.3)
            filter_parts.append(f"[{cur_v}][{chp_idx}:v]overlay={chip_x}:{chip_y}:enable='between(t,0.6,{chip_end:.2f})'[v_chips]")
            cur_v = "v_chips"

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
            "-threads", "4",
            *inputs,
            "-filter_complex_script", str(filter_file),
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-x264-params", "threads=4:rc-lookahead=10",
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

        # Extraer miniatura visual de alta definición para el monitor en vivo del frontend
        thumb_path = scene_dir / "scene_thumb.jpg"
        try:
            import subprocess
            subprocess.run([
                "ffmpeg", "-y", "-ss", "0.5", "-i", str(scene_out),
                "-vframes", "1", "-q:v", "3", str(thumb_path)
            ], capture_output=True, timeout=5)
        except Exception:
            pass

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

        # Liberar inmediatamente archivos temporales pesados de las escenas (.mov intermedios)
        # conservando el video master, thumbnails y metadata intactos
        try:
            for sc in scene_files:
                sc_dir = sc.parent
                for mov in sc_dir.glob("*.mov"):
                    try: mov.unlink()
                    except Exception: pass
            # Limpiar avatar base intermedio del workdir si existe
            for mov in self.workdir.glob("*.mov"):
                try: mov.unlink()
                except Exception: pass
        except Exception as _e_clean:
            safe_log(f"[SceneEngine] Limpieza post-render: {_e_clean}")

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

    async def _get_scene_visual(self, query: str, scene_dir: Path, is_video_scene: bool = False) -> Optional[Path]:
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
                asset_type="video" if is_video_scene else "photo",
            )
            res = await self.orchestrator._resolve_single_cue(cue)
            if res.local_file_path and Path(res.local_file_path).exists():
                return Path(res.local_file_path)
        except Exception as exc:
            safe_log(f"[SceneEngine] No se pudo descargar visual para '{query}': {exc}")
    def _render_chips_overlay(self, chips: List[str], out_path: Path) -> Optional[Path]:
        """Renderiza una hilera horizontal de pastillas (chips) con banderas/iconos para referencias dinámicas."""
        if not chips:
            return None
        import io
        import urllib.request
        from PIL import Image, ImageDraw, ImageFont, ImageFilter

        scale = 2
        pill_h = 36 * scale
        pad_x = 16 * scale
        gap = 12 * scale

        COUNTRY_CODES = {
            "estados unidos": "us", "ee.uu": "us", "eeuu": "us", "usa": "us", "us": "us",
            "china": "cn", "cn": "cn",
            "argentina": "ar", "ar": "ar",
            "españa": "es", "espana": "es", "es": "es",
            "colombia": "co", "co": "co",
            "méxico": "mx", "mexico": "mx", "mx": "mx",
            "chile": "cl", "cl": "cl",
            "brasil": "br", "brazil": "br", "br": "br",
            "alemania": "de", "germany": "de", "de": "de",
            "reino unido": "gb", "uk": "gb", "inglaterra": "gb", "gb": "gb",
            "francia": "fr", "fr": "fr",
            "japón": "jp", "japon": "jp", "jp": "jp",
            "italia": "it", "it": "it",
            "canadá": "ca", "canada": "ca", "ca": "ca",
            "rusia": "ru", "ru": "ru",
            "australia": "au", "au": "au",
            "perú": "pe", "peru": "pe", "pe": "pe",
        }

        flags_dir = Path("assets/flags_cache")
        flags_dir.mkdir(parents=True, exist_ok=True)

        def _get_flag_img(country_code: str, target_h: int) -> Optional[Image.Image]:
            cache_file = flags_dir / f"{country_code}.png"
            if not cache_file.exists():
                try:
                    url = f"https://flagcdn.com/w80/{country_code}.png"
                    req = urllib.request.Request(url, headers={"User-Agent": "AetherCut-Studio/2.0"})
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        cache_file.write_bytes(resp.read())
                except Exception:
                    pass
            if cache_file.exists():
                try:
                    im = Image.open(cache_file).convert("RGBA")
                    tw = int(im.width * (target_h / im.height))
                    res = im.resize((tw, target_h), Image.LANCZOS)
                    # Mascara redondeada sutil para la bandera
                    fmask = Image.new("L", (tw, target_h), 0)
                    ImageDraw.Draw(fmask).rounded_rectangle((0, 0, tw - 1, target_h - 1), radius=4 * scale, fill=255)
                    flag_rounded = Image.new("RGBA", (tw, target_h), (0, 0, 0, 0))
                    flag_rounded.paste(res, (0, 0), fmask)
                    return flag_rounded
                except Exception:
                    pass
            return None

        f_font = None
        for fn in ["segoeuib.ttf", "arialbd.ttf", "seguiemj.ttf"]:
            p = Path("C:/Windows/Fonts") / fn
            if p.exists():
                try:
                    f_font = ImageFont.truetype(str(p), 16 * scale)
                    break
                except Exception:
                    pass
        if not f_font:
            f_font = ImageFont.load_default()

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        pills_data = []
        flag_h = int(18 * scale)

        for c in chips[:6]:
            raw = str(c).strip()
            if not raw:
                continue

            # Detectar si hay bandera emoji o código de 2 letras
            clean_name = raw
            c_code = None

            # 1. Buscar código al inicio (ej: 'us Estados Unidos', 'CN China')
            m_code = re.match(r"^([A-Za-z]{2})\s+(.+)$", raw)
            if m_code and m_code.group(1).lower() in COUNTRY_CODES:
                c_code = COUNTRY_CODES[m_code.group(1).lower()]
                clean_name = m_code.group(2).strip()
            else:
                # 2. Buscar por nombre de país en el texto
                low_raw = raw.lower()
                for k, code_val in COUNTRY_CODES.items():
                    if k in low_raw:
                        c_code = code_val
                        break
                # Limpiar posibles emojis rotos o caracteres basura
                clean_name = re.sub(r"^[A-Za-z]{2}\s+", "", clean_name).strip()

            flag_img = _get_flag_img(c_code, flag_h) if c_code else None
            txt_w = int(probe.textlength(clean_name, font=f_font))
            extra_w = (flag_img.width + int(8 * scale)) if flag_img else 0
            w = int(txt_w + extra_w + (pad_x * 2))
            pills_data.append((clean_name, flag_img, w))

        if not pills_data:
            return None

        total_w = sum(w for _, _, w in pills_data) + (len(pills_data) - 1) * gap
        margin = 16 * scale
        W = total_w + (margin * 2)
        H = pill_h + (margin * 2)

        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        cur_x = margin
        for name_txt, f_img, w in pills_data:
            rect = (cur_x, margin, cur_x + w, margin + pill_h)
            # Pastilla obsidian dark con borde suave
            d.rounded_rectangle(rect, radius=pill_h // 2, fill=(18, 18, 22, 245), outline=(255, 255, 255, 60), width=1 * scale)
            content_x = cur_x + pad_x
            if f_img:
                f_y = margin + ((pill_h - f_img.height) // 2)
                im.paste(f_img, (content_x, f_y), f_img)
                content_x += f_img.width + int(8 * scale)
            d.text((content_x, margin + (pill_h // 2)), name_txt, font=f_font, fill=(255, 255, 255, 255), anchor="lm")
            cur_x += w + gap

        # Sombra suave difusa
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        cur_x = margin
        for _, _, w in pills_data:
            s_draw.rounded_rectangle((cur_x, margin + 4, cur_x + w, margin + pill_h + 4), radius=pill_h // 2, fill=(0, 0, 0, 160))
            cur_x += w + gap
        shadow = shadow.filter(ImageFilter.GaussianBlur(6 * scale))

        comp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        comp.paste(shadow, (0, 0), shadow)
        comp.paste(im, (0, 0), im)

        final_w = W // scale
        final_h = H // scale
        comp = comp.resize((final_w, final_h), Image.LANCZOS)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        comp.save(out_path, "PNG")
        return out_path

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

import re
from pathlib import Path
from typing import List

from core.models import CaptionItem


def _ass_time(sec: float) -> str:
    cs = int(round(max(0.0, sec) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _srt_time(sec: float) -> str:
    ms = int(round(max(0.0, sec) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


class SubtitleGenerator:
    """Subtítulos SRT y ASS. El ASS usa la resolución real del video para que el tamaño sea correcto."""

    @staticmethod
    def generate_srt(captions: List[CaptionItem], output_path: Path) -> Path:
        lines = []
        for i, c in enumerate(captions, start=1):
            lines += [str(i), f"{_srt_time(c.start_sec)} --> {_srt_time(c.end_sec)}", c.text.strip(), ""]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    @staticmethod
    def generate_ass(captions: List[CaptionItem], output_path: Path, width: int = 1920, height: int = 1080) -> Path:
        size = max(28, int(height * 0.052))
        outline = max(2, round(height * 0.0035))
        margin_v = int(height * 0.075)
        # Colores ASS en &HAABBGGRR: blanco, contorno negro, sombra semitransparente.
        header = f"""[Script Info]
Title: AetherCut captions
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Segoe UI,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,{outline},{max(1, outline // 2)},2,{int(width*0.08)},{int(width*0.08)},{margin_v},1
Style: Main2,Segoe UI,{size},&H0055FF55,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,{outline},{max(1, outline // 2)},2,{int(width*0.08)},{int(width*0.08)},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        import random
        emojis = ["🔥", "💡", "🚀", "💥", "⚡", "👀", "💰", "📈"]
        
        for c in captions:
            text = _escape(c.text.strip())
            
            # Censor words
            for cw in getattr(c, "censor_words", []):
                cw_esc = _escape(cw)
                safe_word = cw_esc[0] + "*" * (len(cw_esc)-2) + cw_esc[-1] if len(cw_esc) > 2 else "**"
                text = re.sub(rf"(?i)\b({re.escape(cw_esc)})\b", safe_word, text)
                
            # Highlight words & Emojis
            for hw in c.highlight_words:
                hw = _escape(hw)
                if hw:
                    emoji = random.choice(emojis)
                    color = "&H24BFFB&" if getattr(c, "speaker_id", 1) == 1 else "&HFB24BF&"
                    text = re.sub(rf"(?i)\b({re.escape(hw)})\b", rf"{emoji} {{\\c{color}}}\1{{\\c&HFFFFFF&}}", text, count=1)
            
            # entrada suave: pequeño pop de escala + fade
            fx = r"{\fad(80,60)\fscx92\fscy92\t(0,120,\fscx100\fscy100)}"
            style = "Main" if getattr(c, "speaker_id", 1) == 1 else "Main2"
            events.append(f"Dialogue: 0,{_ass_time(c.start_sec)},{_ass_time(c.end_sec)},{style},,0,0,0,,{fx}{text}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
        return output_path

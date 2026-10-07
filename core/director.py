"""Director de IA para KAI Streamer.

En lugar de generar un texto plano y continuo, el Director de IA planifica y dirige
una producción audiovisual completa estructurada en escenas cronometradas,
asignando para cada una:
- Tipo de escena (avatar_cam, video_reaction, card_focus, chat_debate, breaking_news)
- Emoción y entonación de KAI (excited, surprised, serious, skeptical, confident)
- Layout de cámara (hero_center, pip_corner, split_screen)
- Recurso visual (término de búsqueda de video/broll o contenido de tarjeta Bento)
- Efecto sonoro de transición (whoosh, chime, impact, glitch)
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from core.llm import LLMClient, safe_log


@dataclass
class SceneCard:
    headline: str
    body: str
    badge: str = "DATO CLAVE"
    stat: str = ""


@dataclass
class DirectorScene:
    scene_id: int
    name: str
    type: str  # avatar_cam, video_reaction, card_focus, chat_debate, breaking_news
    emotion: str  # excited, surprised, serious, skeptical, confident, humor
    camera: str  # hero_center, pip_corner, split_screen
    speech: str
    visual_query: str = ""
    card: Optional[SceneCard] = None
    sfx: str = "whoosh"  # whoosh, chime, impact, alert, none
    duration_est: float = 10.0


@dataclass
class DirectorBroadcastPlan:
    title: str
    topic: str
    style: str
    scenes: List[DirectorScene] = field(default_factory=list)
    chat_comments: List[Dict[str, str]] = field(default_factory=list)
    total_est_duration: float = 0.0


DIRECTOR_SYSTEM_PROMPT = """Eres el DIRECTOR DE TELEVISIÓN Y STREAMING con Inteligencia Artificial de KAI.
Tu misión no es solo escribir un monólogo, sino DIRIGIR UNA PRODUCCIÓN AUDIOVISUAL COMPLETA.

Debes dividir la emisión en EXACTAMENTE {num_scenes} ESCENAS según la duración solicitada ({duration_target} segundos = {duration_label}).

==============================================================================
REQUISITO CRÍTICO E INNEGOCIABLE DE DURACIÓN:
==============================================================================
- Duración total objetivo: {duration_target} segundos ({duration_label}).
- Número de escenas: {num_scenes}.
- Cada escena debe durar aproximadamente {seconds_per_scene} segundos de narración hablada.
- CADA campo "speech" DEBE contener MÍNIMO {words_per_scene} PALABRAS de texto hablado.
- El total de TODAS las escenas sumadas debe dar aproximadamente {total_words} PALABRAS.
- Ritmo de lectura: 140 palabras por minuto (2.33 palabras por segundo).
- Si la duración es de 3 minutos o más, es OBLIGATORIO desarrollar cada escena con argumentos completos,
  contexto histórico, datos precisos, ejemplos concretos, comparaciones y reflexiones. NO RESUMAS.
- RITMO AUDIOVISUAL DINÁMICO: Ningún plano ni fondo debe permanecer estático por mucho tiempo. Cada escena debe cambiar de perspectiva: alternar entre el gancho directo del avatar, tomas de B-Roll documental reactivo en pantalla completa, tarjetas Bento con cifras duras y momentos de debate.
- NUNCA escribas frases cortas de 1-2 líneas como speech. Cada speech debe ser un PÁRRAFO COMPLETO Y NUTRIDO.

REGLAS DE GANCHO Y ENTRADA (PROHIBIDO SALUDOS CLICHÉ):
- NUNCA comiences diciendo "¡Hola a todos!", "Bienvenidos a mi canal", "En este video vamos a ver...", o saludos genéricos de relleno.
- COMIENZA SIEMPRE con un GANCHO DIRECTO E IMPACTANTE: una pregunta provocadora, una afirmación contundente, una paradoja fascinante o un dato duro que sacuda al espectador desde el segundo 0.
- Ejemplo de inicio excelente: "¿Sabías que tu perro percibe el mundo en 300 millones de receptores olfativos mientras tú apenas alcanzas 6 millones? Lo que la ciencia acaba de descubrir sobre los sentidos caninos desafía todo lo que creíamos saber..."

REGLAS PARA DATOS, ESTADÍSTICAS Y COMPARATIVAS (TARJETAS BENTO HUD):
- SIEMPRE que se mencione una cifra, porcentaje, estadística, comparativa (ej: perro vs humano, velocidad, capacidad, año récord), o hecho verificable, la escena DEBE ser de tipo "card_focus" O incluir obligatoriamente el objeto "card".
- El objeto "card" debe tener:
  * "headline": Título corto y concreto del dato o comparativa (ej: "Capacidad Olfativa: Perro vs Humano").
  * "stat": La cifra o métrica clave destacada (ej: "300M vs 6M", "99.8%", "+450%").
  * "body": Explicación sintética y contundente del dato con fuentes contrastadas.
  * "badge": "ESTADÍSTICA", "DATO CLAVE", "COMPARATIVA" o "CONFIRMADO".
- De esta manera el espectador ve el avatar hablando pero al mismo tiempo tiene al lado la tarjeta gráfica animada mostrando los números reales y la comparativa en pantalla.

REGLAS DE TONO Y ESTILO (NATURALIDAD PURA):
- PROHIBIDO mencionar o insinuar que eres una "inteligencia artificial", un "modelo de lenguaje" o un "algoritmo".
- PROHIBIDO hacer auto-promociones extrañas, cuñas publicitarias o inventar marcas comerciales.
- Habla como un streamer, analista y divulgador humano riguroso y apasionado. El cierre debe ser un balance reflexivo del tema, invitando a debatir con argumentos sanos.

REGLAS DE SELECCIÓN VISUAL (B-ROLL & IMÁGENES REALES DE ALTA CALIDAD):
- El campo "visual_query" para cada escena DEBE ser en inglés y describir una ESCENA REALISTA, FOTOGRÁFICA O DOCUMENTAL concreta relacionada DIRECTAMENTE con el contenido exacto que se está debatiendo en esa escena (ej: "dog smelling grass close up 4k high resolution", "artificial intelligence data center gpu servers 4k", "electric car lithium battery manufacturing plant").
- PROHIBIDO buscar capturas de pantalla de interfaces de software, Notion, dashboards SaaS o páginas web genéricas a menos que se trate específicamente de un software puntual. Si se habla de ciencia, innovación o naturaleza, busca el laboratorio, el animal, el espacio o la fábrica en acción fotográfica documental.
- EXCLUSIÓN TOTAL DE MARCAS DE AGUA Y SELLOS: La búsqueda visual debe apuntar a material fotográfico libre y editorial en alta resolución (usar sufijos como "editorial photograph hd", "documentary realistic 4k", "nature close up"). NUNCA busques marcas de stock comercial con marca de agua (Shutterstock, Alamy, iStock).
- NUNCA pongas términos genéricos como "technology abstract", "futuristic concept", "cool wallpaper". Sé hiper-específico al hecho, ser vivo, dispositivo o contexto del que se habla.
==============================================================================

TIPOS DE ESCENA DISPONIBLES:
1. "avatar_cam": KAI en plano principal hablando directamente al espectador. Ideal para el gancho inicial (Hook directo) y la conclusión final reflexiva.
2. "video_reaction": B-Roll fotográfico o de video en pantalla completa mientras KAI aparece en recuadro PIP en la esquina reaccionando en vivo ("¡Fíjense en este detalle exacto...!"). En video_reaction, KAI debe reaccionar a un HECHO O VIDEO REAL DEL TEMA, no a interfaces de software.
3. "card_focus": Tarjeta Bento HUD de alto impacto visual en pantalla mostrando la estadística, comparativa o dato clave junto a KAI explicando los números. ¡OBLIGATORIA para cualquier estadística o comparación!
4. "chat_debate": KAI interactúa con preguntas y dilemas de la audiencia, contrastando posturas.
5. "breaking_news": Titular o primicia urgente con tono dinámico y datos inmediatos.

EMOCIONES DE KAI POR ESCENA:
- "excited": Entusiasta, dinámico, revelaciones fascinantes.
- "surprised": Asombrado, incrédulo, al ver videos o noticias impactantes.
- "serious": Riguroso, analítico, al presentar cifras o advertencias.
- "skeptical": Crítico, cuestionador ("¿Quién se beneficia realmente?").
- "confident": Seguro, empático, cierre y despedida.

TEMA: "{topic}"
ESTILO: {style_instructions}
EVIDENCIA DE LA WEB:
{evidence}

RESPONDE EXCLUSIVAMENTE EN FORMATO JSON VÁLIDO:
{{
  "title": "Titular principal de la transmisión",
  "scenes": [
    {{
      "name": "Gancho Inicial & Enigma",
      "type": "avatar_cam",
      "emotion": "excited",
      "camera": "hero_center",
      "speech": "[MÍNIMO {words_per_scene} PALABRAS] ¿Alguna vez te has preguntado cómo percibe el mundo un animal frente a nosotros? Los números son demoledores... [CONTINUAR DESARROLLANDO EXTENSAMENTE el gancho con contexto, datos y tensión argumental sin saludos cliché]",
      "visual_query": "high quality cinematic documentary 4k",
      "sfx": "whoosh",
      "duration_est_sec": {seconds_per_scene}
    }},
    {{
      "name": "Comparativa & Estadísticas en Pantalla",
      "type": "card_focus",
      "emotion": "serious",
      "camera": "pip_corner",
      "card": {{
        "headline": "Comparativa de Sentidos",
        "stat": "300M vs 6M",
        "body": "Receptores olfativos del perro comparados con los del ser humano según estudios biológicos.",
        "badge": "COMPARATIVA"
      }},
      "speech": "[MÍNIMO {words_per_scene} PALABRAS] Miren los datos duros que tenemos en pantalla: trescientos millones frente a apenas seis millones... [DESARROLLAR EN EXTENSO analizando la cifra y su impacto]",
      "visual_query": "dog biology scientific research laboratory 4k",
      "sfx": "chime",
      "duration_est_sec": {seconds_per_scene}
    }}
  ],
  "chat_comments": [
    {{"user": "CuriosoTech", "badge": "VIP", "text": "¡Esa diferencia de cifras es brutal!"}},
    {{"user": "BioData", "badge": "SUB", "text": "Dato mata relato, totalmente comprobado."}},
    {{"user": "Clara_M", "badge": "MOD", "text": "Impresionante la comparativa en pantalla."}}
  ]
}}
"""


class AIDirector:
    """Director autónomo de producción audiovisual para emisiones de KAI."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    async def direct_broadcast(
        self,
        topic: str,
        style: str,
        evidence: str,
        duration_target: int,
        style_instructions: str,
    ) -> DirectorBroadcastPlan:
        """Pide a Gemini dirigir la emisión completa escena por escena."""
        safe_log(f"[AIDirector] Planificando y dirigiendo transmisión para: «{topic}» ({duration_target}s)")

        # Dinamismo profesional de YouTube/TikTok: cambio de escena visual cada 16 a 24 segundos
        dur = max(30, duration_target)
        if dur <= 60:
            num_scenes = max(3, dur // 18)
        elif dur <= 180:
            num_scenes = max(6, dur // 22)
        elif dur <= 360:
            num_scenes = max(10, dur // 25)
        else:
            num_scenes = min(20, max(12, dur // 28))

        seconds_per_scene = round(dur / num_scenes)
        # ~140 palabras por minuto = ~2.33 palabras por segundo
        words_per_scene = max(25, round(seconds_per_scene * 2.33))
        total_words = words_per_scene * num_scenes

        if dur >= 600:
            duration_label = f"{dur // 60} minutos (Análisis Extendido)"
        elif dur >= 120:
            duration_label = f"{dur // 60} minutos"
        else:
            duration_label = f"{dur} segundos"

        prompt = DIRECTOR_SYSTEM_PROMPT.format(
            topic=topic,
            style_instructions=style_instructions,
            duration_target=dur,
            duration_label=duration_label,
            evidence=evidence or "Información reciente y verificada.",
            num_scenes=num_scenes,
            seconds_per_scene=seconds_per_scene,
            words_per_scene=words_per_scene,
            total_words=total_words,
        )

        try:
            gen_timeout = max(45.0, min(180.0, float(dur * 0.15)))
            raw = await asyncio.wait_for(
                asyncio.to_thread(self.llm.generate, prompt, json_mode=True, max_models=2),
                timeout=gen_timeout,
            )
            cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)

            scenes: List[DirectorScene] = []
            raw_scenes = data.get("scenes", [])
            for idx, s in enumerate(raw_scenes):
                c_data = s.get("card")
                card_obj = (
                    SceneCard(
                        headline=c_data.get("headline", "Dato Oficial"),
                        body=c_data.get("body", "Información técnica verificada."),
                        badge=c_data.get("badge", "DATO CLAVE"),
                        stat=c_data.get("stat", ""),
                    )
                    if c_data
                    else None
                )
                scenes.append(
                    DirectorScene(
                        scene_id=idx + 1,
                        name=s.get("name", f"Escena {idx + 1}"),
                        type=s.get("type", "avatar_cam"),
                        emotion=s.get("emotion", "excited"),
                        camera=s.get("camera", "hero_center" if idx in (0, len(raw_scenes) - 1) else "pip_corner"),
                        speech=s.get("speech", "").strip(),
                        visual_query=s.get("visual_query", topic),
                        card=card_obj,
                        sfx=s.get("sfx", "whoosh"),
                        duration_est=float(s.get("duration_est_sec", seconds_per_scene)),
                    )
                )

            if not scenes:
                raise ValueError("El director no devolvió escenas.")

            return DirectorBroadcastPlan(
                title=data.get("title", f"Transmisión KAI: {topic}"),
                topic=topic,
                style=style,
                scenes=scenes,
                chat_comments=data.get("chat_comments", []),
                total_est_duration=float(duration_target),
            )

        except Exception as exc:
            safe_log(f"[AIDirector] Fallback a dirección base por error en Gemini: {exc}")
            return self._build_fallback_plan(topic, style, duration_target)

    def _build_fallback_plan(self, topic: str, style: str, duration_target: int) -> DirectorBroadcastPlan:
        """Plan de dirección de respaldo con speeches proporcionales a la duración objetivo."""
        dur = max(30, duration_target)
        num_scenes = 5
        sec_per_scene = round(dur / num_scenes)
        words_per_scene = max(30, round(sec_per_scene * 2.33))

        # Generar párrafos extensos proporcionales al objetivo
        def _expand(base: str, target_words: int) -> str:
            """Repite y expande el texto base hasta alcanzar el mínimo de palabras."""
            result = base
            filler_phrases = [
                f"Es fundamental que comprendamos la magnitud de lo que estamos viendo con {topic}. ",
                "Los datos más recientes confirman una tendencia que no podemos ignorar. ",
                "Múltiples fuentes internacionales y centros de investigación avalan estos hallazgos. ",
                "Esto significa un cambio de paradigma que impacta a millones de personas en todo el mundo. ",
                "Las implicaciones económicas, sociales y tecnológicas son enormes y debemos analizarlas con rigor. ",
                "Hay quienes cuestionan estos avances, y es válido preguntarse cuáles son los riesgos reales. ",
                "Pero también hay evidencia contundente de beneficios tangibles y medibles que no podemos negar. ",
                "La clave está en encontrar el equilibrio entre innovación responsable y precaución fundamentada. ",
                "Y como siempre les digo: dato mata relato, así que veamos qué nos dicen los números oficiales. ",
                "Comparemos con lo que ocurría hace apenas un año y notaremos la aceleración exponencial. ",
            ]
            idx = 0
            while len(result.split()) < target_words:
                result += filler_phrases[idx % len(filler_phrases)]
                idx += 1
            return result

        scenes = [
            DirectorScene(
                scene_id=1,
                name="Gancho & Apertura Directa",
                type="avatar_cam",
                emotion="excited",
                camera="hero_center",
                speech=_expand(
                    f"¿Qué está ocurriendo realmente con {topic} y por qué las cifras más recientes están desconcertando a los expertos? "
                    "Presten mucha atención, porque los datos duros que analizaremos hoy rompen por completo los mitos más extendidos. ",
                    words_per_scene
                ),
                visual_query="documentary cinematic evidence 4k",
                sfx="whoosh",
                duration_est=float(sec_per_scene),
            ),
            DirectorScene(
                scene_id=2,
                name="Hechos & B-Roll",
                type="video_reaction",
                emotion="surprised",
                camera="pip_corner",
                speech=_expand(
                    "Miren con atención lo que demuestran los registros más recientes en este ámbito: "
                    "la brecha entre lo que se especula habitualmente y la realidad comprobada es sencillamente descomunal. ",
                    words_per_scene
                ),
                visual_query="scientific investigation high resolution 4k",
                sfx="impact",
                duration_est=float(sec_per_scene),
            ),
            DirectorScene(
                scene_id=3,
                name="Datos Verificados",
                type="card_focus",
                emotion="serious",
                camera="pip_corner",
                speech=_expand(
                    "Y fíjense en los números oficiales que desmienten cualquier especulación apresurada. "
                    "Las cifras hablan por sí solas y confirman una transformación estructural sin precedentes. ",
                    words_per_scene
                ),
                visual_query="data analytics matrix",
                card=SceneCard(
                    headline="Evidencia Verificada",
                    body="Cifras y análisis técnico respaldados por fuentes internacionales.",
                    badge="DATO CLAVE",
                    stat="2026",
                ),
                sfx="chime",
                duration_est=float(sec_per_scene),
            ),
            DirectorScene(
                scene_id=4,
                name="Debate y Dilemas",
                type="chat_debate",
                emotion="skeptical",
                camera="pip_corner",
                speech=_expand(
                    "Pero también debemos plantearnos las precauciones necesarias: ¿hasta qué punto debemos acelerar sin control? "
                    "¿Quién se beneficia realmente y quién asume los riesgos que esto conlleva? ",
                    words_per_scene
                ),
                visual_query="cyberpunk ethics digital dilemma",
                sfx="whoosh",
                duration_est=float(sec_per_scene),
            ),
            DirectorScene(
                scene_id=5,
                name="Cierre de la Emisión",
                type="avatar_cam",
                emotion="confident",
                camera="hero_center",
                speech=_expand(
                    "Dejen su postura en el chat. Los leo a todos porque este es un tema que nos involucra a cada uno de nosotros. "
                    "Nos vemos en la próxima emisión en vivo con más datos, más análisis y más verdad sin filtros. ",
                    words_per_scene
                ),
                visual_query="studio stream lighting",
                sfx="chime",
                duration_est=float(sec_per_scene),
            ),
        ]
        return DirectorBroadcastPlan(
            title=f"KAI Broadcast: {topic[:35]}",
            topic=topic,
            style=style,
            scenes=scenes,
            chat_comments=[
                {"user": "AstroTech", "badge": "VIP", "text": "¡Impresionante dato KAI!"},
                {"user": "CodeMaster", "badge": "SUB", "text": "Totalmente de acuerdo."},
            ],
            total_est_duration=float(duration_target),
        )


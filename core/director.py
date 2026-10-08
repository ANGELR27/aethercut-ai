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
    visual_queries: List[str] = field(default_factory=list)  # Soporte para múltiples videos/ángulos por escena
    visual_query2: str = ""                                  # Segundo video de apoyo (reacción / comparativa)
    card: Optional[SceneCard] = None
    chips: List[str] = field(default_factory=list)
    sfx: str = "whoosh"  # whoosh, chime, impact, alert, none
    duration_est: float = 10.0
    # Beats visuales: varios clips de referencia por escena, cada uno ligado a la frase exacta del speech
    # [{"trigger": "frase del speech", "query": "english search", "recent": true}]
    visual_beats: List[Dict[str, Any]] = field(default_factory=list)
    # Pop-ups informativos sincronizados con la locución
    # [{"trigger": "frase del speech", "text": "texto corto", "kind": "stat|fact|alert|quote"}]
    popups: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DirectorBroadcastPlan:
    title: str
    topic: str
    style: str
    scenes: List[DirectorScene] = field(default_factory=list)
    chat_comments: List[Dict[str, str]] = field(default_factory=list)
    total_est_duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DirectorBroadcastPlan":
        scenes_data = data.get("scenes", [])
        scenes: List[DirectorScene] = []
        for s in scenes_data:
            c = s.get("card")
            card_obj = SceneCard(**c) if c else None
            # Reconstruir lista de visual_queries si solo viene visual_query
            vqs = s.get("visual_queries") or []
            vq = s.get("visual_query") or ""
            vq2 = s.get("visual_query2") or ""
            if not vqs:
                if vq:
                    vqs.append(vq)
                if vq2:
                    vqs.append(vq2)
            scenes.append(
                DirectorScene(
                    scene_id=s.get("scene_id", 1),
                    name=s.get("name", "Escena"),
                    type=s.get("type", "avatar_cam"),
                    emotion=s.get("emotion", "excited"),
                    camera=s.get("camera", "pip_corner"),
                    speech=s.get("speech", ""),
                    visual_query=vq,
                    visual_queries=vqs,
                    visual_query2=vq2,
                    card=card_obj,
                    chips=s.get("chips", []),
                    sfx=s.get("sfx", "whoosh"),
                    duration_est=float(s.get("duration_est", s.get("duration_est_sec", 10.0))),
                    visual_beats=_clean_beats(s.get("visual_beats")),
                    popups=_clean_popups(s.get("popups")),
                )
            )
        return cls(
            title=data.get("title", ""),
            topic=data.get("topic", ""),
            style=data.get("style", ""),
            scenes=scenes,
            chat_comments=data.get("chat_comments", []),
            total_est_duration=float(data.get("total_est_duration", 0.0)),
        )


def _clean_beats(raw: Any) -> List[Dict[str, Any]]:
    """Normaliza la lista de beats visuales devuelta por el LLM (tolerante a formatos sucios)."""
    out: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for b in raw[:5]:
        if not isinstance(b, dict):
            continue
        q = str(b.get("query") or "").strip()
        if not q:
            continue
        out.append({
            "trigger": str(b.get("trigger") or "").strip(),
            "query": q,
            "recent": bool(b.get("recent", True)),
        })
    return out


def _clean_popups(raw: Any) -> List[Dict[str, Any]]:
    """Normaliza la lista de pop-ups informativos."""
    out: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for p in raw[:3]:
        if not isinstance(p, dict):
            continue
        txt = str(p.get("text") or "").strip()
        if not txt:
            continue
        kind = str(p.get("kind") or "fact").strip().lower()
        out.append({
            "trigger": str(p.get("trigger") or "").strip(),
            "text": txt[:60],
            "kind": kind if kind in ("stat", "fact", "alert", "quote") else "fact",
        })
    return out


DIRECTOR_SYSTEM_PROMPT = """Eres el DIRECTOR DE TELEVISIÓN Y STREAMING con Inteligencia Artificial de KAI.
Tu misión no es solo escribir un monólogo, sino DIRIGIR UNA PRODUCCIÓN AUDIOVISUAL COMPLETA.
FECHA ACTUAL: {today}. Toda referencia visual debe priorizar material reciente (año {year} o {prev_year}) salvo que el tema sea histórico.

Debes dividir la emisión en EXACTAMENTE {num_scenes} ESCENAS según la duración solicitada ({duration_target} segundos = {duration_label}).

==============================================================================
REQUISITO CRÍTICO E INNEGOCIABLE DE DURACIÓN:
==============================================================================
- Duración total objetivo: {duration_target} segundos ({duration_label}).
- Número de escenas: {num_scenes}.
- Cada escena debe durar aproximadamente {seconds_per_scene} segundos de narración hablada.
- CADA campo "speech" DEBE contener MÍNIMO {words_per_scene} PALABRAS de texto hablado.
- El total de TODAS las escenas sumadas debe dar aproximadamente {total_words} PALABRAS.
- Ritmo de locución y lectura: locución fluida y natural de televisión a 120 palabras por minuto (~2.0 palabras por segundo). Cada idea debe tener tiempo de expresarse sin correr.
- Si la duración es de 3 minutos o más, es OBLIGATORIO desarrollar cada escena con argumentos completos,
  contexto histórico, datos precisos, ejemplos concretos, comparaciones y reflexiones. NO RESUMAS.
- RITMO AUDIOVISUAL DINÁMICO: Ningún plano ni fondo debe permanecer estático por mucho tiempo. Cada escena debe cambiar de perspectiva: alternar entre el gancho directo del avatar, tomas de B-Roll documental reactivo en pantalla completa, tarjetas Bento con cifras duras y momentos de debate.
- NUNCA escribas frases cortas de 1-2 líneas como speech. Cada speech debe ser un PÁRRAFO COMPLETO Y NUTRIDO.

REGLAS DE FIDELIDAD TEMÁTICA, LISTAS Y RANKINGS (TOP 10, TOP 5, COMPARATIVAS):
- FIDELIDAD TOTAL AL TEMA: Si el tema solicita un TOP (ej: "TOP 10 DE LOS PEORES PRESIDENTES EN LOS ÚLTIMOS 6 AÑOS EN AMÉRICA"), la transmisión DEBE ESTRUCTURARSE OBLIGATORIAMENTE COMO ESE TOP. Cada escena debe abordar y nombrar explícitamente a los individuos, mandatarios o puestos concretos (ej: Puesto 10: Pedro Castillo en Perú, Puesto 9: Alberto Fernández en Argentina, etc.) con sus nombres y apellidos reales, años de mandato, cargos y cifras exactas.
- PROHIBIDO GENERALIZAR O DILUIR TEMAS EN ABSTRACCIONES: Está estrictamente prohibido hablar de "la inestabilidad regional" o "la crisis en general" sin mencionar con nombre y apellido a los personajes centrales del tema solicitado. El espectador entró a ver un TOP con nombres concretos; entregar un discurso genérico sin nombrar a los personajes arruina la producción.

REGLAS DE REDACCIÓN Y GUION NARRATIVO (LOCUCIÓN DE RADIO Y TELEVISIÓN):
- Redacta cada escena como un guion audiovisual para locutor profesional: con cadencia rítmica, pausas de respiración y excelente ortografía en español.
- CADA ORACIÓN debe tener longitud moderada (de 10 a 16 palabras) separada por comas y puntos. ESTRICTAMENTE PROHIBIDO redactar párrafos de 30 o 40 palabras seguidas sin comas intermedias.
- Usa comas antes de conjunciones y conectores naturales (ej: ", porque...", ", mientras...", ", donde...", ", pero...", ", y con ello...").
- Habla de forma directa, cautivadora e inteligente, como un narrador o divulgador de primer nivel dirigiéndose a su público.
- Evita muletillas o saludos vacíos (como "Hola a todos" o "Bienvenidos a mi canal"); entra directo al tema con energía y datos interesantes.

REGLAS PARA DATOS, MAPAS, ESTADÍSTICAS Y TARJETAS BENTO HUD (AL MENOS 60% DE LAS ESCENAS):
- ALTO CONTENIDO VISUAL E INFOGRÁFICO OBLIGATORIO: Un video plano o sin gráficos enriquece muy poco la experiencia. Por lo menos el 60% al 70% de las escenas DEBEN contener elementos visuales complementarios: o bien una tarjeta Bento HUD ("card"), o referencias visuales con banderas ("chips"), o un mapa geopolítico.
- SIEMPRE que se mencione una cifra, porcentaje, estadística, comparativa (ej: perro vs humano, PIB, inflación, velocidad, presupuesto, año récord), o hecho verificable, la escena DEBE incluir obligatoriamente el objeto "card".
- SIEMPRE que se discutan países, alianzas diplomáticas, conflictos geopolíticos o acuerdos bilaterales (ej: Estados Unidos, Argentina, Israel, China, Brasil), incluye en "card" un headline o stat con los países involucrados O añade el array "chips" con los nombres oficiales completos. El sistema generará automáticamente un mapa geopolítico vectorial de inteligencia o pastillas HUD con sus banderas nacionales.
- El objeto "card" debe tener:
  * "headline": Título corto y concreto del dato, mapa o comparativa (ej: "Alianza Geopolítica: EE.UU. e Israel", "Capacidad Olfativa: Perro vs Humano", "Inflación Mensual").
  * "stat": La cifra, métrica o relación clave destacada (ej: "300M vs 6M", "52.9%", "+450%", "Alianza Bilateral").
  * "body": Explicación sintética y contundente del dato con fuentes contrastadas.
  * "badge": "ESTADÍSTICA", "DATO CLAVE", "COMPARATIVA", "MAPA GLOBAL" o "CONFIRMADO".
- De esta manera el espectador ve el avatar hablando pero al mismo tiempo tiene en pantalla la tarjeta gráfica interactiva mostrando los mapas, números reales y comparativas en pantalla sin sentirse vacío.

REGLAS PARA EDICIÓN AVANZADA Y REFERENCIAS VISUALES ("chips"):
- SIEMPRE que en la narración se enumeren, comparen o mencionen países (ej: Estados Unidos, China, Argentina, España), marcas o entidades, agrega en la escena el array "chips" con los nombres limpios oficiales (ej: ["Estados Unidos", "China", "Argentina"]).
- NO agregues emojis rotos ni códigos de dos letras como texto crudo; escribe el nombre completo del país o institución ("Estados Unidos", "China", "Argentina", "NASA", "MIT"). El motor gráfico descargará e integrará automáticamente la bandera oficial de alta resolución y aplicará la animación secuencial en el momento en que se mencionen.

REGLAS DE SELECCIÓN VISUAL (MÁXIMA RELEVANCIA Y MULTI-VIDEO POR ESCENA):
- EXACTA COINCIDENCIA TEMÁTICA: Lo que se muestre en pantalla DEBE coincidir al 100% con lo que KAI está narrando en ese instante exacto. Si el guión habla de velocirraptores con plumas, el video DEBE ser de velocirraptores con plumas; si habla de la mordida del T-Rex, el video DEBE mostrar el tiranosaurio rex o biomecánica fósil; si habla de escamas de cocodrilo, debe mostrar piel fósil o reptiles reales.
- CAPACIDAD DE 2 VIDEOS POR ESCENA: Para enriquecer el montaje y evitar fondos repetidos, cada escena puede y debe aportar:
  * "visual_query": El clip de video protagonista para la primera mitad de la escena (en inglés, hiper-específico, 4k/hd, ej: 'velociraptor feathered paleoart documentary animation 4k video').
  * "visual_query2": Un segundo clip de video o ángulo complementario para alternar a mitad de la escena (ej: 'fossil amber feather paleontology laboratory close up video').
- PREDOMINIO ABSOLUTO DE VIDEO: Más del 70% de las escenas deben usar clips de video dinámicos en movimiento.
- BEATS VISUALES ("visual_beats") OBLIGATORIOS: cada escena debe traer de 2 a 4 beats. Cada beat es un clip de referencia EXACTA de lo que se dice en esa frase:
  * "trigger": copia LITERAL de 3 a 6 palabras consecutivas del "speech" donde debe entrar ese clip (en el orden en que aparecen en el speech).
  * "query": búsqueda en inglés hiper-específica de lo que se nombra en esa frase (persona real, lugar, institución, evento, objeto). Ej: si dice "el Banco Central recortó la tasa", query = "argentina central bank building buenos aires news footage".
  * "recent": true si es actualidad (se buscará material del año en curso primero), false solo si es contexto histórico.
  * Prohibido usar queries genéricos ("cinematic", "abstract", "documentary 4k" solos). Nombra la entidad concreta.
- POP-UPS ("popups"): de 0 a 2 por escena. Texto corto (máx. 40 caracteres) que aparece en el instante exacto en que se pronuncia el "trigger" (copia LITERAL de 2 a 5 palabras del speech). "kind": "stat" (cifra), "fact" (dato), "alert" (advertencia/polémica) o "quote" (cita). No repitas lo que ya está en la "card".
- PROHIBIDO repetir el mismo visual_query entre escenas. Cada toma debe ser fresca y diferente.
- EXCLUSIÓN TOTAL DE MARCAS DE AGUA Y SELLOS: NUNCA busques marcas de stock comercial con sellos (Shutterstock, Alamy, iStock, Adobe Stock).
==============================================================================

TIPOS DE ESCENA DISPONIBLES:
1. "avatar_cam": KAI en plano principal hablando directamente al espectador. Ideal para el gancho inicial (Hook directo) y la conclusión final reflexiva.
2. "video_reaction": Clip de video dinámico a pantalla completa con KAI en recuadro PIP en la esquina reaccionando en vivo ("¡Miren esta toma!", "¡Fíjense en este detalle!").
3. "card_focus": Tarjeta Bento HUD con gráfico infográfico (Matplotlib) y KAI en PIP. ¡OBLIGATORIA para estadísticas y comparativas!
4. "chat_debate": KAI interactúa con preguntas y dilemas de la audiencia, contrastando posturas.
5. "breaking_news": Titular o primicia urgente con tono dinámico y clip de video en movimiento.

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
      "speech": "¿Alguna vez te has preguntado cómo percibe el mundo un animal frente a nosotros? Los números son demoledores, y la evidencia científica más reciente cambia por completo nuestra perspectiva habitual.",
      "visual_query": "high quality cinematic documentary 4k video",
      "visual_query2": "nature wildlife cinematic motion footage hd",
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
      "speech": "Miren los datos duros que tenemos en pantalla, con trescientos millones frente a apenas seis millones de receptores. La diferencia es monumental, y explica por qué su capacidad de rastreo supera todo lo imaginable.",
      "chips": ["Canis lupus", "Homo sapiens"],
      "visual_query": "dog biology scientific research laboratory 4k video",
      "visual_query2": "microscopic sensory receptors biology animation video",
      "visual_beats": [
        {{"trigger": "Miren los datos duros", "query": "police sniffer dog working airport footage", "recent": true}},
        {{"trigger": "trescientos millones frente a", "query": "dog nose close up macro sniffing", "recent": false}},
        {{"trigger": "su capacidad de rastreo", "query": "search and rescue dog tracking scent field", "recent": true}}
      ],
      "popups": [
        {{"trigger": "La diferencia es monumental", "text": "50 veces más receptores", "kind": "stat"}}
      ],
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
        # Ritmo de narración natural y elocuente (~120 palabras por minuto = ~2.0 palabras por segundo)
        words_per_scene = max(22, round(seconds_per_scene * 2.0))
        total_words = words_per_scene * num_scenes

        if dur >= 600:
            duration_label = f"{dur // 60} minutos (Análisis Extendido)"
        elif dur >= 120:
            duration_label = f"{dur // 60} minutos"
        else:
            duration_label = f"{dur} segundos"

        import datetime as _dt
        _now = _dt.date.today()
        prompt = DIRECTOR_SYSTEM_PROMPT.format(
            today=_now.isoformat(),
            year=_now.year,
            prev_year=_now.year - 1,
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
                raw_speech = s.get("speech", "").strip()
                from utils.speech_normalizer import normalize_speech_for_tts
                polished_speech = normalize_speech_for_tts(raw_speech)

                scenes.append(
                    DirectorScene(
                        scene_id=idx + 1,
                        name=s.get("name", f"Escena {idx + 1}"),
                        type=s.get("type", "avatar_cam"),
                        emotion=s.get("emotion", "excited"),
                        camera=s.get("camera", "hero_center" if idx in (0, len(raw_scenes) - 1) else "pip_corner"),
                        speech=polished_speech or raw_speech,
                        visual_query=s.get("visual_query", topic),
                        visual_queries=[q for q in [s.get("visual_query"), s.get("visual_query2")] if q],
                        visual_query2=s.get("visual_query2", ""),
                        card=card_obj,
                        chips=s.get("chips", []),
                        sfx=s.get("sfx", "whoosh"),
                        duration_est=float(s.get("duration_est_sec", seconds_per_scene)),
                        visual_beats=_clean_beats(s.get("visual_beats")),
                        popups=_clean_popups(s.get("popups")),
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
        words_per_scene = max(24, round(sec_per_scene * 2.0))

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


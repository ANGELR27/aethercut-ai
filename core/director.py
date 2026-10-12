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
    body: str = ""
    badge: str = "DATO CLAVE"
    stat: str = ""
    style: str = "auto"       # auto, verdict_badge, tech_card, quote, bento, map
    icon: str = "✓"
    subtitle: str = ""
    template: str = "auto"   # verdict_badge, tech_card, stat_counter, versus_split, quote_evidence, step_badge, alert_banner, source_chip
    variant: str = "orange_noir"  # orange_noir, frosted_white, emerald_matrix, crimson_hazard, cyber_cyan, royal_gold
    params: Dict[str, Any] = field(default_factory=dict)


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
    # Texto libre cinemático flotante (sin card, con desenfoque de fondo opcional)
    free_title: Optional[Dict[str, Any]] = None
    # Modo análisis de caso: índice del fotograma REAL del video fuente que
    # respalda esta escena (cuando la transmisión analiza un video/caso concreto).
    case_frame: Optional[int] = None


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
            card_obj = None
            if c and isinstance(c, dict):
                valid_card_keys = {k: v for k, v in c.items() if k in SceneCard.__dataclass_fields__}
                card_obj = SceneCard(**valid_card_keys)
            elif isinstance(c, SceneCard):
                card_obj = c
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
                    # 'or "whoosh"': un "sfx": null (la clave existe) devolvía None.
                    sfx=(s.get("sfx") or "whoosh") if s.get("sfx") != "none" else "none",
                    duration_est=float(s.get("duration_est", s.get("duration_est_sec", 10.0))),
                    visual_beats=_clean_beats(s.get("visual_beats")),
                    popups=_clean_popups(s.get("popups")),
                    free_title=s.get("free_title"),
                    case_frame=s.get("case_frame") if isinstance(s.get("case_frame"), int) else None,
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


def _parse_director_json(raw: str) -> Dict[str, Any]:
    """Parseador altamente tolerante a fallos para el plan audiovisual del LLM."""
    if not raw or not raw.strip():
        raise ValueError("Respuesta vacía del LLM")

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()

    # 1. Intento directo
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 2. Extraer subcadena delimitada por la primera { y la última }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

        # 3. Eliminar comas finales que invalidan JSON: ,} o ,]
        fixed = re.sub(r",\s*([\}\]])", r"\1", candidate)
        try:
            return json.loads(fixed)
        except Exception:
            pass

        # 4. Corregir saltos de línea sin escapar dentro de strings
        fixed_nl = re.sub(r'(?<=: ")(.*?)(?=",\s*\n|"\s*\n|",)', lambda m: m.group(0).replace('\n', '\\n').replace('\r', ''), fixed, flags=re.DOTALL)
        try:
            return json.loads(fixed_nl)
        except Exception:
            pass

    # 5. Respuesta truncada por límite de tokens (auto-cerrar llaves/corchetes)
    if start != -1:
        partial = cleaned[start:].rstrip()
        for close_seq in ["]}", "]}}", "}]}", "}\n}"]:
            try:
                p_trim = re.sub(r",\s*$", "", partial)
                return json.loads(p_trim + close_seq)
            except Exception:
                pass

    return json.loads(cleaned)


DIRECTOR_SYSTEM_PROMPT = """Eres el GUIONISTA PROFESIONAL Y DIRECTOR DE PRODUCCIÓN AUDIOVISUAL DE ÉLITE de KAI.
Especializado en videos de YouTube, divulgación científica, historia, tecnología, misterios, documentales y contenido educativo.
FECHA ACTUAL: {today}. Toda referencia visual debe priorizar material reciente (año {year} o {prev_year}) salvo que el tema sea histórico.

Tu misión es transformar cualquier tema en un guion y una producción audiovisual que consiga cuatro cosas indispensables:
1. Captar la atención desde los primeros segundos.
2. Mantener el interés durante todo el video mediante recursos narrativos y psicológicos.
3. Explicar conceptos complejos de manera sencilla, precisa y causalmente comprensible.
4. Dejar al espectador con la sensación de haber aprendido algo valioso.

No escribas únicamente para transmitir información. Diseña una experiencia de aprendizaje que despierte curiosidad, facilite la comprensión y recompense la atención del espectador.
PRINCIPIO FINAL: "Curiosidad para comenzar, claridad para comprender, progresión para continuar y una recompensa intelectual para terminar."

Debes estructurar la emisión en EXACTAMENTE {num_scenes} ESCENAS según la duración solicitada ({duration_target} segundos = {duration_label}).

==============================================================================
MOTOR PSICOLÓGICO ADAPTATIVO (APLICA SEGÚN EL TEMA):
==============================================================================
A. CURIOSIDAD Y BRECHA DE INFORMACIÓN: Abre con una pregunta cuya respuesta no sea inmediatamente evidente. Revela información progresivamente. Plantea contradicciones entre lo que el público cree y lo que muestran las evidencias. Evita resolver demasiado pronto la pregunta principal.
B. APERTURA Y CIERRE DE BUCLES NARRATIVOS: Introduce preguntas secundarias que se resolverán más adelante. Conecta los descubrimientos con nuevas preguntas relevantes. Cierra cada bucle en el momento adecuado. No acumules preguntas sin responder ni prometas revelaciones que el video no cumple.
C. SORPRESA Y CAMBIO DE PERSPECTIVA: Introduce descubrimientos, contrastes, excepciones o consecuencias inesperadas. Muestra cambios de perspectiva sin inventar ni exagerar hechos reales.
D. RELEVANCIA PERSONAL: Conecta el tema con la vida cotidiana, las decisiones, conocimientos previos o preguntas del espectador.
E. CONFLICTO Y RESOLUCIÓN: Identifica qué misterio, desafío, debate o contradicción impulsa el video. Progresión causal obligatoria: pregunta → investigación → evidencias → dificultad o contradicción → explicación → conclusión.
F. RECOMPENSAS COGNITIVAS CONTINUAS: Cada escena debe aportar valor concreto: una respuesta, un descubrimiento, una conexión inesperada o una herramienta para entender el mundo. El espectador debe recibir valor durante todo el video, no solo al final.
G. EJEMPLOS, ANALOGÍAS Y VISUALIZACIÓN MENTAL: Explica ideas abstractas mediante ejemplos concretos, comparaciones comprensibles y situaciones familiares.
H. RITMO Y VARIACIÓN DE CADENCIA: Alterna preguntas y respuestas, explicaciones y ejemplos, datos y consecuencias, momentos de tensión intelectual y momentos de comprensión.

==============================================================================
ACTIVACIÓN DEL MÓDULO NARRATIVO SEGÚN EL FORMATO (¡NO TODO ES UN DOCUMENTAL!):
==============================================================================
Cada formato tiene sus propias reglas. No fuerces una estructura documental en todos los videos:
- MÓDULO A (Reacciones y análisis): Presenta el material y contexto indispensables; distingue emociones, opiniones y hechos; aporta análisis propio sustancial en vez de narrar lo que ya se ve; espontaneidad y valor añadido.
- MÓDULO B (TOPs, listas y rankings): Criterio de inclusión claro; una escena individual por puesto; progresión sin guardarlo todo para el final; justificación y cifras concretas de cada lugar.
- MÓDULO C (Documentales, ciencia y misterios): Pregunta central, hipótesis, evidencias, explicaciones causales profundas y resolución basada en hechos contrastados.
- MÓDULO D (Humor, memes y entretenimiento): Premisa cómica, preparación y remate, ritmo ágil sin sobre-explicar bromas ni repetir el mismo chiste.
- MÓDULO E (Reviews y comparativas): Problema a resolver, criterios de evaluación, ventajas y desventajas reales, pruebas verificables y recomendación condicionada al usuario.
- MÓDULO F (Gaming y desafíos): Objetivo claro, reglas del desafío, obstáculos inesperados, decisiones bajo presión y desenlace basado en resultados reales.
- MÓDULO G (Historias, biografías y casos): Contexto y protagonistas, decisiones documentadas, causalidad histórica sin inventar diálogos o hechos ficticios.
- MÓDULO H (Tutoriales y educación): Resultado prometido, requisitos previos, pasos secuenciales comprobables, errores comunes a evitar y demostración de éxito verificable.
- MÓDULO I (Noticias, actualidad y tendencias): Información prioritaria inmediata, separar hechos de especulación, contexto y consecuencias inmediatas.
- MÓDULO J (Pódcasts, debates y entrevistas): Conversación orgánica, dilemas abiertos, matices y contraste de perspectivas contrarias.
- MÓDULO K (Shorts verticales breves): Gancho visual instantáneo en el segundo 1, una sola idea contundente desarrollada al grano y remate satisfactorio sin relleno.
- MÓDULO L (Híbridos): Combina con coherencia dos formatos (ej. Reacción + Análisis, TOP + Misterio, Tutorial + Comparativa).

==============================================================================
CLARIDAD COMO REGLA OBLIGATORIA (LA RETENCIÓN NO SUBORDINA LA COMPRENSIÓN):
==============================================================================
- Una idea principal por bloque/escena.
- Define términos técnicos antes de utilizarlos repetidamente.
- Explica las CAUSAS, no solo los resultados finales ("ocurrió X porque Y generó Z").
- Distingue hechos comprobados, hipótesis, interpretaciones y opiniones.
- Transiciones que expliquen por qué una idea conduce a la siguiente.
- Elimina frases vacías que suenen interesantes pero no aporten información real.

==============================================================================
ARQUITECTURA NARRATIVA ADAPTADA EN {num_scenes} ESCENAS:
==============================================================================
1. GANCHO INICIAL ADECUADO AL FORMATO (Escena 1): Conecta de inmediato con la promesa del formato sin saludos largos ni rodeos.
2. PROMESA NARRATIVA: Claridad de qué comprenderá o experimentará el espectador.
3. CONTEXTO MÍNIMO NECESARIO: Lo indispensable para comprender sin sobrecargar.
4. DESARROLLO PROGRESIVO: Bloques que construyen avance real hacia el objetivo.
5. PUNTOS DE RENOVACIÓN DE ATENCIÓN (al 60-70% del video): Introduce una nueva pregunta, giro, evidencia o dilema clave.
6. REVELACIÓN O CLÍMAX CENTRAL: Resolución de la premisa principal con el grado de certeza o emoción que el formato requiere.
7. CONSECUENCIAS Y CONEXIONES: Qué significa el resultado y cómo cambia nuestra comprensión.
8. CIERRE SATISFACTORIO: Conclusión memorable y recompensa intelectual o de entretenimiento lograda.

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
- FIDELIDAD TOTAL AL TEMA: Si el tema solicita un TOP N (ej: "TOP 10 DE LOS PEORES PRESIDENTES EN LOS ÚLTIMOS 6 AÑOS EN AMÉRICA"):
  * La transmisión DEBE tener EXACTAMENTE UNA ESCENA DEDICADA A CADA UNO DE LOS PUESTOS (desde el Puesto 10 descendiendo uno a uno hasta el Puesto 1).
  * ESTRICTAMENTE PROHIBIDO saltarse puestos o agrupar varios mandatarios/puestos en una sola escena. Si el usuario pidió un TOP 10, el video debe tener 10 escenas individuales para los 10 personajes distintos, precedidas por la intro y seguidas por la conclusión.
  * Cada puesto debe nombrar con nombre y apellido completo al mandatario (ej: Puesto 10: Bernardo Arévalo, Puesto 9: Dina Boluarte, Puesto 8: Pedro Castillo, Puesto 7: Alberto Fernández, etc.), su país, sus fechas de mandato y los hechos o porcentajes concretos de su gestión.
- PROHIBIDO GENERALIZAR O DILUIR TEMAS EN ABSTRACCIONES: Está estrictamente prohibido hablar de "la inestabilidad regional" o "la crisis en general" sin mencionar con nombre y apellido a los personajes centrales del tema solicitado. El espectador entró a ver un TOP con nombres concretos; entregar un discurso genérico sin nombrar a los personajes arruina la producción.

REGLAS DE REDACCIÓN Y GUION NARRATIVO (LOCUCIÓN DE RADIO Y TELEVISIÓN):
- Redacta cada escena como un guion audiovisual para locutor profesional: con cadencia rítmica, pausas de respiración y excelente ortografía en español.
- CADA ORACIÓN debe tener longitud moderada (de 10 a 16 palabras) separada por comas y puntos. ESTRICTAMENTE PROHIBIDO redactar párrafos de 30 o 40 palabras seguidas sin comas intermedias.
- Usa comas antes de conjunciones y conectores naturales (ej: ", porque...", ", mientras...", ", donde...", ", pero...", ", y con ello...").
- Habla de forma directa, cautivadora e inteligente, como un narrador o divulgador de primer nivel dirigiéndose a su público.
- Evita muletillas o saludos vacíos (como "Hola a todos" o "Bienvenidos a mi canal"); entra directo al tema con energía y datos interesantes.

REGLAS DE RETENCIÓN Y VARIEDAD VISUAL (EDICIÓN PROFESIONAL):
- VARIEDAD DE ESCENA: NUNCA dos escenas consecutivas del mismo "type" (excepto avatar_cam para abrir y cerrar). Alterna card_focus → video_reaction → vector_motion → chat_debate para que el encuadre respire y el ojo no se aburra del mismo formato.
- PRIMEROS 15 SEGUNDOS DENSOS: el mayor abandono del espectador ocurre aquí. La escena 1 debe entregar el gancho + el dato más impactante del tema, sin contexto previo ni preámbulos.
- BEAT DE RE-ENGANCHE al 60-70% del guion: en esa zona incluye OBLIGATORIAMENTE una escena que reformule la tensión con una pregunta directa al espectador, un dato que invierta lo dicho, o un anticipo del desenlace ("y aquí es donde todo cambia...").
- RITMO DE ORACIONES VARIADO: alterna frases cortas contundentes (6-9 palabras) con frases de desarrollo (14-18 palabras). La variación de cadencia retiene más que el vocabulario.
- CARDS CONCISAS: el "body" de cada card se sostiene en pantalla solo lo que toma leerlo (~un tercio de segundo por palabra). Máximo 130 caracteres: si no cabe el dato esencial en esa cifra, simplifica el texto en vez de alargarlo.
- CITA FUENTES REALES POR NOMBRE: cuando la evidencia web mencione un medio, estudio o institución (Reuters, Ember, Nature, ONU, NASA), cítalo POR SU NOMBRE en la narración al menos 2 veces a lo largo del video ("según el informe de Ember...", "como publicó Reuters...") y en los popups ("Fuente: Ember"). La atribución real construye credibilidad y retiene al espectador escéptico.
- GANCHO VISUAL CONCRETO: el gancho inicial debe señalar algo visible y verificable ("miren estas marcas en la montaña") que la escena siguiente MUESTRE de verdad — nunca prometas visualmente algo que el montaje no entrega.

REGLAS PARA DATOS, MAPAS, ESTADÍSTICAS Y TARJETAS BENTO HUD (AL MENOS 60% DE LAS ESCENAS):
- ALTO CONTENIDO VISUAL E INFOGRÁFICO OBLIGATORIO: Un video plano o sin gráficos enriquece muy poco la experiencia. Por lo menos el 60% al 70% de las escenas DEBEN contener elementos visuales complementarios: o bien una tarjeta Bento HUD ("card"), o referencias visuales con banderas ("chips"), o un mapa geopolítico.
- SIEMPRE que se mencione una cifra, porcentaje, estadística, comparativa (ej: perro vs humano, PIB, inflación, velocidad, presupuesto, año récord), o hecho verificable, la escena DEBE incluir obligatoriamente el objeto "card".
- SIEMPRE que se discutan países, alianzas diplomáticas, conflictos geopolíticos o acuerdos bilaterales (ej: Estados Unidos, Argentina, Israel, China, Brasil), incluye en "card" un headline o stat con los países involucrados O añade el array "chips" con los nombres oficiales completos. El sistema generará automáticamente un mapa geopolítico vectorial de inteligencia o pastillas HUD con sus banderas nacionales.
- El objeto "card" debe tener:
  * "headline": Título corto y concreto del dato, mapa o comparativa (ej: "Alianza Geopolítica: EE.UU. e Israel", "Capacidad Olfativa: Perro vs Humano", "Inflación Mensual").
  * "stat": La cifra, métrica o relación clave destacada (ej: "300M vs 6M", "52.9%", "+450%", "Alianza Bilateral").
  * "body": Explicación sintética y contundente del dato con fuentes contrastadas.
  * "template" (o "style", elige la plantilla exacta de la librería para máximo impacto):
    - "verdict_badge": Distintivo viral estilo sticker/sello inclinado con rebote elástico (ej: headline "ganó Opus", "100% Real", "Confirmado", icon "✓"). Entra con spring bounce y SFX "pop".
    - "tech_card": Tarjeta tecnológica superior dark slate con micro-matriz de puntos (ej: headline "find-skills", body "por Vercel · vercel-labs/skills"). Flota arriba con SFX "whoosh" o "pop".
    - "stat_counter": Cifra récord con número gigante en gradiente, medidor de barra y tendencia (ej: stat "+340%", headline "Récord Histórico"). SFX "chime".
    - "versus_split": Comparativa dual lado A vs lado B con divisor central circular VS en naranja (ej: headline "Humano", body "IA Autónoma", stat "4h vs 12s"). SFX "impact".
    - "quote_evidence": Cita editorial Vox con comillas grandes, fuente y frase resaltada en fluorescente. SFX "whoosh".
    - "step_badge": Píldora de hito/fase con cápsula numérica (ej: headline "Detección Acústica", stat "01"). SFX "pop".
    - "alert_banner": Alerta táctica con ícono de peligro y borde brillante (ej: headline "CONTRADICCIÓN DETECTADA", body "Señal no biológica"). SFX "alert".
    - "source_chip": Micro-pastilla de atribución oficial verificada (ej: headline "NOAA Research 2026"). SFX "pop".
    - "map": Mapa geopolítico táctico satelital.
    - "bento": Tarjeta Bento Obsidian con gráfico e indicador de estado.
  * "variant" (paleta de diseño):
    - "orange_noir": Negro mate Obsidian + Naranja Eléctrico firma + Blanco perla (Firma AetherCut).
    - "frosted_white": Cristal esmerilado translúcido + Borde blanco + Tipografía serif editorial.
    - "emerald_matrix": Negro carbón + Verde Esmeralda neón para hechos verificados y éxito.
    - "crimson_hazard": Negro carbón + Rojo Carmesí para alertas críticas, mitos y controversias.
    - "cyber_cyan": Negro profundo + Cian Neón para tecnología, software y código.
    - "royal_gold": Negro + Oro Solar para récords mundiales y tops #1.
  * "badge":
    - "VEREDICTO", "GANADOR" o "SELLO": Activa verdict_badge.
    - "TECH", "HERRAMIENTA", "DEV" o "SKILL": Activa tech_card.
    - "ESTADÍSTICA", "RÉCORD", "CIFRA": Activa stat_counter.
    - "COMPARATIVA" o "VERSUS": Activa versus_split.
    - "EVIDENCIA DOCUMENTAL" o "INFORME OFICIAL": Activa quote_evidence.
    - "PASO", "FASE" o "HITO": Activa step_badge.
    - "ALERTA" o "PELIGRO": Activa alert_banner.
    - "FUENTE" o "ATRIBUCIÓN": Activa source_chip.
- De esta manera el espectador ve el avatar hablando pero al mismo tiempo tiene en pantalla la tarjeta gráfica interactiva mostrando los mapas, números reales y comparativas en pantalla sin sentirse vacío.

REGLAS PARA TEXTO LIBRE ANIMADO CINEMÁTICO ("free_title") (SIN CAJAS, FLOTANTE EN PANTALLA):
- Si la escena representa un TOP / RANKING (ej: "Puesto 3"), una ENUMERACIÓN DE COSAS IMPORTANTES (ej: "Factor #1: Velocidad", "Paso 2: Neutralización") o un CONCEPTO DE IMPACTO ("Guerra Sin Humanos", "Inversión Récord"), incluye el objeto "free_title" (flotará libre directamente sobre el video sin caja ni contenedor):
  * "title": Titular principal (ej: "DRONES AUTÓNOMOS", "VELOCIDAD DE REACCIÓN", "CONTROL BALÍSTICO").
  * "number": Número destacado de 2 dígitos si aplica (ej: "03", "01") o dejarlo vacío.
  * "tag": Etiqueta superior en micro-letras (ej: "PUESTO 03 · RANKING", "FACTOR DETERMINANTE #1", "ALERTA ESTRATÉGICA").
  * "subtitle": Frase corta explicativa (máximo 12 palabras).
  * "highlight": La palabra exacta del título que debe brillar con halo de luz de color.
  * "blur_bg": true (desenfoca momentáneamente el fondo del video durante 2 segundos mientras aparece el título flotante).

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
- ANCLAJE A LA ENTIDAD REAL DEL CASO: cuando la transmisión trate un caso, lugar, persona, objeto o evento ESPECÍFICO, el "visual_query" y los "query" de los beats DEBEN nombrar esa entidad exacta (ej: 'Dyatlov Pass tent 1959 expedition photograph', 'Nazca lines hummingbird geoglyph aerial', 'Monte Ararat Durupinar formation satellite') y NUNCA su equivalente genérico ('snowy mountain', 'ancient lines', 'rocky mountain'). Una montaña cualquiera cuando se habla de UNA montaña concreta es una mentira visual que rompe la credibilidad.
{case_frames_block}==============================================================================

TIPOS DE ESCENA DISPONIBLES:
1. "avatar_cam": KAI diciendo la primera frase de gancho (Hook de impacto de 3 a 4 segundos MÁXIMO) y luego entra inmediatamente el contenido visual y B-Roll para que la audiencia no se aburra. Ideal para abrir con intriga o para la conclusión final reflexiva.
2. "video_reaction": Clip de video dinámico a pantalla completa con KAI en recuadro PIP en la esquina reaccionando en vivo ("¡Miren esta toma!", "¡Fíjense en este detalle!").
3. "card_focus": Tarjeta Bento HUD con gráfico infográfico (Matplotlib) y KAI en PIP. ¡OBLIGATORIA para estadísticas y comparativas!
4. "vector_motion": B-Roll cinemático conceptual y gráficos de estudio de alta definición (redes neuronales, flujos tecnológicos, metraje 4K o visualizaciones abstractas). ¡Ideal para explicar conceptos y procesos complejos!
5. "chat_debate": KAI interactúa con preguntas y dilemas de la audiencia, contrastando posturas.
6. "breaking_news": Titular o primicia urgente con tono dinámico y clip de video en movimiento.

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
        case_frames: Optional[List[Dict[str, Any]]] = None,
    ) -> DirectorBroadcastPlan:
        """Pide a Gemini dirigir la emisión completa escena por escena.

        case_frames: fotogramas REALES del video/caso fuente (modo análisis de
        caso). Cada item: {"index": int, "desc": str}. El director los usa como
        fondo de las escenas que hablan de lo que SE VE en esos fotogramas.
        """
        safe_log(f"[AIDirector] Planificando y dirigiendo transmisión para: «{topic}» ({duration_target}s)")

        # Detección inteligente de TOPs y Rankings (ej: TOP 10, TOP 5, Ranking 7)
        ranking_match = re.search(r'\b(?:top|ranking|los mejores|los peores|puesto|puestos)\s*(\d{1,2})\b', topic, re.IGNORECASE)
        ranked_n = int(ranking_match.group(1)) if ranking_match else None

        # Dinamismo profesional de YouTube/TikTok: cambio de escena visual cada 16 a 24 segundos
        dur = max(20, duration_target)
        if ranked_n and 3 <= ranked_n <= 15:
            # Para un TOP N: 1 escena de intro/gancho + N escenas (una por cada puesto) + 1 escena de conclusión
            num_scenes = ranked_n + 2
        elif dur <= 35:
            num_scenes = 2
        elif dur <= 60:
            num_scenes = max(3, dur // 18)
        elif dur <= 180:
            num_scenes = max(6, dur // 22)
        elif dur <= 360:
            num_scenes = max(10, dur // 25)
        else:
            num_scenes = min(48, max(12, dur // 28)) if dur > 1200 else min(20, max(12, dur // 28))

        seconds_per_scene = round(dur / num_scenes)
        # Ritmo de narración natural y elocuente (~130 palabras por minuto = ~2.15 palabras por segundo)
        # Ajustamos el objetivo de palabras por escena para que el audio Edge TTS llene exactamente la duración deseada
        words_per_scene = max(26, round(seconds_per_scene * 2.15))
        total_words = words_per_scene * num_scenes

        if dur >= 600:
            duration_label = f"{dur // 60} minutos (Análisis Extendido)"
        elif dur >= 120:
            duration_label = f"{dur // 60} minutos"
        else:
            duration_label = f"{dur} segundos"

        # Bloque de fotogramas del caso (modo análisis): describe al director qué
        # hay disponible y le obliga a anclar las escenas a esos fotogramas reales.
        if case_frames:
            frame_lines = "\n".join(
                f"  * case_frame {f['index']}: {f.get('desc', '')[:200]}"
                for f in case_frames
            )
            case_frames_block = f"""
ANÁLISIS VISUAL DEL VIDEO/CASO FUENTE (FOTOGRAMAS REALES DISPONIBLES):
Estos fotogramas REALES del caso ya están descargados y listos como fondos de pantalla. Índice + descripción:
{frame_lines}
- OBLIGATORIO: las escenas que se refieran a lo que SE VE en estos fotogramas DEBEN incluir "case_frame": <índice del fotograma> en su JSON (es un número entero). Es la evidencia visual del caso: mostrar stock genérico cuando existe el fotograma real sería una mentira visual.
- Ordena la narración para RECORRER los fotogramas en el orden natural del caso ("miren las marcas en la montaña" → el fotograma con las marcas).
- El gancho inicial DEBE abrir con el fotograma más impactante del caso (case_frame en la escena 1 o 2).

"""
        else:
            case_frames_block = ""

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
            case_frames_block=case_frames_block,
        )

        try:
            gen_timeout = max(110.0, min(420.0 if dur > 1200 else 240.0, float(dur * 0.6)))
            raw = await asyncio.wait_for(
                asyncio.to_thread(
                    self.llm.generate,
                    prompt,
                    json_mode=True,
                    max_models=3,
                    deadline_sec=gen_timeout,
                    thinking_budget=1024,
                ),
                timeout=gen_timeout,
            )
            data = None
            try:
                data = _parse_director_json(raw)
            except Exception as parse_err:
                safe_log(f"[AIDirector] Aviso: JSON primario requirió reparación ({parse_err}). Reparando...")
                try:
                    fix_prompt = (
                        "El siguiente texto contiene un JSON de un plan de video con errores menores de sintaxis (comas o comillas). "
                        "Corrige la sintaxis y responde EXCLUSIVAMENTE con el objeto JSON válido:\n\n"
                        f"{raw[:8000]}"
                    )
                    repaired_raw = self.llm.generate(fix_prompt, json_mode=True, deadline_sec=18)
                    data = _parse_director_json(repaired_raw)
                    safe_log("[AIDirector] ✓ JSON reparado y recuperado exitosamente con IA auxiliar.")
                except Exception as fix_err:
                    safe_log(f"[AIDirector] No se pudo reparar JSON con IA auxiliar ({fix_err}).")
                    raise parse_err

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
                        # 'or "whoosh"': un "sfx": null del LLM (la clave existe) no
                        # debe dejar None — crasheaba el render de la escena.
                        sfx=(s.get("sfx") or "whoosh") if s.get("sfx") != "none" else "none",
                        duration_est=float(s.get("duration_est_sec", seconds_per_scene)),
                        visual_beats=_clean_beats(s.get("visual_beats")),
                        popups=_clean_popups(s.get("popups")),
                        # free_title: el prompt exige producirlo y from_dict lo
                        # conservaba, pero esta ruta directa lo descartaba — los
                        # títulos libres del LLM solo aparecían tras la auditoría GLM.
                        free_title=s.get("free_title"),
                        case_frame=s.get("case_frame") if isinstance(s.get("case_frame"), int) else None,
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
        """Plan de dirección de respaldo con progresión narrativa real sin repeticiones y tarjetas informativas ricas."""
        dur = max(30, duration_target)
        num_scenes = 5
        sec_per_scene = round(dur / num_scenes)
        words_per_scene = max(26, round(sec_per_scene * 2.15))

        # Banco de frases temáticas progresivas e independientes por cada escena (CERO repeticiones)
        scene1_phrases = [
            f"Presten mucha atención, porque los datos duros en torno a {topic} rompen por completo los mitos más extendidos. ",
            "Lo que parecía una teoría marginal acaba de recibir confirmación tangible en los últimos registros analizados. ",
            "Acompáñenme a desglosar paso a paso por qué esto cambia todo lo que dábamos por sentado en la materia. ",
            "Vamos a revisar las pruebas reales, lejos de la especulación y con rigor documental absoluto. ",
        ]
        scene2_phrases = [
            "La brecha entre lo que se especula habitualmente y la evidencia comprobada es sencillamente descomunal. ",
            "Los equipos de investigación en el terreno contrastaron los patrones iniciales con modelos predictivos avanzados. ",
            "Cada capa analizada aporta un nivel de precisión que descarta anomalías estadísticas fortuitas o coincidencias. ",
            "Los antecedentes históricos demuestran que este fenómeno no surgió de la noche a la mañana. ",
        ]
        scene3_phrases = [
            "Las cifras hablan por sí solas y confirman una transformación estructural de escala global sin precedentes. ",
            "Al contrastar la serie histórica con los indicadores presentes, la discrepancia matemática resulta indiscutible. ",
            "Dato mata relato: las mediciones estandarizadas confirman un salto cuantitativo que ningún experto esperaba. ",
            "Los registros oficiales avalan que los puntos de quiebre están ocurriendo a un ritmo mucho más acelerado. ",
        ]
        scene4_phrases = [
            "¿Hasta qué punto debemos acelerar sin control, y quién asume los riesgos reales que este cambio conlleva? ",
            "Mientras un sector defiende explicaciones convencionales, la nueva evidencia obliga a replantear el marco teórico. ",
            "No se trata de opiniones ni creencias, sino de comprobar qué modelo resiste el escrutinio del método experimental. ",
            "El dilema ético y operativo está sobre la mesa y los principales referentes mundiales ya están tomando postura. ",
        ]
        scene5_phrases = [
            "Este es un tema crucial que nos involucra a todos, y la discusión apenas está comenzando en los círculos de vanguardia. ",
            "El panorama que se abre a partir de aquí marcará la agenda de los próximos debates y publicaciones especializadas. ",
            "Quiero leer su perspectiva honesta en el chat y en los comentarios: ¿estamos ante el inicio de una nueva era? ",
            "Nos vemos en la próxima emisión en vivo con más análisis, más datos verificados y más verdad sin filtros. ",
        ]

        def _build_speech(intro: str, pool: list, target_w: int) -> str:
            res = intro
            for phrase in pool:
                if len(res.split()) >= target_w:
                    break
                res += phrase
            return res

        scenes = [
            DirectorScene(
                scene_id=1,
                name="Gancho & Apertura Directa",
                type="avatar_cam",
                emotion="excited",
                camera="hero_center",
                speech=_build_speech(
                    f"¿Qué está ocurriendo realmente con {topic} y por qué las cifras más recientes están desconcertando a los expertos? ",
                    scene1_phrases,
                    words_per_scene
                ),
                visual_query=f"{topic} documentary evidence 4k",
                visual_queries=[f"{topic} documentary evidence 4k", f"{topic} investigation 4k"],
                sfx="whoosh",
                duration_est=float(sec_per_scene),
            ),
            DirectorScene(
                scene_id=2,
                name="Hechos & Hallazgos de Campo",
                type="video_reaction",
                emotion="surprised",
                camera="pip_corner",
                speech=_build_speech(
                    "Miren con atención lo que demuestran los registros más recientes en este ámbito: ",
                    scene2_phrases,
                    words_per_scene
                ),
                visual_query=f"{topic} historical scientific records 4k",
                visual_queries=[f"{topic} scientific analysis 4k"],
                card=SceneCard(
                    headline=f"Registro: {topic[:32]}",
                    body="Documentación y evidencia empírica contrastada en campo.",
                    badge="DATO CLAVE",
                    stat="+340%",
                ),
                sfx="impact",
                duration_est=float(sec_per_scene),
            ),
            DirectorScene(
                scene_id=3,
                name="Datos Verificados & Métricas",
                type="card_focus",
                emotion="serious",
                camera="pip_corner",
                speech=_build_speech(
                    "Y fíjense en los números oficiales que desmienten cualquier especulación apresurada. ",
                    scene3_phrases,
                    words_per_scene
                ),
                visual_query=f"{topic} data analysis charts 4k",
                visual_queries=[f"{topic} official metrics 4k"],
                card=SceneCard(
                    headline="Evidencia Verificada 2026",
                    body="Auditoría técnica independiente y registros oficiales consolidados.",
                    badge="EVIDENCIA DOCUMENTAL",
                    stat="2026",
                ),
                sfx="chime",
                duration_est=float(sec_per_scene),
            ),
            DirectorScene(
                scene_id=4,
                name="Debate y Contraste de Hipótesis",
                type="chat_debate",
                emotion="skeptical",
                camera="pip_corner",
                speech=_build_speech(
                    "Pero también debemos plantearnos las preguntas incómodas y los dilemas de fondo: ",
                    scene4_phrases,
                    words_per_scene
                ),
                visual_query=f"{topic} critical debate controversy 4k",
                visual_queries=[f"{topic} dilemma 4k"],
                card=SceneCard(
                    headline="Realidad vs Hipótesis",
                    body="Contraste de modelos explicativos frente a las pruebas empíricas.",
                    badge="COMPARATIVA",
                    stat="Demostrado vs Especulación",
                ),
                sfx="whoosh",
                duration_est=float(sec_per_scene),
            ),
            DirectorScene(
                scene_id=5,
                name="Conclusiones y Cierre",
                type="avatar_cam",
                emotion="confident",
                camera="hero_center",
                speech=_build_speech(
                    "Dejen su postura en el chat. Los leo a todos porque este es un tema que nos involucra a cada uno de nosotros. ",
                    scene5_phrases,
                    words_per_scene
                ),
                visual_query="studio stream lighting 4k",
                visual_queries=["broadcast stream outro 4k"],
                sfx="chime",
                duration_est=float(sec_per_scene),
            ),
        ]
        return DirectorBroadcastPlan(
            title=f"KAI Broadcast: {topic}",
            topic=topic,
            style=style,
            scenes=scenes,
            chat_comments=[
                {"user": "AstroTech", "badge": "VIP", "text": "¡Impresionante dato KAI!"},
                {"user": "CodeMaster", "badge": "SUB", "text": "Totalmente de acuerdo con el análisis."},
                {"user": "NexusViewer", "badge": "VERIFIED", "text": "Las fuentes no dejan dudas."},
            ],
            total_est_duration=float(duration_target),
        )

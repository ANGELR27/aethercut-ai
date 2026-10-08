import re

UNIDADES = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
DECENAS_10 = ["diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve"]
VEINTES = ["veinte", "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve"]
DECENAS = ["", "diez", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
CENTENAS = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]


def numero_a_palabras(n: int) -> str:
    """Convierte un número entero positivo (hasta 999,999,999) en palabras en español continuo."""
    if n == 0:
        return "cero"
    if n == 100:
        return "cien"

    def _hasta_999(num: int) -> str:
        if num == 0:
            return ""
        if num == 100:
            return "cien"
        c = num // 100
        resto = num % 100
        partes = []
        if c > 0:
            partes.append(CENTENAS[c])
        if 10 <= resto <= 19:
            partes.append(DECENAS_10[resto - 10])
        elif 20 <= resto <= 29:
            partes.append(VEINTES[resto - 20])
        elif resto > 0:
            d = resto // 10
            u = resto % 10
            if d > 0 and u > 0:
                partes.append(f"{DECENAS[d]} y {UNIDADES[u]}")
            elif d > 0:
                partes.append(DECENAS[d])
            elif u > 0:
                partes.append(UNIDADES[u])
        return " ".join(partes)

    if n < 1000:
        return _hasta_999(n)

    if n < 1_000_000:
        miles = n // 1000
        resto = n % 1000
        prefijo = "mil" if miles == 1 else f"{_hasta_999(miles)} mil"
        sufijo = _hasta_999(resto)
        return f"{prefijo} {sufijo}".strip()

    if n < 1_000_000_000:
        millones = n // 1_000_000
        resto = n % 1_000_000
        prefijo = "un millón" if millones == 1 else f"{_hasta_999(millones)} millones"
        resto_str = numero_a_palabras(resto) if resto > 0 else ""
        return f"{prefijo} {resto_str}".strip()

    return str(n)


def refine_speech_cadence(text: str) -> str:
    """
    Pule la cadencia oral del texto insertando pausas naturales (comas y puntos):
    1. Si está disponible NVIDIA Nemotron (o LLM), aplica una refinación rápida de puntuación oral de radio.
    2. Si no hay conexión o falla, aplica reglas fonéticas deterministas del español (conectores causales,
       adversativos y temporales) para que la voz neural respire de forma humana sin ahogarse.
    """
    if not text or len(text.strip()) < 15:
        return text

    clean = text.strip()

    # Si ya contiene buena cantidad de comas (más de 1 coma cada 18 palabras), conservarlo
    words = clean.split()
    comma_count = clean.count(",")
    if len(words) > 0 and (comma_count / max(1, len(words))) >= 0.05:
        return clean

    # Intento 1: NVIDIA Nemotron 3.5 Lightning (Ultrarrápido y preciso para puntuación oral)
    try:
        from config.settings import settings
        if getattr(settings, "NVIDIA_API_KEY", None):
            from openai import OpenAI
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=settings.NVIDIA_API_KEY,
                timeout=5.0,
            )
            sys_msg = (
                "Eres un editor de guiones para locución de radio y televisión en español. "
                "Tu única tarea es insertar comas y puntos donde correspondan para que el locutor "
                "tenga pausas de respiración naturales y fluidas. No cambies las palabras, no agregues introducciones "
                "ni explicaciones, devuelve únicamente el texto puntuado."
            )
            resp = client.chat.completions.create(
                model=settings.NVIDIA_MODEL,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": clean},
                ],
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                max_tokens=len(clean) + 60,
                temperature=0.1,
            )
            candidate = resp.choices[0].message.content.strip().strip('"\'')
            if candidate and len(candidate.split()) >= len(words) - 2 and not candidate.startswith("Aquí"):
                return candidate
    except Exception:
        pass

    # Intento 2: Reglas fonéticas deterministas en español para locución natural
    # Añadir coma antes de conjunciones adversativas, causales y explicativas que vengan precedidas de 5+ palabras
    connectors = [
        "porque", "mientras", "donde", "aunque", "pero", "sino que", 
        "ya que", "dado que", "tras", "debido a que", "sin embargo", 
        "a pesar de que", "por lo que", "con lo cual"
    ]
    for conn in connectors:
        # Si el conector está precedido de una palabra y no tiene coma previa
        pattern = rf"(\b\w+\b)\s+({conn}\b)"
        def _add_comma(match):
            return f"{match.group(1)}, {match.group(2)}"
        clean = re.sub(pattern, _add_comma, clean, count=2)

    return clean


def normalize_speech_for_tts(text: str) -> str:
    """
    Normalización limpia y respetuosa de la voz:
    - Conserva 100% los acentos, tildes y signos naturales de puntuación del español.
    - Aplica refinación de cadencia oral (comas de respiración) para que el locutor hable fluido.
    - Únicamente limpia espacios dobles y asegura que los porcentajes (ej: 25%) se lean continuos.
    - Cero cortes mecánicos ni fragmentaciones artificiales.
    """
    if not text:
        return ""

    # Limpiar saltos de línea y espacios repetidos
    text = re.sub(r"\r?\n+", " ", text)
    text = re.sub(r"[ \t]+", " ", text).strip()

    # Normalizar porcentaje para lectura fonética correcta
    text = re.sub(r"(\d+)\s*%", r"\1 por ciento", text)

    # Refinar cadencia oral (comas de respiración) si el texto venía como un bloque plano sin comas
    text = refine_speech_cadence(text)

    # Eliminar dobles signos seguidos accidentales (ej: ,, o ..)
    text = re.sub(r"([,.])\1+", r"\1", text)

    return text

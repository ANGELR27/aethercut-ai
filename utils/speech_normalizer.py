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
    1. Si está disponible NVIDIA Nemotron (o LLM), extrae la versión puntuada con comas limpias.
    2. Reglas gramaticales y fonéticas del español para garantizar que ninguna frase de más de 8-10 palabras
       carezca de coma antes de conectores explicativos, causales o adversativos.
    """
    if not text or len(text.strip()) < 15:
        return text

    clean = text.strip()

    # Intento 1: NVIDIA Nemotron 3.5 Lightning (si está disponible)
    try:
        from config.settings import settings
        if getattr(settings, "NVIDIA_API_KEY", None):
            from openai import OpenAI
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=settings.NVIDIA_API_KEY,
                timeout=5.0,
            )
            prompt_refine = (
                "Reescribe el siguiente texto exactamente igual pero insertando comas naturales donde un locutor de radio "
                "deba respirar. No agregues saludos ni explicaciones, responde SOLO con el texto puntuado:\n\n" + clean
            )
            resp = client.chat.completions.create(
                model=settings.NVIDIA_MODEL,
                messages=[{"role": "user", "content": prompt_refine}],
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                max_tokens=len(clean) + 80,
                temperature=0.1,
            )
            raw_ans = resp.choices[0].message.content.strip()
            # Si el modelo devuelve un bloque con explicaciones o markdown, extraer la línea relevante
            lines = [l.strip().strip('*"`\'') for l in raw_ans.split("\n") if l.strip() and not l.strip().lower().startswith(("aquí", "por qué", "explicación", "1.", "2."))]
            for l in lines:
                if len(l.split()) >= len(clean.split()) - 3:
                    if l.count(",") >= 1:
                        return l
    except Exception:
        pass

    # Intento 2: Reglas fonéticas deterministas del español para locución de radio
    # Conectores y cláusulas que requieren pausa oral obligatoria si no llevan coma previa
    rules = [
        (r"(\b\w+\b)\s+(porque\b)", r"\1, porque"),
        (r"(\b\w+\b)\s+(mientras\b)", r"\1, mientras"),
        (r"(\b\w+\b)\s+(donde\b)", r"\1, donde"),
        (r"(\b\w+\b)\s+(aunque\b)", r"\1, aunque"),
        (r"(\b\w+\b)\s+(pero\b)", r"\1, pero"),
        (r"(\b\w+\b)\s+(sino que\b)", r"\1, sino que"),
        (r"(\b\w+\b)\s+(ya que\b)", r"\1, ya que"),
        (r"(\b\w+\b)\s+(dado que\b)", r"\1, dado que"),
        (r"(\b\w+\b)\s+(debido a que\b)", r"\1, debido a que"),
        (r"(\b\w+\b)\s+(sin embargo\b)", r"\1, sin embargo,"),
        (r"(\b\w+\b)\s+(por lo que\b)", r"\1, por lo que"),
        (r"(\b\w+\b)\s+(con lo cual\b)", r"\1, con lo cual"),
        (r"(\b\w+\b)\s+(demostrando\b)", r"\1, demostrando"),
        (r"(\b\w+\b)\s+(afectando\b)", r"\1, afectando"),
        (r"(\b\w+\b)\s+(generando\b)", r"\1, generando"),
        (r"(\b\w+\b)\s+(restando\b)", r"\1, restando"),
        (r"(\b\w+\b)\s+(poniendo en riesgo\b)", r"\1, poniendo en riesgo"),
    ]

    # Pausa tras cláusulas subordinadas largas iniciadas por 'Cuando ...' o 'Si ...'
    clean = re.sub(r"(Cuando\s+[\w\s]{18,38}?\b[A-Za-zÁ-ú]{4,})\s+(nos encontramos|vemos|chocamos|aparece|surge)", r"\1, \2", clean, flags=re.IGNORECASE)

    # Pausa tras 'en Colombia' o similares cuando van en medio de cláusula temporal
    clean = re.sub(r"(\ben Colombia)\s+(nos encontramos|vemos|analizamos)", r"\1, \2", clean, flags=re.IGNORECASE)

    for pat, rep in rules:
        clean = re.sub(pat, rep, clean, flags=re.IGNORECASE)

    # Si hay oraciones largas sin coma antes de 'y', agregar coma antes de la conjunción
    clean = re.sub(r"([A-Za-zÁ-ú]{4,}\s+[A-Za-zÁ-ú]{4,}\s+[A-Za-zÁ-ú]{4,})\s+y\s+([A-Za-zÁ-ú]{4,}\s+[A-Za-zÁ-ú]{4,})", r"\1, y \2", clean)

    # Limpiar dobles comas accidentales
    clean = re.sub(r",\s*,+", ", ", clean)
    clean = re.sub(r"\s+,\s*", ", ", clean)

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

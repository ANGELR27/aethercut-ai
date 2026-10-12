import re


def refine_speech_cadence(text: str) -> str:
    """
    Pule la cadencia oral del texto respetando la prosodia que el guionista
    (humano o LLM) diseñó. Edge-TTS respeta comas y puntos suspensivos como
    pausas reales, así que este pulido NUNCA elimina pausas legítimas:

    - NO toca comas de aposición ("Todo, absolutamente todo, cambió") ni comas
      antes de 'y' en incisos ("..., y con ello...") — antes las borraba y la
      voz perdía las pausas que el director pidió escribir.
    - NO colapsa puntos suspensivos '...' (pausa dramática del estilo podcast).
    - Solo corrige defectos mecánicos evidentes: comas duplicadas, comas sin
      espacio posterior (excepto decimales), espacios antes de coma y
      espacios faltantes después de punto.
    """
    if not text or len(text.strip()) < 5:
        return text

    clean = text.strip()

    # 1. Comas duplicadas o encadenadas: ',,,' → ','
    clean = re.sub(r',(\s*,)+', ',', clean)

    # 2. Espacios antes de coma: 'palabra ,' → 'palabra,'
    clean = re.sub(r'\s+,', ',', clean)

    # 3. Comas pegadas a la palabra siguiente (con espacio): 'dato,mas' → 'dato, mas'.
    #    El lookahead de dígito preserva los decimales españoles ('1,5 millones').
    clean = re.sub(r',([^\s\d])', r', \1', clean)

    # 4. Signos de exclamación/interrogación repetidos: '!!!' → '!', '???' → '?'.
    #    Los puntos suspensivos '...' se conservan: son pausa dramática intencional.
    clean = re.sub(r'([!?])\1+', r'\1', clean)

    # 5. Punto pegado a la palabra siguiente: 'frase.Siguiente' → 'frase. Siguiente'
    #    (solo si sigue letra: nunca rompe decimales '3.14' ni siglas con puntos).
    clean = re.sub(r'\.(?=[A-ZÁÉÍÓÚÑ])', '. ', clean)

    return clean


def clean_hyphenated_acronyms(text: str) -> str:
    """
    Convierte siglas artificialmente divididas por guiones ('A-D-N' -> 'ADN', 'I-A' -> 'IA', 'N-A-S-A' -> 'NASA')
    para que la voz neuronal de Edge-TTS las lea de forma fluida y natural, sin deletreos
    robóticos ni pausas incómodas entre letras.
    """
    if not text:
        return ""
    # Siglas de 2 a 6 letras mayúsculas separadas por guiones (ej. A-D-N, N-A-S-A, O-N-U, I-A)
    return re.sub(r'\b[A-ZÁÉÍÓÚÑ](?:-[A-ZÁÉÍÓÚÑ]){1,5}\b', lambda m: m.group(0).replace("-", ""), text)


def normalize_speech_for_tts(text: str) -> str:
    """
    Normalización limpia y de alta fidelidad para Edge-TTS:
    - Conserva 100% los acentos, tildes y entonación humana natural.
    - Convierte porcentajes fonéticamente ('25%' -> '25 por ciento').
    - Limpia siglas con guiones para pronunciación fluida ('A-D-N' -> 'ADN').
    - Limpia comas accidentales sin insertar pausas artificiales mecánicas.
    """
    if not text:
        return ""

    # Limpiar saltos de línea y espacios repetidos
    text = re.sub(r"\r?\n+", " ", text)
    text = re.sub(r"[ \t]+", " ", text).strip()

    # Des-guionar siglas mayúsculas artificiales
    text = clean_hyphenated_acronyms(text)

    # Normalizar porcentaje para lectura fonética correcta
    text = re.sub(r"(\d+)\s*%", r"\1 por ciento", text)

    # Pulir cadencia sin introducir frenadas o cortes en seco
    text = refine_speech_cadence(text)

    return text



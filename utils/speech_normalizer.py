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
    Pule la cadencia oral del texto respetando la prosodia natural de Edge-TTS:
    - NO inserta comas artificiales arbitrarias que provoquen pausas muertas o tartamudeo.
    - Corrige comas huérfanas entre determinantes, adjetivos y sustantivos (ej: 'ninguna, decisión' -> 'ninguna decisión').
    - Limpia comas antes de conjunciones copulativas innecesarias (ej: ', y' -> ' y').
    """
    if not text or len(text.strip()) < 5:
        return text

    clean = text.strip()

    # 1. Corregir comas huérfanas entre determinantes/pronombres/artículos y sustantivos
    clean = re.sub(
        r'\b(un|una|unos|unas|el|la|los|las|este|esta|estos|estas|ningún|ningun|ninguna|ninguno|todo|toda|cada|su|sus|mi|mis|tu|tus)\s*,\s*',
        r'\1 ',
        clean,
        flags=re.IGNORECASE,
    )

    # 2. Corregir comas accidentales antes de la conjunción 'y' en enumeraciones continuas
    clean = re.sub(r',\s+y\b', ' y', clean)

    # 3. Corregir comas pegadas a palabras o con espaciado incorrecto
    clean = re.sub(r'\s+,', ',', clean)
    clean = re.sub(r',([^\s\d])', r', \1', clean)

    # 4. Eliminar dobles comas o signos repetidos
    clean = re.sub(r',(\s*,)+', ',', clean)
    clean = re.sub(r'([,.])\1+', r'\1', clean)

    return clean


def normalize_speech_for_tts(text: str) -> str:
    """
    Normalización limpia y de alta fidelidad para Edge-TTS:
    - Conserva 100% los acentos, tildes y entonación humana natural.
    - Convierte porcentajes fonéticamente ('25%' -> '25 por ciento').
    - Limpia comas accidentales sin insertar pausas artificiales mecánicas.
    """
    if not text:
        return ""

    # Limpiar saltos de línea y espacios repetidos
    text = re.sub(r"\r?\n+", " ", text)
    text = re.sub(r"[ \t]+", " ", text).strip()

    # Normalizar porcentaje para lectura fonética correcta
    text = re.sub(r"(\d+)\s*%", r"\1 por ciento", text)

    # Pulir cadencia sin introducir frenadas o cortes en seco
    text = refine_speech_cadence(text)

    return text


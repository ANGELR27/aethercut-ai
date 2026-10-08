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


def normalize_speech_for_tts(text: str) -> str:
    """
    Normaliza el texto para síntesis neural ultra-fluida y natural:
    1. Convierte números arábigos aislados en palabras continuas para evitar pausas
       entre centenas y decenas (ej: '1965' -> 'mil novecientos sesenta y cinco').
    2. Suaviza comas mecánicas o dobles signos de puntuación que producen silencios truncados.
    3. Normaliza porcentajes, unidades y rangos ('20%' -> 'veinte por ciento').
    """
    if not text:
        return ""

    # Limpiar saltos de línea abruptos en mitad de oraciones
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Reemplazar porcentajes: 25% -> 25 por ciento
    text = re.sub(r"(\d+)\s*%", r"\1 por ciento", text)

    # Reemplazar rangos: 10-15 -> 10 a 15
    text = re.sub(r"(\d+)\s*-\s*(\d+)", r"\1 a \2", text)

    # Función para convertir dígitos enteros en palabras
    def _rep_num(match):
        num_str = match.group(0)
        try:
            val = int(num_str)
            if val <= 999_999_999:
                return numero_a_palabras(val)
        except Exception:
            pass
        return num_str

    # Convertir números enteros aislados (años, cifras, conteos)
    text = re.sub(r"\b\d+\b", _rep_num, text)

    # Limpiar comas duplicadas o puntuaciones extrañas que cortan la respiración del TTS
    text = re.sub(r"\s*,\s*,+", ",", text)
    text = re.sub(r"\s*;\s*", ", ", text)
    text = re.sub(r"\s*—\s*", " ", text)
    text = re.sub(r"\s*-\s*", " ", text)
    text = re.sub(r"\s*\.\s*\.+", ".", text)  # Eliminar puntos suspensivos que causan pausas muertas largas
    text = re.sub(r"\s*:\s*", ", ", text)

    # 1. Eliminar comas de muletilla y conectores iniciales ('Es que,', 'Y es que,', 'Pero,', 'Porque,', 'Así que,')
    # que causan que el locutor se quede parado al arrancar la frase
    text = re.sub(r"\b(es que|y es que|pero|porque|así que|por eso|o sea|la verdad|de hecho|en realidad|sin embargo|por tanto|por ende),\s*", r"\1 ", text, flags=re.IGNORECASE)

    # 2. Eliminar comas disruptivas antes de conjunciones que producen pausas falsas o artificiales en TTS
    text = re.sub(r",\s+(y|e|ni|o|u|que)\b", r" \1", text, flags=re.IGNORECASE)
    # Eliminar comas mecánicas pegadas a palabras de enlace
    text = re.sub(r",\s+(como|cuando|donde|porque|ya que|puesto que|pero|aunque|si)\b", r" \1", text, flags=re.IGNORECASE)

    # 3. Evitar coma tras primera palabra de oración (evita pausas innecesarias en el gancho)
    text = re.sub(r"^([A-ZÁÉÍÓÚa-záéíóú]+),\s+", r"\1 ", text)
    # Reducir pausas de punto y coma o dobles puntos seguidos
    text = re.sub(r"\s*([,.]){2,}\s*", r"\1 ", text)

    return text

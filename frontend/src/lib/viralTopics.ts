/* ------------------------------------------------------------------ */
/*  Motor de Temas Virales por Nicho para Videos de 10 a 40 Minutos   */
/* ------------------------------------------------------------------ */

export type ViralCategory =
  | "finanzas"
  | "amor"
  | "religion"
  | "versus"
  | "terror"
  | "misterio"
  | "politica"
  | "ciencia"
  | "curiosidades"
  | "historia"
  | "psicologia"
  | "crimen"
  | "tecnologia"
  | "narrativa";

export interface ViralTopic {
  id: string;
  title: string;
  nuances: string;
  category: ViralCategory;
  score: number; // Puntuación de viralidad (ej: +98)
  glyph: string;
  hookType: string;
  durationMin: number; // Duración recomendada de 10 a 40 minutos
}

export const CATEGORY_LABELS: Record<ViralCategory, { label: string; icon: string; desc: string }> = {
  finanzas: { label: "Finanzas", icon: "💰", desc: "Dinero, negocios e inversiones" },
  amor: { label: "Amor & Pareja", icon: "❤️", desc: "Relaciones, psicología y seducción" },
  religion: { label: "Religión", icon: "✝️", desc: "Fe cristiana y misterios bíblicos" },
  versus: { label: "Versus", icon: "⚔️", desc: "Comparativas de productos y personas" },
  terror: { label: "Terror", icon: "👻", desc: "Casos oscuros, creepypastas y terror psicológico" },
  misterio: { label: "Misterio", icon: "👁️", desc: "Enigmas mundiales y fenómenos inexplicables" },
  politica: { label: "Política", icon: "🏛️", desc: "Geopolítica, guerras de poder y secretos de estado" },
  ciencia: { label: "Ciencia", icon: "🔬", desc: "Astrofísica, cuántica y descubrimientos" },
  curiosidades: { label: "Curiosidades", icon: "💡", desc: "Datos increíbles que desafían la lógica" },
  historia: { label: "Historia", icon: "🏺", desc: "Civilizaciones, archivos y secretos de reyes" },
  psicologia: { label: "Psicología", icon: "🧠", desc: "Mente humana, sesgos y manipulación" },
  crimen: { label: "True Crime", icon: "🔍", desc: "Casos reales, secuestros y robos maestros" },
  tecnologia: { label: "Tecnología", icon: "🤖", desc: "IA, futuro y computación" },
  narrativa: { label: "Narrativa", icon: "🎬", desc: "Historias y técnicas de documental" },
};

export const ALL_CATEGORIES: ViralCategory[] = [
  "finanzas",
  "amor",
  "religion",
  "versus",
  "terror",
  "misterio",
  "politica",
  "ciencia",
  "curiosidades",
  "historia",
  "psicologia",
  "crimen",
  "tecnologia",
  "narrativa",
];

// Catálogo amplio y variado de nichos virales para videos de 10 a 40 minutos
const VIRAL_MASTER_POOL: ViralTopic[] = [
  // =========================================================================
  // 1. FINANZAS & DINERO (8 temas)
  // =========================================================================
  {
    id: "vt-fin-01",
    title: "Cómo los multimillonarios compran activos sin pagar impuestos (El método de la deuda)",
    nuances: "Estrategia 'Buy, Borrow, Die': cómo el colateral financiero evita el IRPF legalmente. Gráficos de flujo de capital y comparación con la clase media.",
    category: "finanzas",
    score: 98,
    glyph: "💰",
    hookType: "Estrategia de Riqueza",
    durationMin: 20,
  },
  {
    id: "vt-fin-02",
    title: "La burbuja inmobiliaria de 2026: qué pasará con las hipotecas y precios",
    nuances: "Ciclos de Kondrátiev y tasas de interés globales. Análisis de accesibilidad juvenil y tácticas de preservación de patrimonio.",
    category: "finanzas",
    score: 95,
    glyph: "📈",
    hookType: "Alerta Macroeconómica",
    durationMin: 25,
  },
  {
    id: "vt-fin-03",
    title: "El hombre que quebró el Banco de Inglaterra en 24 horas (George Soros)",
    nuances: "Crónica de la jugada contra la libra esterlina en 1992. Ritmo de thriller financiero minuto a minuto con pérdidas de 1.000 millones.",
    category: "finanzas",
    score: 96,
    glyph: "🏛️",
    hookType: "Caso Histórico Real",
    durationMin: 15,
  },
  {
    id: "vt-fin-04",
    title: "Los 5 errores financieros que destruyen tu patrimonio entre los 20 y los 35 años",
    nuances: "Interés compuesto negativo, inflación del estilo de vida y dependencia de una sola fuente de ingresos. Consejos accionables cada 4 minutos.",
    category: "finanzas",
    score: 93,
    glyph: "⚠️",
    hookType: "Educación Financiera",
    durationMin: 18,
  },
  {
    id: "vt-fin-05",
    title: "El colapso de una moneda: qué ocurre cuando el dinero fiduciario llega a cero",
    nuances: "De Weimar en 1923 a Zimbabue y Venezuela. Hiperinflación explicada con fotos de archivo y los activos reales que sobrevivieron.",
    category: "finanzas",
    score: 94,
    glyph: "📉",
    hookType: "Crisis Monetaria",
    durationMin: 30,
  },
  {
    id: "vt-fin-06",
    title: "Deuda buena vs Deuda mala: cómo usar el dinero del banco a tu favor",
    nuances: "Apalancamiento inmobiliario e inversión crediticia frente a tarjetas de crédito de consumo. Casos prácticos con balances reales.",
    category: "finanzas",
    score: 91,
    glyph: "⚖️",
    hookType: "Apalancamiento Inteligente",
    durationMin: 12,
  },
  {
    id: "vt-fin-07",
    title: "El imperio invisible de BlackRock: ¿Quién controla las mayores empresas del planeta?",
    nuances: "El algoritmo Aladdin, participaciones cruzadas con Vanguard y State Street. Estilo documental de investigación periodística profunda.",
    category: "finanzas",
    score: 99,
    glyph: "🌐",
    hookType: "Investigación Geopolítica",
    durationMin: 35,
  },
  {
    id: "vt-fin-08",
    title: "Psicología del dinero: por qué personas brillantes toman decisiones de inversión absurdas",
    nuances: "Basado en Morgan Housel: sesgo de supervivencia, aversión extrema a la pérdida y la falacia del coste hundido aplicada a la vida diaria.",
    category: "finanzas",
    score: 90,
    glyph: "🧠",
    hookType: "Psicología Económica",
    durationMin: 22,
  },

  // =========================================================================
  // 2. AMOR & RELACIONES (8 temas)
  // =========================================================================
  {
    id: "vt-amo-01",
    title: "La química del desamor: qué le ocurre a tu cerebro tras una ruptura traumática",
    nuances: "Caída drástica de dopamina y picos de cortisol idénticos a la abstinencia química. Protocolo neurocientífico para sanar más rápido.",
    category: "amor",
    score: 97,
    glyph: "💔",
    hookType: "Neurociencia Emocional",
    durationMin: 15,
  },
  {
    id: "vt-amo-02",
    title: "Por qué elegimos parejas que recrean las heridas no resueltas de nuestra infancia",
    nuances: "Teoría del apego ansioso vs evitativo. El bucle inconsciente de validación y cómo reconfigurar los patrones de atracción.",
    category: "amor",
    score: 96,
    glyph: "🧬",
    hookType: "Psicología Profunda",
    durationMin: 20,
  },
  {
    id: "vt-amo-03",
    title: "Las 4 señales que predicen una separación con 93% de precisión (Laboratorio Gottman)",
    nuances: "Desprecio, crítica destructiva, actitud defensiva y cerrazón comunicativa. Análisis de micro-interacciones con antídotos prácticos.",
    category: "amor",
    score: 98,
    glyph: "🔍",
    hookType: "Estudio Científico",
    durationMin: 25,
  },
  {
    id: "vt-amo-04",
    title: "El mito del alma gemela: la ciencia detrás del amor que dura más de 20 años",
    nuances: "Diferencia entre enamoramiento biológico (18 meses) y amor de apego seguro. Por qué la compatibilidad no se encuentra, se forja.",
    category: "amor",
    score: 92,
    glyph: "❤️",
    hookType: "Desmitificación Social",
    durationMin: 18,
  },
  {
    id: "vt-amo-05",
    title: "Bombardeo de amor (Love Bombing): cómo detectarlo en las primeras tres semanas",
    nuances: "Fase de idealización narcisista, regalos desmedidos y aislamiento progresivo. Señales de alarma y límites firmes antes del enganche.",
    category: "amor",
    score: 95,
    glyph: "🚩",
    hookType: "Señales de Alerta",
    durationMin: 14,
  },
  {
    id: "vt-amo-06",
    title: "Por qué las personas emocionalmente estables aburren a quienes crecieron en el caos",
    nuances: "Adicción inconsciente a la adrenalina y la incertidumbre. Re-educación del sistema nervioso para tolerar la paz en una relación.",
    category: "amor",
    score: 93,
    glyph: "⚡",
    hookType: "Revelación Íntima",
    durationMin: 16,
  },
  {
    id: "vt-amo-07",
    title: "El arte de la seducción psicológica: qué hace magnética e inolvidable a una persona",
    nuances: "Escucha reflexiva, misterio dosificado, autoconfianza no reactiva y respeto por los propios límites sin caer en juegos manipulativos.",
    category: "amor",
    score: 94,
    glyph: "✨",
    hookType: "Carisma y Atracción",
    durationMin: 22,
  },
  {
    id: "vt-amo-08",
    title: "Infidelidad emocional: la traición silenciosa en la era de los mensajes ocultos",
    nuances: "Micro-engaños digitales, confidencias íntimas fuera de la pareja y la pérdida gradual de intimidad. Cómo reconstruir la confianza rota.",
    category: "amor",
    score: 91,
    glyph: "📱",
    hookType: "Debate Contemporáneo",
    durationMin: 24,
  },

  // =========================================================================
  // 3. RELIGIÓN & FE CRISTIANA (8 temas)
  // =========================================================================
  {
    id: "vt-rel-01",
    title: "El misterio del Arca de la Alianza: ¿Dónde está guardada según la historia y la Biblia?",
    nuances: "Desde el Templo de Salomón hasta Aksum (Etiopía). Textos bíblicos, fuentes babilónicas y las investigaciones arqueológicas modernas.",
    category: "religion",
    score: 99,
    glyph: "✝️",
    hookType: "Enigma Bíblico",
    durationMin: 30,
  },
  {
    id: "vt-rel-02",
    title: "Las 7 profecías bíblicas que historiadores confirman que ya se cumplieron con exactitud",
    nuances: "La caída de Tiro, la dispersión de Jerusalén y las visiones de Daniel sobre imperios mundiales (Babilonia, Persia, Grecia y Roma).",
    category: "religion",
    score: 97,
    glyph: "📜",
    hookType: "Profecía y Evidencia",
    durationMin: 28,
  },
  {
    id: "vt-rel-03",
    title: "Los manuscritos del Mar Muerto: el descubrimiento que cambió la historia del texto bíblico",
    nuances: "Hallazgo de las cuevas de Qumrán en 1947: conservación milenaria de Isaías y la autenticidad textual frente a los críticos modernos.",
    category: "religion",
    score: 94,
    glyph: "🏺",
    hookType: "Arqueología Sagrada",
    durationMin: 35,
  },
  {
    id: "vt-rel-04",
    title: "Las últimas 24 horas de Jesús: el análisis forense y médico de la crucifixión romana",
    nuances: "Examen médico de la hematidrosis (sudor de sangre en Getsemaní), el flagelo romano y la asfixia postural en el madero del Calvario.",
    category: "religion",
    score: 98,
    glyph: "🕊️",
    hookType: "Historia Forense",
    durationMin: 25,
  },
  {
    id: "vt-rel-05",
    title: "El libro de Apocalipsis explicado sin mitos: qué significan los sellos, trompetas y copas",
    nuances: "Contexto histórico bajo la persecución de Domiciano. Decodificación de los símbolos y el mensaje central de esperanza y triunfo final.",
    category: "religion",
    score: 96,
    glyph: "📖",
    hookType: "Exégesis Profunda",
    durationMin: 40,
  },
  {
    id: "vt-rel-06",
    title: "La neurobiología de la oración: qué le ocurre al cerebro cuando hablas con Dios",
    nuances: "Estudios de neuroimagen (SPECT y resonancia) sobre la corteza prefrontal y la desactivación de la amígdala ante la fe perseverante.",
    category: "religion",
    score: 92,
    glyph: "🙏",
    hookType: "Ciencia y Espiritualidad",
    durationMin: 18,
  },
  {
    id: "vt-rel-07",
    title: "El rey Salomón: la sabiduría más grande del mundo y la caída más trágica de la historia",
    nuances: "Construcción del Templo, la reina de Saba, el libro de Eclesiastés y las consecuencias devastadoras de la idolatría en el reino.",
    category: "religion",
    score: 93,
    glyph: "👑",
    hookType: "Biografía Bíblica",
    durationMin: 22,
  },
  {
    id: "vt-rel-08",
    title: "Milagros documentados por comités médicos: cuando la ciencia no encuentra explicación",
    nuances: "Expedientes clínicos oficiales de remisiones de enfermedades incurables tras cadenas de oración validadas por juntas médicas independientes.",
    category: "religion",
    score: 95,
    glyph: "✨",
    hookType: "Fe y Evidencia Médica",
    durationMin: 20,
  },

  // =========================================================================
  // 4. VERSUS & COMPARATIVAS (8 temas)
  // =========================================================================
  {
    id: "vt-ver-01",
    title: "iPhone vs Samsung: La guerra secreta de 15 años por el monopolio de tu mente",
    nuances: "Juicios de patentes, ecosistemas cerrados vs abiertos y la paradoja de que Samsung fabrica componentes clave para los iPhone.",
    category: "versus",
    score: 97,
    glyph: "⚔️",
    hookType: "Guerra Tecnológica",
    durationMin: 25,
  },
  {
    id: "vt-ver-02",
    title: "Cristiano Ronaldo vs Lionel Messi: La comparativa definitiva analizada con datos puros",
    nuances: "Goles en fases eliminatorias de Champions y Mundiales, longevidad biomecánica, resiliencia y liderazgo en vestuario sin sesgo fanático.",
    category: "versus",
    score: 99,
    glyph: "⚽",
    hookType: "Duelo Histórico",
    durationMin: 30,
  },
  {
    id: "vt-ver-03",
    title: "Tesla vs BYD: La batalla geopolítica por el control de la energía y transporte mundial",
    nuances: "Modelos de integración vertical, extracción de litio en Sudamérica, fábricas automatizadas y subsidios gubernamentales chinos.",
    category: "versus",
    score: 96,
    glyph: "🔋",
    hookType: "Batalla Industrial",
    durationMin: 28,
  },
  {
    id: "vt-ver-04",
    title: "Comida ultraprocesada vs Alimentos reales: Qué le ocurre a tu sangre a las 2 horas exactas",
    nuances: "Experimento clínico comparativo con dos dietas idénticas en calorías. Picos de glucosa, inflamación endotelial y respuesta de saciedad.",
    category: "versus",
    score: 94,
    glyph: "🥗",
    hookType: "Experimento Fisiológico",
    durationMin: 15,
  },
  {
    id: "vt-ver-05",
    title: "Invertir en Oro vs Invertir en Bienes Raíces: ¿Cuál protege mejor tu dinero en una crisis?",
    nuances: "Rendimiento histórico en las 5 mayores recesiones mundiales, impuestos, liquidez y costes de mantenimiento comparados a 30 años.",
    category: "versus",
    score: 92,
    glyph: "🪙",
    hookType: "Duelo de Inversión",
    durationMin: 20,
  },
  {
    id: "vt-ver-06",
    title: "Trabajo remoto vs Trabajo presencial: Lo que las empresas descubrieron tras 5 años de datos",
    nuances: "Productividad real vs horas silla, aislamiento, creatividad espontánea y la reestructuración del mercado laboral global.",
    category: "versus",
    score: 90,
    glyph: "💻",
    hookType: "Sociedad Laboral",
    durationMin: 18,
  },
  {
    id: "vt-ver-07",
    title: "OpenAI vs Google Gemini: La carrera sin frenos por la primera Superinteligencia Artificial",
    nuances: "Modelos de razonamiento profundo, centros de datos nucleares, consumo hídrico y el dilema de seguridad frente a la competencia militar.",
    category: "versus",
    score: 98,
    glyph: "⚡",
    hookType: "Carrera por la AGI",
    durationMin: 24,
  },
  {
    id: "vt-ver-08",
    title: "Vida en la Tierra vs Colonia en Marte: Los obstáculos biológicos que Musk no suele mencionar",
    nuances: "Radiación cósmica galáctica, atrofia ósea por gravedad al 38% y la presión atmosférica marciana que evapora los fluidos humanos.",
    category: "versus",
    score: 93,
    glyph: "🚀",
    hookType: "Desafío Espacial",
    durationMin: 22,
  },

  // =========================================================================
  // 5. DATOS CURIOSOS & CIENCIA (8 temas)
  // =========================================================================
  {
    id: "vt-cur-01",
    title: "10 cosas cotidianas que fueron inventadas por un error monumental y cambiaron el mundo",
    nuances: "La penicilina de Fleming, el marcapasos, los microondas y el teflón. Anécdotas con giros imprevistos y lecciones de serendipia.",
    category: "curiosidades",
    score: 95,
    glyph: "💡",
    hookType: "Serendipia Científica",
    durationMin: 15,
  },
  {
    id: "vt-cur-02",
    title: "Por qué los pulpos podrían considerarse biológicamente seres de otro planeta",
    nuances: "Tres corazones, sangre azul basada en cobre hemocianina y cerebros periféricos en cada tentáculo que procesan decisiones autónomas.",
    category: "curiosidades",
    score: 96,
    glyph: "🐙",
    hookType: "Biología Extraña",
    durationMin: 20,
  },
  {
    id: "vt-cur-03",
    title: "El lugar más silencioso del planeta donde ningún ser humano soporta más de 45 minutos",
    nuances: "La cámara anecoica de Microsoft: ruido de fondo de -20.6 dB. Escuchar tus propios órganos, sangre fluyendo y la pérdida de equilibrio.",
    category: "curiosidades",
    score: 97,
    glyph: "🔇",
    hookType: "Límite Sensorial",
    durationMin: 12,
  },
  {
    id: "vt-cur-04",
    title: "El misterio del efecto Mandela: ¿Fallo masivo de la memoria colectiva o multiverso?",
    nuances: "Nelson Mandela, el logo de Monopoly y frases de películas icónicas. Análisis neurológico de la confabulación cognitiva espontánea.",
    category: "curiosidades",
    score: 93,
    glyph: "🌀",
    hookType: "Psicología de Masas",
    durationMin: 18,
  },
  {
    id: "vt-cur-05",
    title: "Qué le ocurriría exactamente a tu cuerpo si cayeras dentro de un agujero negro supermasivo",
    nuances: "Espaguetización por fuerzas de marea, dilatación temporal infinita vista por observadores externos y el horizonte de sucesos.",
    category: "curiosidades",
    score: 98,
    glyph: "🕳️",
    hookType: "Física Relativista",
    durationMin: 25,
  },
  {
    id: "vt-cur-06",
    title: "Las megaciudades subterráneas de las hormigas: civilizaciones de 8 millones de obreras",
    nuances: "Excavaciones vertiendo toneladas de cemento: sistemas de ventilación pasiva, carreteras subterráneas y cámaras de agricultura de hongos.",
    category: "curiosidades",
    score: 91,
    glyph: "🐜",
    hookType: "Arquitectura Animal",
    durationMin: 16,
  },
  {
    id: "vt-cur-07",
    title: "Por qué el tiempo parece acelerarse exponencialmente a medida que envejecemos",
    nuances: "Ley de Weber-Fechner y la tasa metabólica del procesamiento visual: procesamos menos fotogramas neuronales por segundo con los años.",
    category: "curiosidades",
    score: 94,
    glyph: "⏳",
    hookType: "Percepción Temporal",
    durationMin: 14,
  },
  {
    id: "vt-cur-08",
    title: "El peligro biológico atrapado en el permafrost ártico: virus con 48.000 años de letargo",
    nuances: "Bacterias como el ántrax congelado y virus gigantes desenterrados en Siberia ante los que el sistema inmune humano jamás combatió.",
    category: "curiosidades",
    score: 92,
    glyph: "❄️",
    hookType: "Riesgo Global",
    durationMin: 22,
  },

  // =========================================================================
  // 6. MISTERIO & CASOS REALES (8 temas)
  // =========================================================================
  {
    id: "vt-mis-01",
    title: "El enigma del Paso Dyatlov: La investigación científica que por fin descifró el suceso de 1959",
    nuances: "Avalancha de placa compacta, comportamiento paradójico de desvestirse por hipotermia y radiación residual en las ropas de montaña.",
    category: "misterio",
    score: 99,
    glyph: "🏔️",
    hookType: "Caso Clásico Resuelto",
    durationMin: 30,
  },
  {
    id: "vt-mis-02",
    title: "El robo del siglo en Amberes: Cómo saquearon la cámara acorazada más blindada del mundo",
    nuances: "Senadores de calor, radar Doppler, candado de 100 millones de combinaciones y el despiste del sandwich que delató a la banda.",
    category: "misterio",
    score: 97,
    glyph: "💎",
    hookType: "Atraco Real",
    durationMin: 28,
  },
  {
    id: "vt-mis-03",
    title: "La misteriosa desaparición de los marineros del Mary Celeste en aguas tranquilas",
    nuances: "Barco flotando a la deriva con comida en la mesa y pertenencias intactas pero sin un solo tripulante. Teorías de gases de alcohol.",
    category: "misterio",
    score: 91,
    glyph: "⛵",
    hookType: "Enigma Marítimo",
    durationMin: 20,
  },
  {
    id: "vt-mis-04",
    title: "El Asesino del Zodiaco: Los mensajes cifrados que tardaron 51 años en poder descifrarse",
    nuances: "El criptograma Z340, las cartas burlonas a la policía y el sospechoso principal que logró eludir a las autoridades hasta su muerte.",
    category: "misterio",
    score: 96,
    glyph: "🎯",
    hookType: "True Crime Histórico",
    durationMin: 35,
  },
  {
    id: "vt-mis-05",
    title: "Isla Sentinel del Norte: La tribu aislada durante 60.000 años que no permite el contacto",
    nuances: "La ley india de exclusión, la hostilidad visceral a los drones y barcos, y por qué un virus común podría extinguirlos a todos.",
    category: "misterio",
    score: 95,
    glyph: "🏝️",
    hookType: "Mundo Aislado",
    durationMin: 18,
  },
  {
    id: "vt-mis-06",
    title: "El Hotel Cecil: Crónica negra de las desapariciones y asesinos que habitaron el edificio",
    nuances: "Richard Ramírez, Jack Unterweger y el caso de Elisa Lam con análisis de las grabaciones del ascensor despojadas de amarillismo.",
    category: "misterio",
    score: 94,
    glyph: "🏨",
    hookType: "Crónica Urbana",
    durationMin: 32,
  },
  {
    id: "vt-mis-07",
    title: "El vuelo MH370 de Malaysia Airlines: Lo que las señales satelitales revelan 10 años después",
    nuances: "Los 'pings' hacia el arco del Océano Índico sur, el giro manual hacia el Estrecho de Malaca y el análisis de restos en Madagascar.",
    category: "misterio",
    score: 98,
    glyph: "✈️",
    hookType: "Desaparición Aérea",
    durationMin: 38,
  },
  {
    id: "vt-mis-08",
    title: "La ciudad subterránea de Derinkuyu: El refugio de 20.000 personas tallado bajo la roca",
    nuances: "Ocho niveles de profundidad en Turquía con puertas de piedra rodante de media tonelada, pozos de aireación y establos subterráneos.",
    category: "misterio",
    score: 93,
    glyph: "🏰",
    hookType: "Arqueología Enigmática",
    durationMin: 24,
  },

  // =========================================================================
  // 7. TECNOLOGÍA & IA (8 temas)
  // =========================================================================
  {
    id: "vt-tec-01",
    title: "La Singularidad Tecnológica: Qué ocurrirá el día que la IA cree una IA más inteligente que ella",
    nuances: "Crecimiento exponencial recursivo de la inteligencia, el test de Turing obsoleto y las predicciones de Ray Kurzweil para 2029-2035.",
    category: "tecnologia",
    score: 98,
    glyph: "🤖",
    hookType: "Futuro Exponencial",
    durationMin: 25,
  },
  {
    id: "vt-tec-02",
    title: "Computación cuántica explicada para mortales: Por qué romperá todo el cifrado bancario",
    nuances: "Superposición cuántica, entrelazamiento de qubits y la carrera de los gobiernos por el cifrado post-cuántico antes del 'Día Q'.",
    category: "tecnologia",
    score: 95,
    glyph: "⚛️",
    hookType: "Seguridad Digital",
    durationMin: 22,
  },
  {
    id: "vt-tec-03",
    title: "La guerra por los microchips de 2 nanómetros: Por qué Taiwán y ASML controlan el mundo",
    nuances: "Litografía ultravioleta extrema (EUV), espejos Zeiss de precisión atómica y la dependencia económica y militar de EEUU y China.",
    category: "tecnologia",
    score: 97,
    glyph: "🔬",
    hookType: "Geopolítica del Chip",
    durationMin: 30,
  },
  {
    id: "vt-tec-04",
    title: "Neuralink y la interfaz cerebro-computadora: De curar parálisis a la telepatía digital",
    nuances: "Ensayos en pacientes humanos reales, lectura de señales motoras en tiempo real y el dilema bioético de la privacidad mental.",
    category: "tecnologia",
    score: 94,
    glyph: "🧠",
    hookType: "Biotecnología",
    durationMin: 20,
  },
  {
    id: "vt-tec-05",
    title: "Deepfakes y clonación de voz indetectable: El colapso inminente de la prueba judicial",
    nuances: "Modelos generativos de video en tiempo real, estafas telefónicas con 3 segundos de audio clonado y cómo proteger tu identidad.",
    category: "tecnologia",
    score: 96,
    glyph: "🎭",
    hookType: "Ciberseguridad",
    durationMin: 18,
  },
  {
    id: "vt-tec-06",
    title: "Reactores de fusión nuclear comercial: Cómo recrear el corazón del Sol en la Tierra",
    nuances: "Tokamaks magnéticos, proyectos ITER y el récord de ganancia neta de energía (Q>1). La promesa de energía infinita limpia.",
    category: "tecnologia",
    score: 91,
    glyph: "☀️",
    hookType: "Energía del Futuro",
    durationMin: 26,
  },
  {
    id: "vt-tec-07",
    title: "La muerte de las contraseñas: Cómo funcionan las Passkeys y la autenticación biométrica",
    nuances: "Criptografía asimétrica de curva elíptica integrada en chips de seguridad (Enclave Seguro) y por qué las claves tradicionales deben morir.",
    category: "tecnologia",
    score: 89,
    glyph: "🔑",
    hookType: "Privacidad",
    durationMin: 14,
  },
  {
    id: "vt-tec-08",
    title: "Starlink y la constelación de 40.000 satélites: Cómo cambiará la geopolítica de las comunicaciones",
    nuances: "Láser intersatelital en órbita baja, baja latencia en zonas remotas de conflicto y el problema de la basura espacial (Síndrome de Kessler).",
    category: "tecnologia",
    score: 93,
    glyph: "🛰️",
    hookType: "Infraestructura Global",
    durationMin: 22,
  },

  // =========================================================================
  // 8. NARRATIVA & DOCUMENTAL (8 temas)
  // =========================================================================
  {
    id: "vt-nar-01",
    title: "Estructura del documental magnético: Cómo mantener enganchada a la audiencia 30 minutos",
    nuances: "El viaje del héroe adaptado a no ficción; micro-revelaciones cada 3 minutos y resolución de tensión acumulada al cierre.",
    category: "narrativa",
    score: 95,
    glyph: "🎬",
    hookType: "Guion de Alta Retención",
    durationMin: 20,
  },
  {
    id: "vt-nar-02",
    title: "Las técnicas de montaje de Christopher Nolan: Controlar la percepción del tiempo",
    nuances: "Montaje alterno paralelo (Cross-cutting), líneas temporales convergentes y la banda sonora en forma de escala Shepard continua.",
    category: "narrativa",
    score: 97,
    glyph: "⏳",
    hookType: "Cine y Edición",
    durationMin: 25,
  },
  {
    id: "vt-nar-03",
    title: "El poder del silencio en el cine: Cuándo quitar la música crea tensión insoportable",
    nuances: "Escenas maestras de No Country for Old Men y Alien. La psicología de la pausa auditiva que obliga al espectador a contener la respiración.",
    category: "narrativa",
    score: 92,
    glyph: "🤫",
    hookType: "Diseño Sonoro",
    durationMin: 15,
  },
  {
    id: "vt-nar-04",
    title: "Cómo construir un antagonista que la audiencia no pueda odiar (De Joker a Walter White)",
    nuances: "Justificación moral interna, coherencia psicológica y el espejo oscuro de los deseos reprimidos de la sociedad.",
    category: "narrativa",
    score: 96,
    glyph: "👤",
    hookType: "Psicología de Personajes",
    durationMin: 24,
  },
  {
    id: "vt-nar-05",
    title: "El arte de la revelación de datos estilo Vox: Convertir estadísticas aburridas en espectáculo",
    nuances: "Tarjetas bento cinéticas, mapas tácticos con zoom milimétrico y animación de tipografía en los momentos cumbre de la locución.",
    category: "narrativa",
    score: 94,
    glyph: "📊",
    hookType: "Storytelling Visual",
    durationMin: 18,
  },
  {
    id: "vt-nar-06",
    title: "El gancho narrativo en tres actos: Cómo abrir con intriga y no desinflarse a mitad del video",
    nuances: "Planteamiento de la incógnita dramática en 10 segundos, siembra de pistas y giros que subvierten las expectativas del espectador.",
    category: "narrativa",
    score: 93,
    glyph: "🎯",
    hookType: "Estructura Dramática",
    durationMin: 22,
  },
  {
    id: "vt-nar-07",
    title: "Por qué los documentales de crímenes reales son adictivos: La paradoja del miedo seguro",
    nuances: "Catarsis psicológica, preparación para amenazas del entorno y el atractivo morboso del misterio forense sin peligro real.",
    category: "narrativa",
    score: 95,
    glyph: "🔎",
    hookType: "Análisis Sociológico",
    durationMin: 28,
  },
  {
    id: "vt-nar-08",
    title: "El efecto Kuleshov: Cómo dos imágenes juntas crean una tercera emoción en el espectador",
    nuances: "El principio fundacional del montaje cinematográfico soviético y su aplicación directa a los videos de YouTube modernos.",
    category: "narrativa",
    score: 91,
    glyph: "🎞️",
    hookType: "Teoría del Montaje",
    durationMin: 16,
  },

  // =========================================================================
  // 9. TERROR & HORROR (8 temas)
  // =========================================================================
  {
    id: "vt-ter-01",
    title: "El misterio del Paso Dyatlov: La noche que la montaña se tragó a 9 excursionistas",
    nuances: "Análisis forense de la radiación inexplicable, fracturas sin impacto externo y las últimas fotografías de la cámara.",
    category: "terror",
    score: 99,
    glyph: "🏔️",
    hookType: "Expedición Trágica",
    durationMin: 28,
  },
  {
    id: "vt-ter-02",
    title: "Los sonidos submarinos sin identificar: Del 'Bloop' a 'Julia' en las fosas abisales",
    nuances: "Espectrogramas de la NOAA, hidroacústica militar durante la Guerra Fría y criaturas hipotéticas de las profundidades marinas.",
    category: "terror",
    score: 96,
    glyph: "🌊",
    hookType: "Terror Abisal",
    durationMin: 22,
  },
  {
    id: "vt-ter-03",
    title: "La perturbadora historia del Hotel Cecil y la habitación de los asesinos",
    nuances: "Richard Ramirez, Jack Unterweger, Elisa Lam y el fenómeno de la sincronicidad arquitectónica en Los Ángeles.",
    category: "terror",
    score: 98,
    glyph: "🏨",
    hookType: "True Horror",
    durationMin: 35,
  },
  {
    id: "vt-ter-04",
    title: "El experimento ruso del sueño: El límite donde la mente humana colapsa",
    nuances: "El gas estimulante de los años 40, paranoia soviética, testimonios clasificados y el mito frente a la fisiología del insomnio extremo.",
    category: "terror",
    score: 97,
    glyph: "☣️",
    hookType: "Psicosis Colectiva",
    durationMin: 20,
  },
  {
    id: "vt-ter-05",
    title: "Skinwalker Ranch: 500 acres de anomalías biológicas y objetos no identificados",
    nuances: "La compra secreta del magnate Robert Bigelow, monitoreo del Pentágono, radiación gamma y mutilaciones inexplicables de ganado.",
    category: "terror",
    score: 95,
    glyph: "🛸",
    hookType: "Paranormal Clasificado",
    durationMin: 32,
  },
  {
    id: "vt-ter-06",
    title: "La frecuencia del miedo: Cómo el infrasonido de 18.9 Hz hackea tu cerebro",
    nuances: "La investigación de Vic Tandy, cómo la frecuencia de resonancia del globo ocular provoca alucinaciones visuales y ataques de pánico.",
    category: "terror",
    score: 94,
    glyph: "🔊",
    hookType: "Terror Científico",
    durationMin: 15,
  },
  {
    id: "vt-ter-07",
    title: "El bosque de Aokigahara: La geología magnética y los mitos de los Ubasute",
    nuances: "Roca volcánica que anula las brújulas, patrullas silenciosas del Monte Fuji y la psicología detrás del aislamiento contemporáneo.",
    category: "terror",
    score: 96,
    glyph: "🌲",
    hookType: "Misterio Oscuro",
    durationMin: 25,
  },
  {
    id: "vt-ter-08",
    title: "Cuentas congeladas en la Antártida: Los incidentes olvidados de la Operación Highjump",
    nuances: "La flota del almirante Byrd en 1947, pérdidas no documentadas en el hielo y bitácoras de vuelo que contradicen los informes oficiales.",
    category: "terror",
    score: 97,
    glyph: "❄️",
    hookType: "Enigma Bélico",
    durationMin: 30,
  },

  // =========================================================================
  // 10. POLÍTICA & GEOPOLÍTICA (8 temas)
  // =========================================================================
  {
    id: "vt-pol-01",
    title: "La trampa de Tucídides: Por qué la guerra entre potencias parece inevitable",
    nuances: "Comparativa histórica de Atenas vs Esparta, Reino Unido vs Alemania en 1914 y la tensión actual en el estrecho de Taiwán.",
    category: "politica",
    score: 98,
    glyph: "⚔️",
    hookType: "Geopolítica Global",
    durationMin: 35,
  },
  {
    id: "vt-pol-02",
    title: "El fin del Petrodólar: El acuerdo secreto de 1974 y la rebelión de los BRICS+",
    nuances: "El pacto Kissinger-Faisal, desdolarización del comercio marítimo, reservas soberanas y el nuevo sistema multilateral.",
    category: "politica",
    score: 99,
    glyph: "💵",
    hookType: "Economía de Poder",
    durationMin: 30,
  },
  {
    id: "vt-pol-03",
    title: "Cómo funciona la guerra psicológica moderna: De Cambridge Analytica a los algoritmos cognitivos",
    nuances: "Microtargeting político, polarización algorítmica, botfarms militares y la manipulación de la opinión pública en comicios.",
    category: "politica",
    score: 97,
    glyph: "🧠",
    hookType: "Guerra de Información",
    durationMin: 25,
  },
  {
    id: "vt-pol-04",
    title: "El estrecho de Malaca: El cuello de botella que podría paralizar al planeta en 48 horas",
    nuances: "El 80% del crudo asiático concentrado en 2.8 km de ancho. Estrategias de bloqueo naval y rutas alternativas por el Ártico.",
    category: "politica",
    score: 96,
    glyph: "🚢",
    hookType: "Geopolítica Crítica",
    durationMin: 20,
  },
  {
    id: "vt-pol-05",
    title: "La diplomacia de la deuda: Cómo se compran puertos e infraestructuras estratégicas sin disparar un tiro",
    nuances: "El caso del puerto Hambantota en Sri Lanka, contratos de arrendamiento por 99 años y la nueva ruta de la seda.",
    category: "politica",
    score: 95,
    glyph: "🏗️",
    hookType: "Estrategia de Estado",
    durationMin: 28,
  },
  {
    id: "vt-pol-06",
    title: "La doctrina de la destrucción mutua asegurada (MAD): Los 5 días que casi acaban con el mundo",
    nuances: "La crisis de los misiles de Cuba en 1962, el incidente de Stanislav Petrov en 1983 y los protocolos de los maletines nucleares.",
    category: "politica",
    score: 99,
    glyph: "🚀",
    hookType: "Historia Diplomática",
    durationMin: 38,
  },
  {
    id: "vt-pol-07",
    title: "El negocio de la reconstrucción: Quién gana realmente cuando termina un conflicto bélico",
    nuances: "Licitaciones multimillonarias, fondos de inversión soberanos, empresas contratistas y la deuda soberana post-guerra.",
    category: "politica",
    score: 94,
    glyph: "💼",
    hookType: "Poder y Capital",
    durationMin: 22,
  },
  {
    id: "vt-pol-08",
    title: "El control del agua dulce: El próximo gran conflicto que ya comenzó en los grandes ríos",
    nuances: "La represa del Renacimiento en el río Nilo (Egipto vs Etiopía), el Tíbet como torre de agua asiática y tratados en crisis.",
    category: "politica",
    score: 96,
    glyph: "💧",
    hookType: "Recursos Críticos",
    durationMin: 26,
  },

  // =========================================================================
  // 11. CIENCIA & COSMOS (8 temas)
  // =========================================================================
  {
    id: "vt-cie-01",
    title: "El misterio de la materia oscura: El 85% del universo que no podemos ver ni tocar",
    nuances: "Lentes gravitacionales, curvas de rotación galáctica de Vera Rubin, partículas WIMP y la teoría MOND que desafía a Einstein.",
    category: "ciencia",
    score: 99,
    glyph: "🌌",
    hookType: "Física Fundamental",
    durationMin: 32,
  },
  {
    id: "vt-cie-02",
    title: "La paradoja de Fermi: Si el universo es infinito, ¿por qué hay tanto silencio?",
    nuances: "La hipótesis del Gran Filtro, el Bosque Oscuro de Liu Cixin, civilizaciones tipo III en la escala Kardashev y planetas océano.",
    category: "ciencia",
    score: 98,
    glyph: "📡",
    hookType: "Astrofísica Teórica",
    durationMin: 28,
  },
  {
    id: "vt-cie-03",
    title: "Entrelazamiento cuántico: Por qué Einstein lo llamó 'acción fantasmal a distancia'",
    nuances: "El teorema de Bell, experimentos con fotones entrelazados a miles de kilómetros y teleportación de información cuántica.",
    category: "ciencia",
    score: 97,
    glyph: "⚛️",
    hookType: "Mecánica Cuántica",
    durationMin: 24,
  },
  {
    id: "vt-cie-04",
    title: "El telescopio James Webb vio lo que no debería existir: Galaxias que desafían el Big Bang",
    nuances: "Galaxias masivas formadas apenas 300 millones de años tras el inicio. La crisis cosmológica de la tensión de Hubble.",
    category: "ciencia",
    score: 99,
    glyph: "🔭",
    hookType: "Cosmología de Vanguardia",
    durationMin: 35,
  },
  {
    id: "vt-cie-05",
    title: "Crispr y la reprogramación genética: La era donde el ser humano decide su propia evolución",
    nuances: "Edición de embriones en laboratorio, erradicación de enfermedades hereditarias y el debate bioético de los bebés de diseño.",
    category: "ciencia",
    score: 96,
    glyph: "🧬",
    hookType: "Biotecnología",
    durationMin: 22,
  },
  {
    id: "vt-cie-06",
    title: "La muerte térmica del cosmos: Qué ocurrirá dentro de un googol de años",
    nuances: "La era de los agujeros negros, radiación Hawking, evaporación de bariones y el fin absoluto de la entropía cósmica.",
    category: "ciencia",
    score: 95,
    glyph: "⏳",
    hookType: "Destino del Universo",
    durationMin: 30,
  },
  {
    id: "vt-cie-07",
    title: "El experimento de la doble rendija: Cuando la realidad cambia solo porque la observas",
    nuances: "Dualidad onda-partícula, borrador cuántico con elección retardada y el problema de la medición en física de partículas.",
    category: "ciencia",
    score: 97,
    glyph: "👁️",
    hookType: "Enigma de la Materia",
    durationMin: 18,
  },
  {
    id: "vt-cie-08",
    title: "Vida bajo el hielo: Los océanos secretos de Europa y Encélado",
    nuances: "Géisers hidrotérmicos alimentados por fuerzas de marea de Júpiter y Saturno; por qué es el lugar más probable para vida extraterrestre.",
    category: "ciencia",
    score: 96,
    glyph: "🪐",
    hookType: "Exobiología",
    durationMin: 26,
  },

  // =========================================================================
  // 12. HISTORIA & SECRETOS (8 temas)
  // =========================================================================
  {
    id: "vt-his-01",
    title: "El colapso de la Edad del Bronce: El cataclismo que borró 8 imperios en 50 años",
    nuances: "Los misteriosos Pueblos del Mar, sequías masivas, ruptura de redes comerciales de estaño y la caída simultánea de Micenas y los Hititas.",
    category: "historia",
    score: 98,
    glyph: "🏛️",
    hookType: "Apocalipsis Antiguo",
    durationMin: 36,
  },
  {
    id: "vt-his-02",
    title: "Los archivos secretos del Vaticano: 85 kilómetros de estanterías y lo que realmente contienen",
    nuances: "Cartas de María Estuardo, juicios de los Caballeros Templarios, actas de Galileo Galilei y documentos desclasificados del siglo XX.",
    category: "historia",
    score: 99,
    glyph: "📜",
    hookType: "Documentos Ocultos",
    durationMin: 30,
  },
  {
    id: "vt-his-03",
    title: "Cómo una sola moneda causó la caída del Imperio Romano (La gran inflación de plata)",
    nuances: "La degradación del denario bajo Nerón y Caracalla, la crisis del siglo III y cómo el descontrol monetario destruyó el ejército profesional.",
    category: "historia",
    score: 97,
    glyph: "🪙",
    hookType: "Economía Histórica",
    durationMin: 25,
  },
  {
    id: "vt-his-04",
    title: "La biblioteca de Alejandría no se quemó en un día: La verdadera crónica de su extinción",
    nuances: "El incendio de Julio César en el 48 a.C., los decretos de Teodosio y el olvido burocrático que causó la mayor pérdida de conocimiento.",
    category: "historia",
    score: 95,
    glyph: "📚",
    hookType: "Tragedia Intelectual",
    durationMin: 22,
  },
  {
    id: "vt-his-05",
    title: "La dinastía banquera que financió a todos los reyes de Europa: El auge de los Médici",
    nuances: "La contabilidad por partida doble, el control del Papado, el mecenazgo del Renacimiento y los asesinatos políticos de Florencia.",
    category: "historia",
    score: 96,
    glyph: "👑",
    hookType: "Poder y Mecenazgo",
    durationMin: 28,
  },
  {
    id: "vt-his-06",
    title: "Los guerreros olvidados de la Operación Mincemeat: El cadáver que engañó a Hitler",
    nuances: "El plan de inteligencia naval británica de Ian Fleming para desviar divisiones Panzer hacia Grecia fingiendo un desembarco inexistente.",
    category: "historia",
    score: 96,
    glyph: "🪖",
    hookType: "Espionaje Militar",
    durationMin: 24,
  },
  {
    id: "vt-his-07",
    title: "La peste negra: Cómo una bacteria rediseñó el mapa económico y los derechos laborales de Europa",
    nuances: "La muerte de un tercio de la población, el colapso del feudalismo, el aumento salarial campesino y el nacimiento de la clase media.",
    category: "historia",
    score: 97,
    glyph: "🐀",
    hookType: "Pandemia y Sociedad",
    durationMin: 32,
  },
  {
    id: "vt-his-08",
    title: "Göbekli Tepe: El templo de 11.500 años que obliga a reescribir la historia de la agricultura",
    nuances: "Monolitos tallados con animales en relieve milenios antes de Stonehenge y las pirámides; el culto religioso antes que las ciudades.",
    category: "historia",
    score: 98,
    glyph: "🗿",
    hookType: "Arqueología Revolucionaria",
    durationMin: 34,
  },

  // =========================================================================
  // 13. PSICOLOGÍA & MENTE (8 temas)
  // =========================================================================
  {
    id: "vt-psi-01",
    title: "El experimento de la cárcel de Stanford: Cómo personas buenas cometen actos crueles en 6 días",
    nuances: "Philip Zimbardo, desindividualización, autoridad ciega y las grabaciones inéditas que revelan cómo se salió de control.",
    category: "psicologia",
    score: 98,
    glyph: "⛓️",
    hookType: "Psicología Social",
    durationMin: 26,
  },
  {
    id: "vt-psi-02",
    title: "Gaslighting y manipulación encubierta: Las 7 micro-técnicas que usan los narcisistas",
    nuances: "Reescritura de recuerdos, aislamiento progresivo, triangulación afectiva y el protocolo para desarmar la niebla mental.",
    category: "psicologia",
    score: 97,
    glyph: "🎭",
    hookType: "Relaciones Tóxicas",
    durationMin: 20,
  },
  {
    id: "vt-psi-03",
    title: "Por qué el cerebro humano prefiere creer una mentira cómoda antes que una verdad incómoda",
    nuances: "Disonancia cognitiva de Leon Festinger, el sesgo de confirmación y cómo la identidad social bloquea los datos racionales.",
    category: "psicologia",
    score: 95,
    glyph: "🧩",
    hookType: "Sesgos Cognitivos",
    durationMin: 22,
  },
  {
    id: "vt-psi-04",
    title: "El efecto Dunning-Kruger: Por qué los menos competentes son los más seguros de sí mismos",
    nuances: "El valle de la desesperación, la montaña de la arrogancia y cómo la ignorancia genera más confianza que el conocimiento real.",
    category: "psicologia",
    score: 94,
    glyph: "📈",
    hookType: "Comportamiento",
    durationMin: 16,
  },
  {
    id: "vt-psi-05",
    title: "La psicología del dinero: Por qué ser inteligente no te hace rico",
    nuances: "El sesgo de supervivencia, la envidia como motor de bancarrota y por qué el éxito financiero es más de conducta que de números.",
    category: "psicologia",
    score: 98,
    glyph: "💳",
    hookType: "Mentalidad Financiera",
    durationMin: 28,
  },
  {
    id: "vt-psi-06",
    title: "El experimento Milgram: El 65% de las personas aplicaría descargas letales si se lo ordenan",
    nuances: "La autoridad de la bata blanca en la Universidad de Yale, tensión ética y la anatomía de los regímenes totalitarios.",
    category: "psicologia",
    score: 97,
    glyph: "⚡",
    hookType: "Obediencia Ciega",
    durationMin: 24,
  },
  {
    id: "vt-psi-07",
    title: "La tríada oscura de la personalidad: Maquiavelismo, narcisismo y psicopatía en el trabajo",
    nuances: "Cómo ascienden en las corporaciones, encanto superficial, falta de empatía selectiva y métodos de defensa asertiva.",
    category: "psicologia",
    score: 96,
    glyph: "♟️",
    hookType: "Personalidad Humana",
    durationMin: 25,
  },
  {
    id: "vt-psi-08",
    title: "La trampa de la dopamina barata: Por qué nos sentimos vacíos con entretenimiento ilimitado",
    nuances: "Receptores D2 desensibilizados por scrolls infinitos, la báscula de placer-dolor de Anna Lembke y el reseteo de motivación.",
    category: "psicologia",
    score: 97,
    glyph: "📱",
    hookType: "Neurociencia Cotidiana",
    durationMin: 23,
  },

  // =========================================================================
  // 14. TRUE CRIME & CASOS REALES (8 temas)
  // =========================================================================
  {
    id: "vt-cri-01",
    title: "El misterio de D.B. Cooper: El único secuestro aéreo sin resolver en la historia de la aviación",
    nuances: "El salto con 200.000 dólares en una noche de tormenta sobre el noroeste del Pacífico, el billete encontrado en el río y sospechosos del FBI.",
    category: "crimen",
    score: 98,
    glyph: "🪂",
    hookType: "Crimen Imposible",
    durationMin: 30,
  },
  {
    id: "vt-cri-02",
    title: "El caso del Asesino del Zodiaco y los criptogramas que tardaron 51 años en descifrarse",
    nuances: "Las cartas a los periódicos de San Francisco, el descifrado del cifrado 340 en 2020 por David Oranchak y el perfil psicológico.",
    category: "crimen",
    score: 99,
    glyph: "🔏",
    hookType: "Criptografía y Crimen",
    durationMin: 34,
  },
  {
    id: "vt-cri-03",
    title: "El robo del siglo: Cómo vaciaron la caja acorazada del Banco Río sin disparar un tiro",
    nuances: "Armas de juguete, rehenes negociados por horas mientras escapaban en botes inflables por el desagüe pluvial con millones.",
    category: "crimen",
    score: 97,
    glyph: "🏦",
    hookType: "Atraco Perfecto",
    durationMin: 28,
  },
  {
    id: "vt-cri-04",
    title: "Madoff y el mayor esquema Ponzi de la historia: 64.000 millones de dólares en humo",
    nuances: "Cómo engañó a bancos de Wall Street durante 30 años, las alertas ignoradas de Harry Markopolos y el derrumbe en 2008.",
    category: "crimen",
    score: 98,
    glyph: "📉",
    hookType: "Fraude Financiero",
    durationMin: 32,
  },
  {
    id: "vt-cri-05",
    title: "La desaparición de Madeleine McCann: Las 7 inconsistencias que los detectives nunca resolvieron",
    nuances: "Cronología minuto a minuto en Praia da Luz, peritajes caninos, la pista alemana de Christian Brueckner y la cooperación de Interpol.",
    category: "crimen",
    score: 99,
    glyph: "🔎",
    hookType: "Caso Abierto",
    durationMin: 38,
  },
  {
    id: "vt-cri-06",
    title: "Catch Me If You Can: La verdadera historia de Frank Abagnale Jr. (Mito vs Realidad)",
    nuances: "Falsificación de cheques de Pan Am, la mitomanía desmentida por periodistas de investigación y cómo construyó su leyenda mediática.",
    category: "crimen",
    score: 95,
    glyph: "✈️",
    hookType: "Estafa Maestra",
    durationMin: 24,
  },
  {
    id: "vt-cri-07",
    title: "El asesino de la baraja: El rastro del naipe en las calles de Madrid",
    nuances: "La pistola Tokarev soviética traída de Bosnia, crímenes sin móvil aparente y la confesión inesperada en una comisaría de Puertollano.",
    category: "crimen",
    score: 96,
    glyph: "🃏",
    hookType: "Perfil Criminal",
    durationMin: 26,
  },
  {
    id: "vt-cri-08",
    title: "Silk Road y Dread Pirate Roberts: El imperio del mercado negro en la Dark Web",
    nuances: "Ross Ulbricht, transacciones en Bitcoin anónimas, agentes corruptos de la DEA y la trampa en la biblioteca pública de San Francisco.",
    category: "crimen",
    score: 98,
    glyph: "💻",
    hookType: "Ciberdelincuencia",
    durationMin: 35,
  },
];

const STORAGE_PINNED_KEY = "lumen_pinned_viral_topics";
const STORAGE_DAILY_TOPICS_KEY = "lumen_daily_viral_topics";
const STORAGE_DATE_KEY = "lumen_viral_topics_date";

/**
 * Obtiene los IDs de los temas anclados/favoritos desde localStorage
 */
export function getStoredPinnedIds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_PINNED_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/**
 * Guarda los IDs de los temas anclados en localStorage y en el backend
 */
export function savePinnedIds(ids: string[], topicObj?: ViralTopic, isAdding?: boolean): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_PINNED_KEY, JSON.stringify(ids));
  } catch {}

  // Sincronización en segundo plano con el backend
  if (topicObj) {
    try {
      fetch("/api/trend-radar/favorites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: isAdding ? "add" : "remove",
          topic: {
            id: topicObj.id,
            title: topicObj.title,
            category: topicObj.category,
            score: topicObj.score,
            nuances: topicObj.nuances,
            durationMin: topicObj.durationMin,
          },
        }),
      }).catch(() => {});
    } catch {}
  }
}

/**
 * Genera el paquete completo de temas organizados por nichos para videos de 10 a 40 minutos.
 * Los temas anclados (pinnedIds) se conservan intactos y no se reemplazan.
 */
export function generateDailyTopics(pinnedIds: string[], forceNewSeed: boolean = false): ViralTopic[] {
  const todayStr = new Date().toISOString().slice(0, 10);
  let savedTopics: ViralTopic[] = [];

  if (!forceNewSeed && typeof window !== "undefined") {
    try {
      const storedDate = localStorage.getItem(STORAGE_DATE_KEY);
      const rawTopics = localStorage.getItem(STORAGE_DAILY_TOPICS_KEY);
      if (storedDate === todayStr && rawTopics) {
        savedTopics = JSON.parse(rawTopics);
        const hasAllCats = ALL_CATEGORIES.every((c) =>
          savedTopics.some((t) => t.category === c),
        );
        if (savedTopics && hasAllCats && savedTopics.length >= 100) {
          return savedTopics;
        }
      }
    } catch {}
  }

  const result: ViralTopic[] = [];
  const pinnedSet = new Set(pinnedIds);

  for (const cat of ALL_CATEGORIES) {
    const catPool = VIRAL_MASTER_POOL.filter((t) => t.category === cat);

    // 1. Conservar los temas anclados de esta categoría
    const pinnedInCat: ViralTopic[] = [];
    pinnedSet.forEach((pid) => {
      const found =
        VIRAL_MASTER_POOL.find((t) => t.id === pid && t.category === cat) ||
        savedTopics.find((t) => t.id === pid && t.category === cat);
      if (found && !pinnedInCat.some((x) => x.id === found.id)) {
        pinnedInCat.push(found);
      }
    });

    // 2. Temas no anclados
    const availableUnpinned = catPool.filter((t) => !pinnedSet.has(t.id));

    // Mezcla determinista o con semilla para variar puntuaciones ligeramente en refresco
    const seed = forceNewSeed ? Date.now() : todayStr.split("-").reduce((a, b) => a + Number(b), 0);
    const shuffled = [...availableUnpinned].sort((a, b) => {
      const hashA = (a.id.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) * seed) % 100;
      const hashB = (b.id.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) * seed) % 100;
      return hashB - hashA;
    });

    // Asignar micro-variaciones a las puntuaciones en refresco (+88 a +99)
    const freshSelection = shuffled.map((t, idx) => ({
      ...t,
      score: Math.min(99, Math.max(88, t.score + (((idx * 3 + seed) % 5) - 2))),
    }));

    // Los anclados van de primero, seguidos por los temas frescos
    result.push(...pinnedInCat, ...freshSelection);
  }

  // Guardar en caché local
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(STORAGE_DATE_KEY, todayStr);
      localStorage.setItem(STORAGE_DAILY_TOPICS_KEY, JSON.stringify(result));
    } catch {}
  }

  return result;
}

// Mantener retrocompatibilidad con la firma anterior si se invoca
export const generateDaily30Topics = generateDailyTopics;

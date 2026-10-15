import { useState, useRef, useEffect } from "react";
import { ASSET_FOLDERS, PRESETS } from "@/lib/data";
import {
  generateDailyTopics,
  getStoredPinnedIds,
  savePinnedIds,
  CATEGORY_LABELS,
  ALL_CATEGORIES,
  type ViralTopic,
  type ViralCategory,
} from "@/lib/viralTopics";
import { useEditor } from "@/lib/store";
import { cn } from "@/utils/cn";
import { Hairline, IconButton, Meter, SectionLabel, Toggle } from "./ui";
import {
  IconCheck,
  IconChevron,
  IconCrop,
  IconLayers,
  IconMusic,
  IconPlus,
  IconScissors,
  IconSparkle,
  IconType,
  IconPin,
  IconRefresh,
  IconFolder,
  IconTrash,
  IconPlay,
  IconShare,
} from "./Icons";
import { ProjectDetailsModal } from "./ProjectDetailsModal";

const TABS = [
  { id: "media", label: "Proyectos", icon: IconFolder },
  { id: "ai", label: "IA", icon: IconSparkle },
  { id: "text", label: "Texto", icon: IconType },
  { id: "audio", label: "Audio", icon: IconMusic },
  { id: "fx", label: "Efectos", icon: IconCrop },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function LeftPanel() {
  const [tab, setTab] = useState<TabId>("ai");
  const { importVideo, isUploading } = useEditor();
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex min-h-0 shrink-0">
      {/* ---- rail ---- */}
      <nav className="flex w-[54px] shrink-0 flex-col items-center gap-1 border-r border-white/[0.05] bg-black/40 py-3">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              title={t.label}
              className={cn(
                "group relative grid h-10 w-10 place-items-center rounded-xl transition-all duration-300",
                active
                  ? "bg-gradient-to-b from-white/[0.13] to-white/[0.03] text-beam-200 shadow-[0_1px_0_0_rgba(255,255,255,0.12)_inset,0_8px_20px_-12px_rgba(47,92,255,1)]"
                  : "text-white/30 hover:bg-white/[0.04] hover:text-white/70",
              )}
            >
              {active && (
                <span className="absolute -left-[13px] h-5 w-[2px] rounded-full bg-beam-400 shadow-[0_0_12px_2px_rgba(47,92,255,0.9)]" />
              )}
              <Icon className="h-[18px] w-[18px]" />
              <span className="pointer-events-none absolute left-[46px] z-50 hidden whitespace-nowrap rounded-md border border-white/10 bg-ink-900/95 px-2 py-1 text-[10px] text-white/70 shadow-xl group-hover:block">
                {t.label}
              </span>
            </button>
          );
        })}
        <div className="mt-auto flex flex-col items-center gap-1">
          <div className="micro-sm rotate-180 whitespace-nowrap text-white/15 [writing-mode:vertical-rl]">
            Biblioteca
          </div>
        </div>
      </nav>

      {/* ---- panel ---- */}
      <aside className="glass-soft flex w-[268px] min-h-0 flex-col rounded-none border-y-0 border-l-0 lg:w-[286px]">
        <div className="flex items-center justify-between px-4 pb-3 pt-4">
          <div>
            <h2 className="serif-display text-[17px] leading-none text-white">
              {TABS.find((t) => t.id === tab)?.label}
            </h2>
            <p className="micro-sm mt-1.5 text-white/25">
              {tab === "ai" && "Automatización neuronal"}
              {tab === "media" && "Recientes en disco (máx. 5)"}
              {tab === "text" && "Subtítulos y titulares"}
              {tab === "audio" && "Pista y locución"}
              {tab === "fx" && "LUT, grano y reencuadre"}
            </p>
          </div>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  importVideo(file);
                  e.target.value = "";
                }
              }}
            />
            <IconButton
              size="sm"
              title={isUploading ? "Subiendo..." : "Importar video"}
              onClick={() => fileInputRef.current?.click()}
            >
              <IconPlus className={cn("h-3.5 w-3.5", isUploading && "anim-spin text-beam-300")} />
            </IconButton>
          </div>
        </div>

        <div
          className={cn(
            "min-h-0 flex-1 px-3",
            tab === "ai" ? "flex flex-col overflow-hidden pb-1" : "overflow-y-auto pb-4",
          )}
        >
          {tab === "ai" && <AITab />}
          {tab === "media" && <MediaTab />}
          {tab === "text" && <TextTab />}
          {tab === "audio" && <AudioTab />}
          {tab === "fx" && <FxTab />}
        </div>
      </aside>
    </div>
  );
}

/* ------------------------------------------------------------------ */

const NEURAL_VOICES = [
  { id: "es-MX-JorgeNeural", n: "Jorge · México", d: "Conversacional" },
  { id: "es-US-AlonsoNeural", n: "Alonso · Latino", d: "Broadcast" },
  { id: "es-CO-GonzaloNeural", n: "Gonzalo · Colombia", d: "Neutro & Calmo" },
  { id: "es-AR-TomasNeural", n: "Tomás · Argentina", d: "Directo & Enérgico" },
  { id: "es-MX-DaliaNeural", n: "Dalia · México", d: "Femenina Cálida" },
  { id: "es-AR-ElenaNeural", n: "Elena · Argentina", d: "Femenina Expresiva" },
  { id: "es-ES-AlvaroNeural", n: "Álvaro · España", d: "Tech & Divulgación" },
  { id: "clon-propio", n: "Clon de voz propio", d: "Muestra de estudio" },
];

function AITab() {
  const {
    isCreating,
    createProgress,
    createStatusMessage,
    createVideo,
    cancelCreation,
    resumeProject,
    flash,
    projects,
    activeProjectId,
    activeProjectTitle,
    selectedVoice,
    setSelectedVoice,
    previewVoice,
    playingVoiceId,
  } = useEditor();

  const [topicPrompt, setTopicPrompt] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<ViralCategory | "all">("all");
  const [videoFormat, setVideoFormat] = useState<"long" | "reel">("long");
  const [targetDurationMin, setTargetDurationMin] = useState<number>(15);
  const [targetReelSec, setTargetReelSec] = useState<number>(60);
  const [isExtractingClips, setIsExtractingClips] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [pinnedIds, setPinnedIds] = useState<string[]>(() => getStoredPinnedIds());
  const [topics, setTopics] = useState<ViralTopic[]>(() =>
    generateDailyTopics(getStoredPinnedIds()),
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (topicPrompt.trim() && !isCreating) {
        const text = topicPrompt.trim();
        setTopicPrompt("");
        if (videoFormat === "reel") {
          createVideo(text, {
            duration: targetReelSec,
            style: "shorts",
            aspect_ratio: "9:16",
          });
        } else {
          createVideo(text, {
            duration: targetDurationMin * 60,
            style: "divulgacion",
            aspect_ratio: "16:9",
          });
        }
      }
    }
  };

  const [isRefreshingTopics, setIsRefreshingTopics] = useState(false);

  const handleRefresh = async () => {
    if (isRefreshingTopics) return;
    setIsRefreshingTopics(true);
    flash("Buscando tendencias reales en Internet con IA...");
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 7500);
    try {
      const res = await fetch("/api/viral-niches/refresh", {
        method: "POST",
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        if (data.topics && Array.isArray(data.topics) && data.topics.length > 0) {
          const liveTopics: ViralTopic[] = data.topics;
          const existingFiltered = topics.filter(
            (t) => !liveTopics.some((lt) => lt.category === t.category && lt.title.toLowerCase() === t.title.toLowerCase()),
          );
          const combined = [...liveTopics, ...existingFiltered];

          const pinnedSet = new Set(pinnedIds);
          const pinned = combined.filter((t) => pinnedSet.has(t.id));
          const unpinned = combined.filter((t) => !pinnedSet.has(t.id));
          const finalTopics = [...pinned, ...unpinned];

          setTopics(finalTopics);
          try {
            localStorage.setItem("aethercut_daily_topics", JSON.stringify(finalTopics));
          } catch (_) {}
          flash("✓ ¡Tendencias de Internet actualizadas con IA y puntuación real!");
          return;
        }
      }
    } catch (e) {
      console.warn("Fallo en búsqueda en vivo de temas:", e);
    } finally {
      clearTimeout(timeoutId);
      setIsRefreshingTopics(false);
    }

    const fresh = generateDailyTopics(pinnedIds, true);
    setTopics(fresh);
    flash("Temas actualizados con nuevas puntuaciones · Favoritos intactos");
  };

  const togglePin = (topic: ViralTopic) => {
    const isPinned = pinnedIds.includes(topic.id);
    const nextPinned = isPinned
      ? pinnedIds.filter((id) => id !== topic.id)
      : [topic.id, ...pinnedIds];

    setPinnedIds(nextPinned);
    savePinnedIds(nextPinned, topic, !isPinned);
    flash(
      isPinned
        ? `«${topic.title.slice(0, 24)}...» desanclado`
        : `«${topic.title.slice(0, 24)}...» anclado de primero`,
    );
  };

  const handleIntegrate = (topic: ViralTopic) => {
    const combined = `${topic.title}. ${topic.nuances}`;
    setTopicPrompt(combined);
    if (videoFormat === "long") {
      setTargetDurationMin(topic.durationMin || 15);
    }
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
    flash(`Tema integrado: «${topic.title.slice(0, 25)}...»`);
  };

  const handleGenerate = (
    topic: ViralTopic,
    format: "long" | "reel" = videoFormat,
    overrideDurationSec?: number,
  ) => {
    if (isCreating) return;
    const combined = `${topic.title}. ${topic.nuances}`;
    if (format === "reel") {
      const dur = overrideDurationSec || targetReelSec;
      createVideo(combined, {
        duration: dur,
        style: "shorts",
        aspect_ratio: "9:16",
      });
      flash(`Generando Reel 9:16 (${dur}s): «${topic.title.slice(0, 24)}...»`);
    } else {
      const dur = overrideDurationSec || targetDurationMin * 60;
      const minLabel = Math.round(dur / 60);
      createVideo(combined, {
        duration: dur,
        style: "divulgacion",
        aspect_ratio: "16:9",
      });
      flash(`Generando video documental 16:9 (${minLabel}m): «${topic.title.slice(0, 24)}...»`);
    }
  };

  const handleExtractMasterClips = async () => {
    if (!activeProjectId || isExtractingClips) return;
    try {
      setIsExtractingClips(true);
      flash("Extrayendo 3 Reels verticales 9:16 de los mejores momentos del video...");
      const res = await fetch(`/api/projects/${activeProjectId}/extract-clips`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error al extraer clips");
      flash("¡3 Reels verticales 9:16 listos y extraídos con éxito!");
    } catch (err: any) {
      flash(`Aviso: ${err.message || "No se pudieron extraer clips"}`);
    } finally {
      setIsExtractingClips(false);
    }
  };

  // Grupos activos según el filtro seleccionado
  const activeCategories: ViralCategory[] =
    selectedCategory === "all" ? ALL_CATEGORIES : [selectedCategory];

  // Temas filtrados
  const displayedTopics =
    selectedCategory === "all"
      ? topics
      : topics.filter((t) => t.category === selectedCategory);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* 1. SECCIÓN ESTÁTICA / FIJA (Card de prompt, formato, duración y pipeline) */}
      <div className="shrink-0 rounded-xl border border-white/[0.06] bg-gradient-to-b from-white/[0.04] to-transparent p-3 mb-2">
        {/* Cabecera del generador con Switcher de formato Largo vs Reel */}
        <div className="flex items-center justify-between gap-1 pb-1.5 border-b border-white/[0.04]">
          <div className="flex items-center gap-0.5 bg-black/50 p-0.5 rounded-lg border border-white/[0.08]">
            <button
              type="button"
              onClick={() => setVideoFormat("long")}
              className={cn(
                "px-2 py-0.5 rounded text-[8.5px] font-semibold flex items-center gap-1 transition-all",
                videoFormat === "long"
                  ? "bg-beam-500/25 text-beam-100 border border-beam-400/35 shadow-[0_0_8px_rgba(56,189,248,0.2)]"
                  : "text-white/40 hover:text-white/70",
              )}
              title="Modo Largo / Documental: 10 a 40 minutos en formato panorámico 16:9"
            >
              <span>🎬</span>
              <span>Largo 16:9</span>
            </button>
            <button
              type="button"
              onClick={() => setVideoFormat("reel")}
              className={cn(
                "px-2 py-0.5 rounded text-[8.5px] font-semibold flex items-center gap-1 transition-all",
                videoFormat === "reel"
                  ? "bg-purple-500/25 text-purple-100 border border-purple-400/35 shadow-[0_0_8px_rgba(168,85,247,0.2)]"
                  : "text-white/40 hover:text-white/70",
              )}
              title="Modo Reel / Short: 30 a 90 segundos en formato vertical 9:16 con gancho viral"
            >
              <span>📱</span>
              <span>Reel 9:16</span>
            </button>
          </div>

          {/* Control editable de tiempo con signos - y + para elegir libremente o hacer pruebas cortas */}
          <div className="flex items-center bg-black/60 rounded-lg border border-white/[0.08] px-1 py-0.5 shadow-inner">
            <button
              type="button"
              onClick={() => {
                if (videoFormat === "long") {
                  setTargetDurationMin((prev) => Math.max(1, prev - 1));
                } else {
                  setTargetReelSec((prev) => Math.max(10, prev - 5));
                }
              }}
              className="h-5 w-5 grid place-items-center rounded text-[13px] font-bold text-white/50 hover:text-white hover:bg-white/[0.08] active:scale-90 transition-all select-none"
              title={videoFormat === "long" ? "Restar 1 minuto" : "Restar 5 segundos"}
            >
              −
            </button>

            <div className="flex items-center gap-0.5 px-1">
              {videoFormat === "long" ? (
                <>
                  <input
                    type="number"
                    min={1}
                    max={60}
                    value={targetDurationMin || ""}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      if (!isNaN(val)) {
                        setTargetDurationMin(Math.max(1, Math.min(60, val)));
                      } else if (e.target.value === "") {
                        setTargetDurationMin(1);
                      }
                    }}
                    className="w-6 text-center bg-transparent border-0 p-0 text-[11px] font-bold text-beam-200 focus:outline-none focus:ring-0 tnum [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    title="Escribe directamente los minutos (ej: 1 o 2 para pruebas cortas, o 10 a 40 para documental)"
                  />
                  <span className="text-[9px] font-medium text-white/40 select-none">m</span>
                </>
              ) : (
                <>
                  <input
                    type="number"
                    min={10}
                    max={300}
                    value={targetReelSec || ""}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      if (!isNaN(val)) {
                        setTargetReelSec(Math.max(5, Math.min(300, val)));
                      } else if (e.target.value === "") {
                        setTargetReelSec(15);
                      }
                    }}
                    className="w-7 text-center bg-transparent border-0 p-0 text-[11px] font-bold text-purple-300 focus:outline-none focus:ring-0 tnum [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                    title="Escribe directamente los segundos (ej: 15, 30, 45, 60, 90)"
                  />
                  <span className="text-[9px] font-medium text-white/40 select-none">s</span>
                </>
              )}
            </div>

            <button
              type="button"
              onClick={() => {
                if (videoFormat === "long") {
                  setTargetDurationMin((prev) => Math.min(60, prev + 1));
                } else {
                  setTargetReelSec((prev) => Math.min(300, prev + 5));
                }
              }}
              className="h-5 w-5 grid place-items-center rounded text-[13px] font-bold text-white/50 hover:text-white hover:bg-white/[0.08] active:scale-90 transition-all select-none"
              title={videoFormat === "long" ? "Sumar 1 minuto" : "Sumar 5 segundos"}
            >
              +
            </button>
          </div>
        </div>

        {/* Selector y verificador rápido de voz neuronal */}
        <div className="mt-2 flex items-center justify-between bg-black/40 rounded-lg px-2 py-1 border border-white/[0.05]">
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            <span className="text-[10px] select-none shrink-0">🎙️</span>
            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              className="w-full bg-transparent border-0 p-0 text-[9.5px] font-medium text-white/80 focus:outline-none focus:ring-0 truncate cursor-pointer"
              title="Voz neuronal exacta que narrará tus videos"
            >
              {NEURAL_VOICES.map((v) => (
                <option key={v.id} value={v.id} className="bg-night-950 text-white">
                  {v.n} ({v.d})
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={() => previewVoice(selectedVoice)}
            className="shrink-0 text-[9px] text-beam-300/80 hover:text-beam-200 transition-colors pl-1.5 font-medium"
            title="Escuchar muestra de esta voz neuronal"
          >
            {playingVoiceId === selectedVoice ? "🔊 Probando..." : "▶ Muestra"}
          </button>
        </div>

        <div className="mt-2">
          <Meter value={isCreating ? createProgress : 100} />
        </div>
        {isCreating ? (
          <div className="mt-2 flex items-center justify-between gap-1.5">
            <p className="text-[10px] leading-relaxed text-beam-200/90 truncate flex-1" title={createStatusMessage}>
              {createStatusMessage || "Procesando video con IA..."}
            </p>
            <button
              type="button"
              onClick={cancelCreation}
              className="shrink-0 text-[9px] font-medium text-red-300 hover:text-red-100 bg-red-500/15 hover:bg-red-500/30 border border-red-500/30 px-1.5 py-0.5 rounded transition-all"
              title="Cancelar creación activa"
            >
              Cancelar
            </button>
          </div>
        ) : (
          <textarea
            ref={textareaRef}
            value={topicPrompt}
            onChange={(e) => setTopicPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            placeholder={
              videoFormat === "reel"
                ? "Escribe el tema para tu Reel / Short vertical 9:16 (30-90s) con gancho dinámico..."
                : "Escribe el tema o integra uno de los nichos abajo para crear tu video de 10 a 40 min..."
            }
            className="mt-2 w-full resize-none border-0 bg-transparent p-0 text-[10px] leading-relaxed text-white/85 placeholder:text-white/35 focus:outline-none focus:ring-0"
          />
        )}
        {topicPrompt.trim().length > 0 && !isCreating && (
          <div className="mt-1 flex items-center justify-between">
            <span className="text-[9px] text-white/30">
              {videoFormat === "reel" ? (
                <>
                  Formato: <strong className="text-purple-300 font-semibold">Reel 9:16 ({targetReelSec}s)</strong>
                </>
              ) : (
                <>
                  Duración: <strong className="text-beam-300 font-semibold">{targetDurationMin} min (16:9)</strong>
                </>
              )}
            </span>
            <button
              type="button"
              onClick={() => {
                const text = topicPrompt.trim();
                setTopicPrompt("");
                if (videoFormat === "reel") {
                  createVideo(text, {
                    duration: targetReelSec,
                    style: "shorts",
                    aspect_ratio: "9:16",
                  });
                } else {
                  createVideo(text, {
                    duration: targetDurationMin * 60,
                    style: "divulgacion",
                    aspect_ratio: "16:9",
                  });
                }
              }}
              className={cn(
                "micro-sm transition-colors font-medium",
                videoFormat === "reel"
                  ? "text-purple-300 hover:text-purple-100"
                  : "text-beam-300 hover:text-beam-100",
              )}
            >
              {videoFormat === "reel"
                ? `Crear Reel (${targetReelSec}s) ↵`
                : `Crear video (${targetDurationMin}m) ↵`}
            </button>
          </div>
        )}

        {/* Acceso rápido a extraer 3 Reels verticales si hay video activo en el editor */}
        {activeProjectId && (
          <div className="mt-2 pt-2 border-t border-white/[0.05] flex items-center justify-between">
            <span className="text-[9px] text-white/30 truncate max-w-[120px]" title={activeProjectTitle}>
              En timeline: {activeProjectTitle || "Video activo"}
            </span>
            <div className="flex items-center gap-1.5">
              {(() => {
                const activeProj = projects?.find((p) => p.id === activeProjectId);
                const isInterrupted =
                  Boolean(activeProjectId) &&
                  !isCreating &&
                  Boolean(
                    activeProj &&
                      !activeProj.has_result &&
                      (activeProj.status === "render" ||
                        activeProj.status === "running" ||
                        activeProj.status === "script" ||
                        activeProj.status === "error"),
                  );
                return (
                  isInterrupted && (
                    <button
                      type="button"
                      onClick={() => resumeProject(activeProjectId)}
                      className="text-[9px] font-medium px-2 py-0.5 rounded-md border border-amber-400/40 bg-amber-500/15 text-amber-200 hover:bg-amber-500/30 transition-all flex items-center gap-1"
                      title="Reanudar generación de este video desde donde se detuvo"
                    >
                      <span>⚡</span>
                      <span>Reanudar</span>
                    </button>
                  )
                );
              })()}
              <button
                type="button"
                onClick={handleExtractMasterClips}
                disabled={isExtractingClips}
                className={cn(
                  "text-[9px] font-medium px-2 py-0.5 rounded-md border transition-all flex items-center gap-1",
                  isExtractingClips
                    ? "border-white/10 bg-white/5 text-white/40 cursor-not-allowed"
                    : "border-purple-400/30 bg-purple-500/15 text-purple-200 hover:bg-purple-500/25 hover:border-purple-400/50",
                )}
                title="Extrae automáticamente 3 clips verticales (Shorts / Reels 9:16) a partir de los mejores momentos"
              >
                <span>✂️</span>
                <span>{isExtractingClips ? "Extrayendo..." : "Extraer 3 Reels"}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 2. BARRA DE CABECERA CON CONTADOR Y BOTÓN ACTUALIZAR */}
      <div className="shrink-0 flex items-center justify-between px-1 mb-1">
        <div className="flex items-center gap-1.5">
          <span className="micro-sm text-white/35 font-medium tracking-wider">
            NICHOS VIRALES
          </span>
          <span className="rounded-full bg-beam-500/10 border border-beam-400/20 px-1.5 py-0.2 text-[9px] font-semibold text-beam-300">
            {displayedTopics.length} disponibles
          </span>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={isRefreshingTopics}
          title="Buscar tendencias reales en Internet con IA y recalcular puntuaciones virales"
          className="flex items-center gap-1 text-[9.5px] text-white/40 hover:text-beam-300 transition-colors px-1.5 py-0.5 rounded hover:bg-white/[0.04] disabled:opacity-50"
        >
          <IconRefresh className={cn("h-3 w-3", isRefreshingTopics && "animate-spin text-beam-300")} />
          <span>{isRefreshingTopics ? "Buscando en web..." : "Actualizar"}</span>
        </button>
      </div>

      {/* 3. BOTÓN DE FILTRADO HORIZONTAL RÁPIDO POR NICHO */}
      <div
        onWheel={(e) => {
          if (e.deltaY !== 0) {
            e.currentTarget.scrollLeft += e.deltaY;
          }
        }}
        className="shrink-0 flex items-center gap-1 overflow-x-auto no-scrollbar py-1 px-0.5 mb-1.5 scroll-smooth"
      >
        <button
          type="button"
          onClick={() => setSelectedCategory("all")}
          className={cn(
            "shrink-0 flex items-center gap-1 px-2 py-1 rounded-lg text-[9.5px] border transition-all duration-200",
            selectedCategory === "all"
              ? "bg-beam-500/20 border-beam-400/40 text-beam-100 font-medium shadow-[0_0_8px_rgba(56,189,248,0.15)]"
              : "bg-white/[0.025] border-white/[0.06] text-white/45 hover:text-white/80 hover:bg-white/[0.05]",
          )}
        >
          <span>Todos</span>
          <span className="text-[8.5px] opacity-60">({topics.length})</span>
        </button>
        {ALL_CATEGORIES.map((catKey) => {
          const catInfo = CATEGORY_LABELS[catKey];
          const count = topics.filter((t) => t.category === catKey).length;
          const isActive = selectedCategory === catKey;
          return (
            <button
              key={catKey}
              type="button"
              onClick={() => setSelectedCategory(catKey)}
              title={catInfo.desc}
              className={cn(
                "shrink-0 flex items-center gap-1 px-2 py-1 rounded-lg text-[9.5px] border transition-all duration-200",
                isActive
                  ? "bg-beam-500/20 border-beam-400/40 text-beam-100 font-medium shadow-[0_0_8px_rgba(56,189,248,0.15)]"
                  : "bg-white/[0.025] border-white/[0.06] text-white/45 hover:text-white/80 hover:bg-white/[0.05]",
              )}
            >
              <span>{catInfo.icon}</span>
              <span>{catInfo.label}</span>
              <span className="text-[8.5px] opacity-60">({count})</span>
            </button>
          );
        })}
      </div>

      {/* 4. LISTA SCROLLABLE DE TEMAS CON EFECTO DE DESAPARICIÓN */}
      <div
        className="min-h-0 flex-1 overflow-y-auto space-y-4 pr-1 pb-4 pt-1"
        style={{
          WebkitMaskImage:
            "linear-gradient(to bottom, transparent 0px, black 16px, black calc(100% - 16px), transparent 100%)",
          maskImage:
            "linear-gradient(to bottom, transparent 0px, black 16px, black calc(100% - 16px), transparent 100%)",
        }}
      >
        {activeCategories.map((g) => {
          const items = topics.filter((a) => a.category === g);
          if (!items.length) return null;

          // Ordenar: temas anclados/favoritos van DE PRIMERO en su categoría
          const sortedItems = [...items].sort((a, b) => {
            const aPinned = pinnedIds.includes(a.id);
            const bPinned = pinnedIds.includes(b.id);
            if (aPinned && !bPinned) return -1;
            if (!aPinned && bPinned) return 1;
            return b.score - a.score;
          });

          const catInfo = CATEGORY_LABELS[g];

          return (
            <div key={g} className="space-y-2">
              <div className="flex items-center justify-between">
                <SectionLabel>
                  <span className="flex items-center gap-1.5">
                    <span>{catInfo.icon}</span>
                    <span>{catInfo.label}</span>
                  </span>
                </SectionLabel>
                <span className="text-[9px] text-white/20">
                  {sortedItems.length} temas
                </span>
              </div>
              {sortedItems.map((topic) => {
                const isPinned = pinnedIds.includes(topic.id);
                return (
                  <div
                    key={topic.id}
                    className={cn(
                      "group relative overflow-hidden rounded-xl border p-2.5 transition-all duration-300",
                      isPinned
                        ? "border-amber-400/25 bg-amber-400/[0.035] shadow-[0_0_12px_rgba(251,191,36,0.06)]"
                        : "border-white/[0.06] bg-white/[0.015] hover:border-white/[0.14] hover:bg-white/[0.035]",
                    )}
                  >
                    {isPinned && (
                      <span className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-amber-400/40 via-amber-300/80 to-amber-400/40" />
                    )}
                    <div className="flex items-start gap-2.5">
                      {/* Glyph / Icono del nicho */}
                      <span
                        className={cn(
                          "mt-[1px] grid h-6 w-6 shrink-0 place-items-center rounded-lg border text-[11px]",
                          isPinned
                            ? "border-amber-400/35 bg-amber-400/10 text-amber-300"
                            : "border-beam-400/25 bg-beam-500/10 text-beam-200",
                        )}
                      >
                        {topic.glyph || catInfo.icon}
                      </span>

                      <div className="min-w-0 flex-1">
                        {/* Título + duración + score de viralidad + botoncito de favoritos */}
                        <div className="flex items-start justify-between gap-1.5">
                          <h4 className="text-[11.5px] font-medium leading-snug text-white/90 line-clamp-2">
                            {topic.title}
                          </h4>
                          <div className="flex items-center gap-1 shrink-0 pt-0.5">
                            {/* Badge de duración sugerida (10-40 min) */}
                            <span
                              className="text-[8.5px] font-medium text-white/45 bg-white/[0.04] px-1 py-0.5 rounded border border-white/[0.06]"
                              title={`Duración sugerida: ${topic.durationMin} minutos`}
                            >
                              ⏱ {topic.durationMin}m
                            </span>
                            {/* Score de viralidad */}
                            <span
                              className="tnum text-[9.5px] font-semibold text-beam-200/90 bg-beam-500/10 px-1 py-0.5 rounded border border-beam-400/20"
                              title="Puntuación de potencial viral estimado"
                            >
                              +{topic.score}
                            </span>
                            {/* Botoncito pequeño sutil de guardar en favoritos / anclar */}
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                togglePin(topic);
                              }}
                              title={
                                isPinned
                                  ? "Anclado de primero en favoritos · Clic para desanclar"
                                  : "Guardar en favoritos y anclar de primero en esta categoría"
                              }
                              className={cn(
                                "p-1 rounded-md transition-all duration-200",
                                isPinned
                                  ? "text-amber-400 bg-amber-400/15 border border-amber-400/35 shadow-[0_0_8px_rgba(251,191,36,0.25)]"
                                  : "text-white/20 hover:text-amber-300/80 hover:bg-white/[0.06]",
                              )}
                            >
                              <IconPin
                                className={cn(
                                  "h-3 w-3 transition-transform",
                                  isPinned ? "rotate-[-45deg] scale-110" : "opacity-60",
                                )}
                                filled={isPinned}
                              />
                            </button>
                          </div>
                        </div>

                        {/* Matices o descripción para crear sobre eso */}
                        <p className="mt-1 text-[10px] leading-snug text-white/40 line-clamp-2">
                          {topic.nuances}
                        </p>

                        {/* Botones Integrar, Generar Largo y Generar Reel */}
                        <div className="mt-2.5 flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleIntegrate(topic)}
                            className="flex-1 rounded-lg border border-white/10 bg-white/[0.025] py-[4.5px] text-[10px] font-medium text-white/70 hover:border-white/20 hover:bg-white/[0.06] hover:text-white transition-all text-center"
                            title="Copiar título y matices en la card de edición superior"
                          >
                            Integrar
                          </button>
                          {videoFormat === "long" ? (
                            <>
                              <button
                                type="button"
                                onClick={() => handleGenerate(topic, "long", (topic.durationMin || targetDurationMin) * 60)}
                                disabled={isCreating}
                                className={cn(
                                  "flex-[1.2] rounded-lg border py-[4.5px] text-[10px] font-medium transition-all text-center truncate px-1",
                                  isCreating
                                    ? "opacity-50 cursor-not-allowed border-white/10 text-white/40"
                                    : "border-beam-400/30 bg-beam-500/15 text-beam-200 hover:border-beam-300/50 hover:bg-beam-500/25 hover:text-white",
                                )}
                                title={`Generar video documental de ${topic.durationMin || targetDurationMin} min con IA en 16:9`}
                              >
                                Generar ({topic.durationMin || targetDurationMin}m)
                              </button>
                              <button
                                type="button"
                                onClick={() => handleGenerate(topic, "reel")}
                                disabled={isCreating}
                                className={cn(
                                  "shrink-0 rounded-lg border py-[4.5px] px-2 text-[10px] font-medium transition-all text-center",
                                  isCreating
                                    ? "opacity-50 cursor-not-allowed border-white/10 text-white/40"
                                    : "border-purple-400/30 bg-purple-500/15 text-purple-200 hover:border-purple-300/50 hover:bg-purple-500/25 hover:text-white",
                                )}
                                title={`Generar versión Reel vertical 9:16 (${targetReelSec}s) con gancho dinámico instantáneo`}
                              >
                                📱 Reel ({targetReelSec}s)
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                type="button"
                                onClick={() => handleGenerate(topic, "reel")}
                                disabled={isCreating}
                                className={cn(
                                  "flex-[1.2] rounded-lg border py-[4.5px] text-[10px] font-medium transition-all text-center truncate px-1",
                                  isCreating
                                    ? "opacity-50 cursor-not-allowed border-white/10 text-white/40"
                                    : "border-purple-400/30 bg-purple-500/15 text-purple-200 hover:border-purple-300/50 hover:bg-purple-500/25 hover:text-white",
                                )}
                                title={`Generar Reel vertical 9:16 de ${targetReelSec}s con gancho viral`}
                              >
                                📱 Reel ({targetReelSec}s)
                              </button>
                              <button
                                type="button"
                                onClick={() => handleGenerate(topic, "long", (topic.durationMin || 15) * 60)}
                                disabled={isCreating}
                                className={cn(
                                  "shrink-0 rounded-lg border py-[4.5px] px-2 text-[10px] font-medium transition-all text-center",
                                  isCreating
                                    ? "opacity-50 cursor-not-allowed border-white/10 text-white/40"
                                    : "border-beam-400/30 bg-beam-500/15 text-beam-200 hover:border-beam-300/50 hover:bg-beam-500/25 hover:text-white",
                                )}
                                title={`Generar video documental largo de ${topic.durationMin} min en 16:9`}
                              >
                                🎬 {topic.durationMin}m
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MediaTab() {
  const { seek, clips, projects, activeProjectId, selectProject, deleteProject } = useEditor();
  const [detailsProject, setDetailsProject] = useState<any | null>(null);
  const realScenes = clips.filter((c) => c.kind === "scene");
  const recentProjects = (projects || []).slice(0, 20);

  return (
    <div className="space-y-4">
      {/* 1. PROYECTOS RECIENTES EN DISCO (MÁXIMO 20) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-0.5">
          <SectionLabel
            right={
              <span className="rounded-full bg-beam-500/10 border border-beam-400/20 px-1.5 py-0.2 text-[9px] font-semibold text-beam-300 font-mono">
                {recentProjects.length}/20 en disco
              </span>
            }
          >
            Proyectos Recientes
          </SectionLabel>
        </div>

        {recentProjects.length === 0 ? (
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.015] p-4 text-center">
            <IconFolder className="mx-auto h-6 w-6 text-white/20 mb-1.5" />
            <p className="text-[11px] text-white/50">No hay proyectos recientes</p>
            <p className="text-[9.5px] text-white/25 mt-0.5">Genera uno desde la pestaña IA</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {recentProjects.map((p) => {
              const isActive = p.id === activeProjectId;
              const title = p.name || p.topic || `Proyecto ${p.id}`;
              const durSec = p.duration ? Math.round(p.duration) : null;
              const durStr = durSec
                ? durSec >= 60
                  ? `${Math.floor(durSec / 60)}m ${durSec % 60}s`
                  : `${durSec}s`
                : null;

              return (
                <div
                  key={p.id}
                  onClick={() => selectProject(p.id)}
                  className={cn(
                    "group relative flex w-full items-center gap-2.5 rounded-xl border p-2 text-left transition-all duration-200 cursor-pointer",
                    isActive
                      ? "border-beam-400/50 bg-beam-500/15 shadow-[0_0_15px_-3px_rgba(79,123,255,0.3)] ring-1 ring-beam-400/30"
                      : "border-white/[0.06] bg-white/[0.015] hover:border-white/[0.15] hover:bg-white/[0.04]",
                  )}
                >
                  {/* Thumbnail / Frame */}
                  <div className="relative h-12 w-[34px] shrink-0 overflow-hidden rounded-md border border-white/10 bg-black/50">
                    {p.thumbnail_url ? (
                      <img
                        src={p.thumbnail_url}
                        alt=""
                        className="no-drag h-full w-full object-cover opacity-85 transition-opacity group-hover:opacity-100"
                      />
                    ) : (
                      <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-beam-900/40 via-ink-900 to-black text-beam-300/40">
                        <IconPlay className="h-3.5 w-3.5" />
                      </div>
                    )}
                    {isActive && (
                      <div className="absolute inset-x-0 bottom-0 h-1 bg-beam-400" />
                    )}
                  </div>

                  {/* Info */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={cn(
                          "truncate text-[11px] font-medium leading-tight",
                          isActive ? "text-white" : "text-white/80 group-hover:text-white",
                        )}
                        title={title}
                      >
                        {title}
                      </span>
                    </div>

                    <div className="mt-1 flex items-center gap-2 text-[9.5px]">
                      {durStr && (
                        <span className="font-mono text-white/50 bg-white/[0.04] px-1 py-0.2 rounded border border-white/[0.04]">
                          ⏱ {durStr}
                        </span>
                      )}
                      <span
                        className={cn(
                          "flex items-center gap-1",
                          p.has_result ? "text-emerald-400/90" : "text-amber-400/90",
                        )}
                      >
                        <span
                          className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            p.has_result ? "bg-emerald-400" : "bg-amber-400",
                          )}
                        />
                        {p.has_result ? "Listo" : p.status || "En proceso"}
                      </span>
                      {isActive && (
                        <span className="text-beam-300 font-semibold text-[8.5px] uppercase tracking-wider ml-auto">
                          Activo
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Acciones: botón info/copiar y botón eliminar */}
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDetailsProject(p);
                      }}
                      className="p-1.5 rounded-lg text-white/40 hover:text-beam-300 hover:bg-beam-500/15 transition-all"
                      title="Ver y copiar título, descripción y hashtags para redes"
                    >
                      <IconShare className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`¿Eliminar «${title.slice(0, 30)}...» de disco?`)) {
                          deleteProject(p.id);
                        }
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-white/30 hover:text-red-400 hover:bg-red-500/10 transition-all"
                      title="Eliminar proyecto de disco y liberar espacio"
                    >
                      <IconTrash className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal de detalles de publicación */}
      <ProjectDetailsModal
        isOpen={Boolean(detailsProject)}
        onClose={() => setDetailsProject(null)}
        projectId={detailsProject?.id || null}
        projectTitle={detailsProject?.name || detailsProject?.topic || "Video KAI"}
        thumbnailUrl={detailsProject?.thumbnail_url}
        durationSec={detailsProject?.duration}
      />

      {/* 2. ESCENAS DEL PROYECTO ACTIVO */}
      {realScenes.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-white/[0.06]">
          <SectionLabel
            right={<span className="tnum text-[9px] text-white/25">{realScenes.length}</span>}
          >
            Escenas del Proyecto Activo
          </SectionLabel>
          <div className="space-y-1.5">
            {realScenes.map((sc) => (
              <button
                key={sc.id}
                onClick={() => seek(sc.start)}
                className="group flex w-full items-center gap-2.5 rounded-xl border border-white/[0.05] bg-white/[0.012] p-2 text-left transition-all duration-200 hover:border-beam-300/25 hover:bg-white/[0.04]"
              >
                <div className="relative h-11 w-[30px] shrink-0 overflow-hidden rounded-md border border-white/10 bg-black/40">
                  {sc.frame ? (
                    <img
                      src={sc.frame}
                      alt=""
                      className="no-drag h-full w-full object-cover opacity-80 transition-opacity group-hover:opacity-100"
                    />
                  ) : (
                    <div className="h-full w-full bg-gradient-to-br from-abyss-700 to-ink-900" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[11px] text-white/80 group-hover:text-white">
                    {sc.label}
                  </div>
                  <div className="micro-sm mt-1 text-white/30">
                    {Math.round(sc.start)}s · {Math.round(sc.duration)}s dur
                  </div>
                </div>
                <IconChevron className="h-3 w-3 shrink-0 text-white/15 transition-transform group-hover:translate-x-0.5 group-hover:text-white/40" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TextTab() {
  const {
    overlays,
    toggleOverlay,
    subtitleStyle,
    setSubtitleStyle,
    subtitleFont,
    setSubtitleFont,
    captions,
    updateCaption,
    seek,
  } = useEditor();

  const styles = [
    { id: "kinetic", name: "Kinetic Bold", detail: "Palabra activa resaltada" },
    { id: "karaoke", name: "Karaoke Flow", detail: "Relleno progresivo" },
    { id: "minimal", name: "Minimal Line", detail: "Banda inferior fina" },
    { id: "outline", name: "Outline Pop", detail: "Contorno + sombra" },
  ];

  const fonts = ["Inter Tight", "Instrument", "Neue Haas", "Söhne Mono"];

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <SectionLabel>Estilo de subtítulo</SectionLabel>
        {styles.map((s) => {
          const isActive = subtitleStyle === s.id;
          return (
            <button
              key={s.id}
              onClick={() => setSubtitleStyle(s.id)}
              className={cn(
                "flex w-full items-center justify-between rounded-xl border p-2.5 text-left transition-all duration-300",
                isActive
                  ? "border-beam-400/40 bg-beam-500/[0.12] shadow-[0_0_15px_-3px_rgba(79,123,255,0.3)]"
                  : "border-white/[0.06] bg-white/[0.015] hover:border-white/[0.14]",
              )}
            >
              <span>
                <span className="block text-[11.5px] font-medium text-white/90">{s.name}</span>
                <span className="micro-sm mt-0.5 block text-white/35">{s.detail}</span>
              </span>
              <span
                className={cn(
                  "h-2 w-2 rounded-full transition-all duration-300",
                  isActive ? "bg-beam-300 shadow-[0_0_10px_2px_rgba(126,163,255,0.8)] scale-110" : "bg-white/15",
                )}
              />
            </button>
          );
        })}
      </div>

      <Hairline />

      <div className="space-y-1.5">
        <SectionLabel>Superposición</SectionLabel>
        <Toggle
          on={overlays.captions}
          onChange={() => toggleOverlay("captions")}
          label="Subtítulos"
          hint={`${captions.length} frases sincronizadas`}
        />
        <Toggle
          on={overlays.tracking}
          onChange={() => toggleOverlay("tracking")}
          label="Caja de seguimiento"
          hint="Rostro principal"
        />
        <Toggle
          on={overlays.safe}
          onChange={() => toggleOverlay("safe")}
          label="Zonas seguras"
          hint="UI de plataforma"
        />
      </div>

      <Hairline />

      <div className="space-y-2">
        <SectionLabel>Tipografía</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          {fonts.map((f) => {
            const isActive = subtitleFont === f;
            return (
              <button
                key={f}
                onClick={() => setSubtitleFont(f)}
                className={cn(
                  "rounded-lg border px-2.5 py-2 text-left text-[10.5px] font-medium transition-all duration-200",
                  isActive
                    ? "border-beam-400/40 bg-beam-500/[0.12] text-white shadow-[0_0_12px_-2px_rgba(79,123,255,0.4)]"
                    : "border-white/[0.06] text-white/50 hover:border-white/15 hover:text-white/80",
                )}
              >
                {f}
              </button>
            );
          })}
        </div>
      </div>

      {captions.length > 0 && (
        <>
          <Hairline />
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <SectionLabel>Líneas de subtítulo ({captions.length})</SectionLabel>
              <span className="text-[9px] text-white/30">Clic para saltar</span>
            </div>
            <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1 text-left">
              {captions.map((c, idx) => (
                <div
                  key={idx}
                  onClick={() => seek(c.start)}
                  className="group flex flex-col gap-1 rounded-lg border border-white/[0.05] bg-white/[0.02] p-2 transition-colors hover:border-beam-400/30 hover:bg-white/[0.04] cursor-pointer"
                >
                  <div className="flex items-center justify-between text-[9px] text-beam-300/70">
                    <span className="font-mono">{c.start.toFixed(1)}s → {c.end.toFixed(1)}s</span>
                    <span className="text-white/20 group-hover:text-white/50 text-[8px]">Editar</span>
                  </div>
                  <input
                    type="text"
                    value={c.text}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => updateCaption(idx, e.target.value)}
                    className="w-full bg-transparent text-[10.5px] text-white/85 outline-none focus:border-b focus:border-beam-400 focus:text-white"
                  />
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function AudioTab() {
  const { selectedVoice, setSelectedVoice, playingVoiceId, previewVoice, flash } = useEditor();
  const [speechifyCredits, setSpeechifyCredits] = useState<boolean>(true);

  useEffect(() => {
    fetch("/api/speechify/status")
      .then((r) => r.json())
      .then((d) => {
        if (typeof d.has_credits === "boolean") {
          setSpeechifyCredits(d.has_credits);
        }
      })
      .catch(() => {});
  }, []);

  const bars = [0.4, 0.75, 0.55, 0.9, 0.35, 0.65, 1, 0.5, 0.8, 0.45, 0.7, 0.3, 0.6, 0.95, 0.4, 0.68];

  const voices = [
    // --- Voces VoiceStudio (Español) ---
    { id: "es-MX-JorgeNeural", n: "Jorge · México", d: "Conversacional & Dinámico · 1.0×", provider: "voicestudio" },
    { id: "es-US-AlonsoNeural", n: "Alonso · Latino", d: "Broadcast Internacional · 1.0×", provider: "voicestudio" },
    { id: "es-CO-GonzaloNeural", n: "Gonzalo · Colombia", d: "Neutro & Calmo · 0.95×", provider: "voicestudio" },
    { id: "es-AR-TomasNeural", n: "Tomás · Argentina", d: "Directo & Enérgico · 1.0×", provider: "voicestudio" },
    { id: "es-MX-DaliaNeural", n: "Dalia · México", d: "Femenina Cálida · 1.0×", provider: "voicestudio" },
    { id: "es-AR-ElenaNeural", n: "Elena · Argentina", d: "Femenina Expresiva · 0.95×", provider: "voicestudio" },
    { id: "es-ES-AlvaroNeural", n: "Álvaro · España", d: "Tech & Divulgación · 0.95×", provider: "voicestudio" },
    { id: "voicestudio-omni-es", n: "OmniVoice · Neutro", d: "VoiceStudio Multilingüe · 1.0×", provider: "voicestudio" },
    { id: "voicestudio-piper-dave", n: "Piper Dave · Docu", d: "VoiceStudio Locutor · 0.95×", provider: "voicestudio" },
    { id: "clon-propio", n: "Clon de voz propio", d: "Muestra de estudio 12 s", provider: "voicestudio" },
    // --- Voces Speechify (Español) ---
    { id: "speechify:alejandro", n: "Alejandro", d: "Speechify · Cálida · 1.0×", provider: "speechify" },
    { id: "speechify:aitana", n: "Aitana", d: "Speechify · Brillante · 1.0×", provider: "speechify" },
    { id: "speechify:alejandra", n: "Alejandra", d: "Speechify · Narrativa · 0.95×", provider: "speechify" },
    { id: "speechify:alexa", n: "Alexa", d: "Speechify · Estudio · 1.0×", provider: "speechify" },
    { id: "speechify:alondra", n: "Alondra", d: "Speechify · Documental · 0.95×", provider: "speechify" },
  ];

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.015] p-3">
        <div className="flex items-center justify-between">
          <span className="text-[11.5px] text-white/85">Pulso Nocturno</span>
          <span className="micro-sm text-signal-400/80">Activa</span>
        </div>
        <div className="mt-3 flex h-10 items-end gap-[3px]">
          {bars.map((b, i) => (
            <div
              key={i}
              className="flex-1 rounded-sm bg-gradient-to-t from-beam-500/25 to-beam-300/70"
              style={{ height: `${b * 100}%` }}
            />
          ))}
        </div>
        <div className="mt-3 flex justify-between">
          <span className="micro-sm text-white/25">92 BPM</span>
          <span className="micro-sm text-white/25">-14 LUFS</span>
          <span className="micro-sm text-white/25">Reverb 18%</span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <SectionLabel>Locución neuronal</SectionLabel>
          <span className="micro-sm text-white/30 tracking-wider">
            {voices.length} VOCES
          </span>
        </div>

        <div className="relative">
          <div className="max-h-[178px] overflow-y-auto space-y-2 pr-1.5 subtle-scrollbar">
            {voices.map((v) => {
              const isSelected = selectedVoice === v.id || (v.id === "es-MX-JorgeNeural" && !voices.some((x) => x.id === selectedVoice));
              const isPlaying = playingVoiceId === v.id;
              const isBlocked = v.provider === "speechify" && !speechifyCredits;

              return (
                <div
                  key={v.id}
                  onClick={() => {
                    if (isBlocked) {
                      flash("Créditos agotados en Speechify. Clave bloqueada.");
                      return;
                    }
                    setSelectedVoice(v.id);
                  }}
                  className={cn(
                    "group flex items-center justify-between rounded-xl border p-2.5 transition-colors",
                    isBlocked
                      ? "cursor-not-allowed opacity-40 border-white/[0.04] bg-white/[0.008]"
                      : isSelected
                      ? "cursor-pointer border-beam-400/30 bg-beam-500/[0.07]"
                      : "cursor-pointer border-white/[0.06] bg-white/[0.012] hover:border-white/[0.12]",
                  )}
                >
                  <span className="min-w-0 pr-2">
                    <span className="flex items-center gap-1.5">
                      <span className={cn("block text-[11px] truncate", isSelected ? "text-white/95 font-medium" : "text-white/80")}>
                        {v.n}
                      </span>
                      {v.provider === "speechify" && (
                        <span
                          className={cn(
                            "rounded-[4px] px-1 py-0.5 text-[8.5px] uppercase tracking-wider font-mono",
                            isBlocked
                              ? "border border-rose-500/25 bg-rose-500/10 text-rose-300/80"
                              : "border border-beam-500/25 bg-beam-500/15 text-beam-300",
                          )}
                        >
                          {isBlocked ? "Agotada" : "Speechify"}
                        </span>
                      )}
                      {v.provider === "voicestudio" && (
                        <span className="rounded-[4px] px-1 py-0.5 text-[8.5px] uppercase tracking-wider font-mono border border-cyan-500/25 bg-cyan-500/10 text-cyan-300">
                          VoiceStudio
                        </span>
                      )}
                    </span>
                    <span className="micro-sm mt-1 block text-white/25 truncate">{v.d}</span>
                  </span>

                  <button
                    type="button"
                    disabled={isBlocked}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (isBlocked) {
                        flash("Voz bloqueada sin créditos.");
                        return;
                      }
                      previewVoice(v.id);
                    }}
                    title={isBlocked ? "Voz bloqueada sin créditos" : isPlaying ? "Pausar muestra" : "Reproducir muestra de voz"}
                    className={cn(
                      "shrink-0 rounded-md p-1 transition-colors",
                      isBlocked
                        ? "cursor-not-allowed text-white/10 opacity-30"
                        : isPlaying
                        ? "text-beam-400"
                        : "text-white/25 hover:text-white/70",
                    )}
                  >
                    <IconMusic className={cn("h-3.5 w-3.5", isPlaying && "animate-pulse text-beam-400")} />
                  </button>
                </div>
              );
            })}
          </div>

          {/* Gradiente degradé inferior suave */}
          <div className="pointer-events-none absolute -bottom-0.5 left-0 right-0 h-6 bg-gradient-to-t from-[#0e0f15]/95 via-[#0e0f15]/60 to-transparent" />
        </div>
      </div>

      <Hairline />
      <div className="space-y-1.5">
        <SectionLabel>Mezcla inteligente</SectionLabel>
        <Toggle on label="Ducking automático" hint="-9 dB bajo la voz" onChange={() => {}} />
        <Toggle on label="Reducción de ruido" hint="Perfil de sala" onChange={() => {}} />
        <Toggle on={false} label="Beat detect" hint="92 BPM confirmado" onChange={() => {}} />
      </div>
    </div>
  );
}

function FxTab() {
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <SectionLabel>Look & LUT</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          {PRESETS.map((p, i) => (
            <button
              key={p.id}
              className={cn(
                "group overflow-hidden rounded-xl border text-left transition-all duration-300",
                i === 1 ? "border-beam-400/40 glow-beam" : "border-white/[0.07] hover:border-white/20",
              )}
            >
              <div className="h-14 w-full" style={{ background: p.swatch }} />
              <div className="p-2">
                <div className="text-[10.5px] text-white/80">{p.name}</div>
                <div className="micro-sm mt-1 text-white/25">{p.detail}</div>
              </div>
            </button>
          ))}
        </div>
      </div>
      <Hairline />
      <div className="space-y-3">
        <SectionLabel>Ajustes finos</SectionLabel>
        {[
          { l: "Grano de película", v: 34 },
          { l: "Halación azul", v: 58 },
          { l: "Recorte vertical", v: 82 },
          { l: "Estabilización", v: 96 },
        ].map((s) => (
          <div key={s.l}>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-[10.5px] text-white/55">{s.l}</span>
              <span className="tnum text-[9.5px] text-white/35">{s.v}%</span>
            </div>
            <Meter value={s.v} height={2} />
          </div>
        ))}
      </div>
      <Hairline />
      <div className="flex items-center gap-2.5 rounded-xl border border-white/[0.06] bg-white/[0.012] p-2.5">
        <IconScissors className="h-4 w-4 shrink-0 text-beam-200/70" />
        <div>
          <div className="text-[11px] text-white/80">Reencuadre inteligente</div>
          <div className="micro-sm mt-1 text-white/25">Sigue al sujeto en 9:16</div>
        </div>
      </div>
    </div>
  );
}

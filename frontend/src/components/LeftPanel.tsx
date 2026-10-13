import { useState, useRef, useEffect } from "react";
import { ASSET_FOLDERS, AUTOMATIONS, PRESETS, type Automation } from "@/lib/data";
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
} from "./Icons";

const TABS = [
  { id: "media", label: "Medios", icon: IconLayers },
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
              {tab === "media" && "Tomas y generativos"}
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

        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
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

const CATEGORY_LABEL: Record<Automation["category"], string> = {
  narrativa: "Narrativa",
  ritmo: "Ritmo",
  acabado: "Acabado",
  distribución: "Distribución",
};

function AITab() {
  const {
    progress,
    applied,
    run,
    isCreating,
    createProgress,
    createStatusMessage,
    createVideo,
  } = useEditor();
  const [topicPrompt, setTopicPrompt] = useState("");
  const groups = ["narrativa", "ritmo", "acabado", "distribución"] as const;
  const done = applied.length;
  const total = AUTOMATIONS.length;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (topicPrompt.trim() && !isCreating) {
        const text = topicPrompt.trim();
        setTopicPrompt("");
        createVideo(text);
      }
    }
  };

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-white/[0.06] bg-gradient-to-b from-white/[0.04] to-transparent p-3">
        <div className="flex items-center justify-between">
          <span className="micro-sm text-white/30">
            {isCreating ? "Creando video IA" : "Pipeline automatizado"}
          </span>
          <span className="tnum text-[10px] text-beam-200">
            {isCreating ? `${Math.round(createProgress)}%` : `${done}/${total}`}
          </span>
        </div>
        <div className="mt-2.5">
          <Meter value={isCreating ? createProgress : (done / total) * 100} />
        </div>
        {isCreating ? (
          <p className="mt-2.5 text-[10px] leading-relaxed text-beam-200/90 truncate">
            {createStatusMessage || "Procesando video con IA..."}
          </p>
        ) : (
          <textarea
            value={topicPrompt}
            onChange={(e) => setTopicPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            placeholder="Cada acción se procesa sobre el máster sin re-render. Escribe aquí el tema o especificaciones..."
            className="mt-2.5 w-full resize-none border-0 bg-transparent p-0 text-[10px] leading-relaxed text-white/85 placeholder:text-white/35 focus:outline-none focus:ring-0"
          />
        )}
        {topicPrompt.trim().length > 0 && !isCreating && (
          <div className="mt-1 flex items-center justify-end">
            <button
              type="button"
              onClick={() => {
                const text = topicPrompt.trim();
                setTopicPrompt("");
                createVideo(text);
              }}
              className="micro-sm text-beam-300 hover:text-beam-100 transition-colors"
            >
              Crear video ↵
            </button>
          </div>
        )}
      </div>

      {groups.map((g) => {
        const items = AUTOMATIONS.filter((a) => a.category === g);
        if (!items.length) return null;
        return (
          <div key={g} className="space-y-2">
            <SectionLabel>{CATEGORY_LABEL[g]}</SectionLabel>
            {items.map((a) => {
              const p = progress[a.id];
              const isApplied = applied.includes(a.id);
              const isRunning = p !== undefined;
              return (
                <div
                  key={a.id}
                  className={cn(
                    "group relative overflow-hidden rounded-xl border p-2.5 transition-all duration-500",
                    isApplied
                      ? "border-signal-400/20 bg-signal-400/[0.035]"
                      : isRunning
                        ? "border-beam-400/35 bg-beam-500/[0.07]"
                        : "border-white/[0.06] bg-white/[0.015] hover:border-white/[0.14] hover:bg-white/[0.035]",
                  )}
                >
                  {isRunning && (
                    <span className="shimmer-bar absolute inset-x-0 top-0 h-[2px] overflow-hidden bg-beam-500/20" />
                  )}
                  <div className="flex items-start gap-2.5">
                    <span
                      className={cn(
                        "mt-[1px] grid h-6 w-6 shrink-0 place-items-center rounded-lg border text-[11px]",
                        isApplied
                          ? "border-signal-400/30 bg-signal-400/10 text-signal-400"
                          : "border-beam-400/25 bg-beam-500/10 text-beam-200",
                      )}
                    >
                      {isApplied ? <IconCheck className="h-3 w-3" /> : a.glyph}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-[11.5px] text-white/85">{a.name}</span>
                        <span className="tnum shrink-0 text-[9.5px] text-beam-200/80">
                          +{a.score}
                        </span>
                      </div>
                      <p className="mt-1 text-[10px] leading-snug text-white/35">{a.detail}</p>

                      {isRunning ? (
                        <div className="mt-2 space-y-1">
                          <Meter value={p} height={2} />
                          <div className="flex justify-between">
                            <span className="micro-sm text-beam-200/70">Procesando</span>
                            <span className="tnum text-[9px] text-white/40">
                              {Math.round(p)}%
                            </span>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => run(a.id)}
                          disabled={isApplied}
                          className={cn(
                            "mt-2 w-full rounded-lg border py-[5px] text-[10px] font-medium tracking-wide transition-all duration-300",
                            isApplied
                              ? "cursor-default border-transparent text-signal-400/70"
                              : "border-white/10 bg-white/[0.03] text-white/60 hover:border-beam-300/40 hover:bg-beam-500/15 hover:text-white",
                          )}
                        >
                          {isApplied ? "Aplicado al máster" : "Ejecutar"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

function MediaTab() {
  const { seek, clips } = useEditor();
  const realScenes = clips.filter((c) => c.kind === "scene");

  return (
    <div className="space-y-5">
      {realScenes.length > 0 && (
        <div className="space-y-2">
          <SectionLabel
            right={<span className="tnum text-[9px] text-white/25">{realScenes.length}</span>}
          >
            Escenas del Proyecto
          </SectionLabel>
          {realScenes.map((sc) => (
            <button
              key={sc.id}
              onClick={() => seek(sc.start)}
              className="group flex w-full items-center gap-2.5 rounded-xl border border-white/[0.05] bg-white/[0.012] p-2 text-left transition-all duration-300 hover:border-beam-300/25 hover:bg-white/[0.04]"
            >
              <div className="relative h-11 w-[30px] shrink-0 overflow-hidden rounded-md border border-white/10">
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
                <div className="truncate text-[11px] text-white/80">{sc.label}</div>
                <div className="micro-sm mt-1 text-white/25">
                  {Math.round(sc.start)}s · {Math.round(sc.duration)}s dur
                </div>
              </div>
              <IconChevron className="h-3 w-3 shrink-0 text-white/15 transition-transform group-hover:translate-x-0.5 group-hover:text-white/40" />
            </button>
          ))}
        </div>
      )}

      {ASSET_FOLDERS.map((folder) => (
        <div key={folder.name} className="space-y-2">
          <SectionLabel
            right={<span className="tnum text-[9px] text-white/25">{folder.count}</span>}
          >
            {folder.name}
          </SectionLabel>
          {folder.items.map((it) => (
            <button
              key={it.name}
              className="group flex w-full items-center gap-2.5 rounded-xl border border-white/[0.05] bg-white/[0.012] p-2 text-left transition-all duration-300 hover:border-beam-300/25 hover:bg-white/[0.04]"
            >
              <div className="relative h-11 w-[30px] shrink-0 overflow-hidden rounded-md border border-white/10">
                {it.frame ? (
                  <img
                    src={it.frame}
                    alt=""
                    className="no-drag h-full w-full object-cover opacity-80 transition-opacity group-hover:opacity-100"
                  />
                ) : (
                  <div className="h-full w-full bg-gradient-to-br from-abyss-700 to-ink-900" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-[11px] text-white/80">{it.name}</div>
                <div className="micro-sm mt-1 text-white/25">{it.meta}</div>
              </div>
              <IconChevron className="h-3 w-3 shrink-0 text-white/15 transition-transform group-hover:translate-x-0.5 group-hover:text-white/40" />
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

function TextTab() {
  const { overlays, toggleOverlay } = useEditor();
  const styles = [
    { name: "Kinetic Bold", detail: "Palabra activa resaltada", active: true },
    { name: "Karaoke Flow", detail: "Relleno progresivo" },
    { name: "Minimal Line", detail: "Banda inferior fina" },
    { name: "Outline Pop", detail: "Contorno + sombra" },
  ];
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <SectionLabel>Estilo de subtítulo</SectionLabel>
        {styles.map((s) => (
          <button
            key={s.name}
            className={cn(
              "flex w-full items-center justify-between rounded-xl border p-2.5 text-left transition-all duration-300",
              s.active
                ? "border-beam-400/35 bg-beam-500/[0.08]"
                : "border-white/[0.06] bg-white/[0.015] hover:border-white/[0.14]",
            )}
          >
            <span>
              <span className="block text-[11.5px] text-white/85">{s.name}</span>
              <span className="micro-sm mt-1 block text-white/25">{s.detail}</span>
            </span>
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                s.active ? "bg-beam-300 shadow-[0_0_10px_2px_rgba(126,163,255,0.7)]" : "bg-white/15",
              )}
            />
          </button>
        ))}
      </div>
      <Hairline />
      <div className="space-y-1.5">
        <SectionLabel>Superposición</SectionLabel>
        <Toggle on={overlays.captions} onChange={() => toggleOverlay("captions")} label="Subtítulos" hint="92 palabras alineadas" />
        <Toggle on={overlays.tracking} onChange={() => toggleOverlay("tracking")} label="Caja de seguimiento" hint="Rostro principal" />
        <Toggle on={overlays.safe} onChange={() => toggleOverlay("safe")} label="Zonas seguras" hint="UI de plataforma" />
      </div>
      <Hairline />
      <div className="space-y-2">
        <SectionLabel>Tipografía</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          {["Inter Tight", "Instrument", "Neue Haas", "Söhne Mono"].map((f, i) => (
            <div
              key={f}
              className={cn(
                "rounded-lg border px-2.5 py-2 text-[10.5px]",
                i === 0 ? "border-beam-400/30 bg-beam-500/[0.08] text-white/85" : "border-white/[0.06] text-white/45",
              )}
            >
              {f}
            </div>
          ))}
        </div>
      </div>
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

import { useEffect, useState, useRef } from "react";
import { useEditor } from "@/lib/store";
import { PLATFORMS } from "@/lib/data";
import { Hairline, IconButton } from "./ui";
import {
  IconChevron,
  IconDownload,
  IconRedo,
  IconUndo,
  IconCpu,
  IconCheck,
  IconSparkle,
} from "./Icons";
import { ExportModal } from "./ExportModal";
import { cn } from "@/utils/cn";

function Mark() {
  return (
    <div className="relative grid h-8 w-8 place-items-center">
      <div className="absolute inset-0 rounded-[11px] bg-gradient-to-br from-beam-500/40 via-abyss-700 to-transparent opacity-80 blur-[6px]" />
      <div className="relative grid h-8 w-8 place-items-center rounded-[11px] border border-white/10 bg-gradient-to-br from-abyss-700/90 to-ink-950 shadow-[0_1px_0_0_rgba(255,255,255,0.12)_inset]">
        <svg viewBox="0 0 24 24" className="h-4 w-4 text-beam-200">
          <circle cx="12" cy="12" r="7.2" fill="none" stroke="currentColor" strokeWidth="1" opacity=".55" />
          <path d="M12 4.8V12l5.2 3" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          <circle cx="12" cy="12" r="1.6" fill="#7ea3ff" />
        </svg>
      </div>
    </div>
  );
}

export function TopBar() {
  const {
    platform,
    setPlatform,
    running,
    score,
    projects,
    activeProjectId,
    activeProjectTitle,
    selectProject,
    exportMaster,
    duration,
    ratio,
    subtitleStyle,
    overlays,
  } = useEditor();
  const [exporting, setExporting] = useState<number | null>(null);
  const [projectOpen, setProjectOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setProjectOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (exporting === null) return;
    if (exporting >= 100) {
      const t = window.setTimeout(() => setExporting(null), 1800);
      return () => window.clearTimeout(t);
    }
    const t = window.setTimeout(
      () => setExporting((e) => Math.min(100, (e ?? 0) + 4 + Math.random() * 7)),
      90,
    );
    return () => window.clearTimeout(t);
  }, [exporting]);

  const handleExportClick = () => {
    if (exporting !== null) return;
    setModalOpen(true);
  };

  const handleModalConfirm = (opts: {
    burnSubtitles: boolean;
    resolution: "1080p" | "4k" | "720p";
    fps: 30 | 60;
    title: string;
  }) => {
    setModalOpen(false);
    setExporting(0);
    exportMaster({
      burnSubtitles: opts.burnSubtitles,
      style: subtitleStyle,
      title: opts.title,
    });
  };

  const openCopilot = () => {
    const copilot = (window as any).agentCopilot;
    if (copilot) {
      if (typeof copilot.toggle === "function") {
        copilot.toggle();
      } else if (typeof copilot.open === "function") {
        copilot.open();
      }
    } else {
      const fab = document.getElementById("agentFabLauncher");
      if (fab) fab.click();
    }
  };

  return (
    <header className="relative z-30 shrink-0">
      <div className="glass-deep flex h-14 items-center gap-4 border-x-0 border-t-0 px-3 sm:px-4">
        {/* brand */}
        <div className="flex items-center gap-3">
          <Mark />
          <div className="hidden sm:block">
            <div className="flex items-baseline gap-1.5">
              <span className="text-[13px] font-medium tracking-[0.2em] text-white">LUMEN</span>
              <span className="serif-display text-[15px] italic leading-none text-beam-300">studio</span>
            </div>
            <div className="micro-sm mt-1 text-white/25">Neural video suite · v4.2</div>
          </div>
        </div>

        <div className="mx-1 hidden h-6 w-px bg-white/[0.07] md:block" />

        {/* project selector dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setProjectOpen(!projectOpen)}
            className="group hidden min-w-0 items-center gap-2 rounded-xl border border-white/[0.05] bg-white/[0.015] px-2.5 py-1.5 transition-colors hover:bg-white/[0.04] md:flex"
            title="Seleccionar proyecto"
          >
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-signal-400 anim-ping" />
            <span className="max-w-[180px] truncate text-[11px] text-white/75">
              {activeProjectTitle || "Ritmo Nocturno — EP.02"}
            </span>
            <span className="micro-sm shrink-0 text-white/25">
              {activeProjectId ? "En vivo" : "Autoguardado"}
            </span>
            <IconChevron
              className={cn(
                "h-3 w-3 text-white/25 transition-transform duration-200",
                projectOpen && "rotate-180 text-white/60",
              )}
            />
          </button>

          {projectOpen && (
            <div className="glass-deep absolute left-0 top-full mt-2 w-72 overflow-hidden rounded-2xl border border-white/10 p-1.5 shadow-[0_20px_60px_rgba(0,0,0,0.8)] z-50 backdrop-blur-2xl">
              <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.06]">
                <span className="micro-sm text-white/40 font-semibold tracking-wider uppercase">
                  Proyectos en Servidor
                </span>
                <span className="tnum text-[10px] text-beam-200">{projects.length}</span>
              </div>
              <div className="max-h-64 overflow-y-auto py-1">
                {projects.length === 0 ? (
                  <div className="px-3 py-4 text-center text-[11px] text-white/35">
                    No hay proyectos en el servidor aún.
                  </div>
                ) : (
                  projects.map((p) => {
                    const isCurrent = activeProjectId === p.id;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => {
                          selectProject(p.id);
                          setProjectOpen(false);
                        }}
                        className={cn(
                          "flex w-full items-center justify-between gap-2.5 rounded-xl px-2.5 py-2 text-left transition-colors",
                          isCurrent
                            ? "border border-beam-400/30 bg-beam-500/15 text-white"
                            : "text-white/70 hover:bg-white/[0.05] hover:text-white",
                        )}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-[11px] font-medium text-white/90">
                            {p.name}
                          </div>
                          <div className="micro-sm mt-0.5 text-white/30">
                            {p.status} · {p.duration ? `${Math.round(p.duration)}s` : "En proceso"}
                          </div>
                        </div>
                        {isCurrent && (
                          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-signal-400" />
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex-1" />

        {/* engine status */}
        <div className="hidden items-center gap-2 rounded-xl border border-white/[0.05] bg-black/30 px-2.5 py-1.5 lg:flex">
          <IconCpu className="h-3.5 w-3.5 text-beam-300/70" />
          <span className="micro-sm text-white/35">Tensor</span>
          <span className="micro-sm text-white/60">RT·48C</span>
          <span className="mx-1 h-3 w-px bg-white/10" />
          <span className={running ? "micro-sm text-beam-200" : "micro-sm text-white/30"}>
            {running ? "Procesando" : "Inactivo"}
          </span>
        </div>

        {/* platform picker */}
        <div className="hidden items-center gap-0.5 rounded-xl border border-white/[0.06] bg-black/40 p-0.5 sm:flex">
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              onClick={() => setPlatform(p.id)}
              className={
                "rounded-[9px] px-2.5 py-[6px] text-[10px] font-medium tracking-wide transition-all duration-300 " +
                (platform === p.id
                  ? "bg-gradient-to-b from-white/[0.12] to-white/[0.03] text-white shadow-[0_1px_0_0_rgba(255,255,255,0.1)_inset]"
                  : "text-white/35 hover:text-white/70")
              }
            >
              {p.name}
            </button>
          ))}
        </div>

        {/* history */}
        <div className="hidden items-center gap-1 md:flex">
          <IconButton size="sm" title="Deshacer">
            <IconUndo className="h-3.5 w-3.5" />
          </IconButton>
          <IconButton size="sm" title="Rehacer">
            <IconRedo className="h-3.5 w-3.5" />
          </IconButton>
        </div>

        {/* score chip */}
        <div className="hidden items-center gap-2 rounded-xl border border-beam-400/20 bg-beam-500/[0.07] px-2.5 py-1.5 xl:flex">
          <span className="micro-sm text-white/35">Score viral</span>
          <span className="tnum text-[13px] font-light text-beam-200">{score}</span>
        </div>

        {/* Copilot Chat trigger */}
        <button
          type="button"
          onClick={openCopilot}
          title="Abrir AetherCopilot AI (Chat multi-modelo)"
          className="relative flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-xl border border-purple-500/30 bg-gradient-to-b from-purple-500/15 to-purple-900/20 px-3 text-[11px] font-medium text-purple-200 shadow-[0_1px_0_0_rgba(255,255,255,0.1)_inset,0_8px_20px_-10px_rgba(168,85,247,0.7)] transition-all duration-300 hover:border-purple-400/50 hover:from-purple-500/25"
        >
          <IconSparkle className="h-3.5 w-3.5 shrink-0 text-purple-300" />
          <span className="whitespace-nowrap">Copilot IA</span>
        </button>

        {/* export */}
        <button
          type="button"
          onClick={handleExportClick}
          className="relative flex h-8 shrink-0 items-center gap-2 whitespace-nowrap overflow-hidden rounded-xl border border-white/10 bg-gradient-to-b from-white/[0.14] to-white/[0.04] px-3.5 text-[11px] font-medium text-white shadow-[0_1px_0_0_rgba(255,255,255,0.18)_inset,0_10px_30px_-14px_rgba(47,92,255,0.9)] transition-all duration-300 hover:border-beam-300/40 hover:from-beam-500/25"
        >
          {exporting !== null && exporting < 100 && (
            <span
              className="absolute inset-y-0 left-0 bg-beam-500/25 transition-[width] duration-150"
              style={{ width: `${exporting}%` }}
            />
          )}
          {exporting === null && <IconDownload className="relative h-3.5 w-3.5 shrink-0" />}
          {exporting !== null && exporting < 100 ? (
            <span className="relative tnum whitespace-nowrap">Renderizando {Math.round(exporting)}%</span>
          ) : exporting !== null ? (
            <>
              <IconCheck className="relative h-3.5 w-3.5 shrink-0 text-signal-400" />
              <span className="relative whitespace-nowrap">Máster listo</span>
            </>
          ) : null}
          {exporting === null && <span className="relative whitespace-nowrap">Exportar</span>}
        </button>

        {/* avatar */}
        <div className="hidden h-8 w-8 shrink-0 place-items-center rounded-full border border-white/10 bg-gradient-to-br from-abyss-700 to-ink-900 text-[10px] font-medium text-beam-200 sm:grid">
          MR
        </div>
      </div>
      <Hairline className="absolute inset-x-0 bottom-0" />

      {/* Export Specifications Modal */}
      <ExportModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onConfirm={handleModalConfirm}
        defaultTitle={activeProjectTitle || "KAI_Video_Master"}
        durationSec={duration}
        ratio={ratio}
        subtitleStyle={subtitleStyle}
        subtitlesActive={overlays.captions}
      />
    </header>
  );
}

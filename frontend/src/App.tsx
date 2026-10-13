import { AUTOMATIONS, BASE_RETENTION, compact, retentionAt } from "@/lib/data";
import { EditorProvider, useEditor } from "@/lib/store";
import { LeftPanel } from "@/components/LeftPanel";
import { MetricsPanel, ActivityBar } from "@/components/MetricsPanel";
import { PreviewStage, Transport } from "@/components/PreviewStage";
import { Timeline } from "@/components/Timeline";
import { TopBar } from "@/components/TopBar";
import { cn } from "@/utils/cn";

/* compact strip: métricas esenciales en pantallas sin panel derecho */
function CompactMetrics() {
  const { score, metrics, boost } = useEditor();
  const pts = BASE_RETENTION.map((_, i) => retentionAt(i, boost));
  const d = pts
    .map((v, i) => `${i === 0 ? "M" : "L"}${(i / (pts.length - 1)) * 90},${28 - v * 24}`)
    .join(" ");
  return (
    <div className="glass-soft hidden h-[54px] shrink-0 items-center gap-4 overflow-x-auto rounded-none border-x-0 border-y-0 px-3 lg:flex xl:hidden">
      <div className="flex shrink-0 items-baseline gap-1.5">
        <span className="micro-sm text-white/30">Score</span>
        <span className="tnum text-[16px] font-light text-beam-200">{score}</span>
      </div>
      <span className="h-6 w-px shrink-0 bg-white/[0.07]" />
      <div className="flex shrink-0 items-baseline gap-1.5">
        <span className="micro-sm text-white/30">Alcance</span>
        <span className="tnum text-[14px] font-light text-white">{compact(metrics.reach)}</span>
      </div>
      <span className="h-6 w-px shrink-0 bg-white/[0.07]" />
      <div className="flex shrink-0 items-baseline gap-1.5">
        <span className="micro-sm text-white/30">Guardados</span>
        <span className="tnum text-[14px] font-light text-white">{compact(metrics.saves)}</span>
      </div>
      <svg viewBox="0 0 90 30" className="h-6 w-24 shrink-0">
        <path d={d} fill="none" stroke="#7ea3ff" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
      <span className="micro-sm shrink-0 text-white/20">+{Math.round(boost * 100)} pts IA</span>
    </div>
  );
}

/* chips de IA para pantallas sin panel izquierdo */
function CompactAI() {
  const { run, applied, progress } = useEditor();
  return (
    <div className="flex shrink-0 items-center gap-2 overflow-x-auto px-3 py-2 md:hidden">
      {AUTOMATIONS.slice(0, 5).map((a) => {
        const p = progress[a.id];
        const done = applied.includes(a.id);
        return (
          <button
            key={a.id}
            onClick={() => run(a.id)}
            disabled={done || p !== undefined}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-[10px] transition-all",
              done
                ? "border-signal-400/25 bg-signal-400/[0.07] text-signal-400/80"
                : p !== undefined
                  ? "border-beam-400/40 bg-beam-500/15 text-beam-100"
                  : "border-white/[0.08] bg-white/[0.02] text-white/60",
            )}
          >
            <span>{a.glyph}</span>
            {done ? "Aplicado" : p !== undefined ? `${Math.round(p)}%` : a.name}
          </button>
        );
      })}
    </div>
  );
}

function Shell() {
  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-ink-1000 text-white">
      {/* ambient background */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(120%_90%_at_50%_-10%,#0a142c_0%,#05070c_45%,#030407_100%)]" />
        <div className="absolute inset-0 grid-lines opacity-40" />
        <div className="absolute -left-32 top-1/4 h-[420px] w-[420px] rounded-full bg-beam-500/[0.09] blur-[130px] anim-breathe" />
        <div className="absolute -right-24 bottom-0 h-[380px] w-[380px] rounded-full bg-abyss-600/45 blur-[130px]" />
        <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-black/60 to-transparent" />
      </div>

      <TopBar />

      <main className="flex min-h-0 flex-1">
        <div className="hidden md:flex">
          <LeftPanel />
        </div>

        <div className="flex min-w-0 flex-1 flex-col">
          <PreviewStage />
          <CompactAI />
          <Transport />
          <CompactMetrics />
          <Timeline />
        </div>

        <MetricsPanel />
      </main>

      <ActivityBar />
    </div>
  );
}

export default function App() {
  return (
    <EditorProvider>
      <Shell />
    </EditorProvider>
  );
}

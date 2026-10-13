import { useEffect, useMemo, useRef, useState } from "react";
import {
  AUDIENCE,
  AUTOMATIONS,
  BASE_RETENTION,
  HEATMAP,
  MOMENTS,
  PLATFORMS,
  compact,
  retentionAt,
} from "@/lib/data";
import { useEditor } from "@/lib/store";
import { cn } from "@/utils/cn";
import { Hairline, Meter, SectionLabel } from "./ui";
import {
  IconBookmark,
  IconChart,
  IconCheck,
  IconClock,
  IconComment,
  IconEye,
  IconFlame,
  IconSend,
  IconSparkle,
} from "./Icons";

/* ---------- animated counter ---------- */
function Counter({ value, format }: { value: number; format: (n: number) => string }) {
  const [shown, setShown] = useState(value);
  const from = useRef(value);
  useEffect(() => {
    const start = performance.now();
    const a = from.current;
    const b = value;
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / 700);
      const e = 1 - Math.pow(1 - p, 3);
      setShown(a + (b - a) * e);
      if (p < 1) raf = requestAnimationFrame(tick);
      else from.current = b;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{format(shown)}</>;
}

/* ---------- gauge ---------- */
function ScoreGauge() {
  const { score, boost } = useEditor();
  const L = Math.PI * 64;
  const angle = -90 + (score / 100) * 180;
  const grade =
    score >= 90 ? "Élite" : score >= 80 ? "Alto potencial" : score >= 70 ? "Sólido" : "En desarrollo";

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/[0.07] bg-gradient-to-b from-white/[0.045] to-transparent p-3.5">
      <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-beam-500/18 blur-3xl anim-breathe" />
      <div className="flex items-start justify-between">
        <div>
          <span className="micro-sm text-white/30">Score viral</span>
          <div className="mt-1.5 flex items-baseline gap-1.5">
            <span className="text-glow tnum text-[30px] font-light leading-none text-white">
              <Counter value={score} format={(n) => String(Math.round(n))} />
            </span>
            <span className="text-[11px] text-white/30">/ 100</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <IconFlame className="h-3 w-3 text-ember-400/80" />
            <span className="text-[10px] text-white/55">{grade}</span>
          </div>
        </div>
        <svg viewBox="0 0 160 96" className="h-[86px] w-[142px]">
          <defs>
            <linearGradient id="gg" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#142a5e" />
              <stop offset="55%" stopColor="#2f5cff" />
              <stop offset="100%" stopColor="#7ea3ff" />
            </linearGradient>
          </defs>
          <path d="M16 84 A64 64 0 1 1 144 84" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="7" strokeLinecap="round" />
          <path
            d="M16 84 A64 64 0 1 1 144 84"
            fill="none"
            stroke="url(#gg)"
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={L}
            strokeDashoffset={L * (1 - score / 100)}
            style={{ transition: "stroke-dashoffset 900ms cubic-bezier(.2,.8,.2,1)" }}
          />
          {Array.from({ length: 11 }).map((_, i) => {
            const a = ((-90 + i * 18) * Math.PI) / 180;
            const r1 = 50;
            const r2 = i % 5 === 0 ? 43 : 47;
            return (
              <line
                key={i}
                x1={80 + Math.sin(a) * r1}
                y1={84 - Math.cos(a) * r1}
                x2={80 + Math.sin(a) * r2}
                y2={84 - Math.cos(a) * r2}
                stroke="rgba(255,255,255,0.16)"
                strokeWidth="1"
              />
            );
          })}
          <g style={{ transform: `rotate(${angle}deg)`, transformOrigin: "80px 84px", transition: "transform 900ms cubic-bezier(.2,.8,.2,1)" }}>
            <line x1="80" y1="84" x2="80" y2="34" stroke="#a9c2ff" strokeWidth="1.4" strokeLinecap="round" />
          </g>
          <circle cx="80" cy="84" r="3.4" fill="#0b0f18" stroke="#7ea3ff" strokeWidth="1.2" />
        </svg>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2">
        {[
          { l: "Hook", v: Math.min(98, 58 + boost * 80), u: "%" },
          { l: "Retención", v: Math.min(92, (0.41 + boost) * 100), u: "%" },
          { l: "Rebote", v: Math.max(5, 32 - boost * 48), u: "%" },
        ].map((k) => (
          <div key={k.l} className="rounded-lg border border-white/[0.05] bg-black/25 px-2 py-1.5">
            <div className="micro-sm text-white/25">{k.l}</div>
            <div className="tnum mt-1 text-[12px] font-light text-white/90">
              {Math.round(k.v)}
              <span className="text-[9px] text-white/30">{k.u}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- retention chart ---------- */
function RetentionChart() {
  const { boost, time, seek, applied } = useEditor();
  const [hover, setHover] = useState<number | null>(null);
  const n = BASE_RETENTION.length;
  const W = 300;
  const H = 104;

  const cur = useMemo(() => BASE_RETENTION.map((_, i) => retentionAt(i, boost)), [boost]);
  const x = (i: number) => (i / (n - 1)) * W;
  const y = (v: number) => H - v * (H - 10) - 4;

  const line = cur.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${W},${H} L0,${H} Z`;
  const baseLine = BASE_RETENTION.map(
    (v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`,
  ).join(" ");

  const idx = hover ?? Math.round((time / 32) * (n - 1));
  const activeIdx = Math.max(0, Math.min(n - 1, idx));
  const t = (activeIdx / (n - 1)) * 32;

  return (
    <div className="space-y-2">
      <SectionLabel
        right={
          <span className="flex items-center gap-2">
            <span className="flex items-center gap-1">
              <span className="h-[2px] w-3 rounded-full bg-beam-300" />
              <span className="micro-sm text-white/35">Proyectada</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="h-[2px] w-3 rounded-full bg-white/20" />
              <span className="micro-sm text-white/25">Base</span>
            </span>
          </span>
        }
      >
        Curva de retención
      </SectionLabel>

      <div
        className="relative overflow-hidden rounded-xl border border-white/[0.06] bg-black/30 p-2"
        onPointerMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          setHover(Math.round(((e.clientX - r.left) / r.width) * (n - 1)));
        }}
        onPointerLeave={() => setHover(null)}
        onPointerDown={() => seek(t)}
      >
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="none">
          <defs>
            <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2f5cff" stopOpacity="0.42" />
              <stop offset="100%" stopColor="#2f5cff" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[0.25, 0.5, 0.75].map((g) => (
            <line key={g} x1="0" y1={y(g)} x2={W} y2={y(g)} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
          ))}
          <path d={area} fill="url(#fill)" />
          <path d={baseLine} fill="none" stroke="rgba(255,255,255,0.16)" strokeWidth="1" strokeDasharray="3 3" />
          <path d={line} fill="none" stroke="#7ea3ff" strokeWidth="1.5" strokeLinecap="round" />
          {MOMENTS.map((m) => (
            <circle
              key={m.t}
              cx={x((m.t / 32) * (n - 1))}
              cy={y(retentionAt(Math.round((m.t / 32) * (n - 1)), boost))}
              r="2.6"
              fill={m.kind === "risk" ? "#ff7a59" : "#46e0c0"}
            />
          ))}
          <line
            x1={x((time / 32) * (n - 1))}
            y1="0"
            x2={x((time / 32) * (n - 1))}
            y2={H}
            stroke="#7ea3ff"
            strokeWidth="0.8"
            opacity="0.5"
          />
          <circle
            cx={x(activeIdx)}
            cy={y(cur[activeIdx])}
            r="3.4"
            fill="#0b0f18"
            stroke="#a9c2ff"
            strokeWidth="1.4"
          />
        </svg>
        <div className="mt-1 flex justify-between px-0.5">
          {["0s", "8s", "16s", "24s", "32s"].map((l) => (
            <span key={l} className="tnum text-[8.5px] text-white/20">
              {l}
            </span>
          ))}
        </div>
        <div className="pointer-events-none absolute right-2 top-2 rounded-md border border-white/10 bg-ink-950/85 px-2 py-1 text-right backdrop-blur-sm">
          <div className="tnum text-[13px] font-light leading-none text-white">
            {Math.round(cur[activeIdx] * 100)}%
          </div>
          <div className="micro-sm mt-1 text-white/30">{t.toFixed(1)}s</div>
        </div>
        <div className="pointer-events-none absolute bottom-6 left-2 flex items-center gap-1 rounded-md border border-signal-400/20 bg-signal-400/[0.07] px-1.5 py-0.5">
          <IconSparkle className="h-2.5 w-2.5 text-signal-400/80" />
          <span className="micro-sm text-signal-400/80">
            +{Math.round(boost * 100)} pts por IA ({applied.length})
          </span>
        </div>
      </div>
    </div>
  );
}

/* ---------- moments ---------- */
function Moments() {
  const { seek } = useEditor();
  const tone: Record<string, string> = {
    peak: "text-signal-400 border-signal-400/25",
    risk: "text-ember-400 border-ember-400/25",
    reveal: "text-beam-200 border-beam-400/25",
    cta: "text-white/70 border-white/12",
  };
  return (
    <div className="space-y-1.5">
      <SectionLabel>Momentos clave</SectionLabel>
      {MOMENTS.map((m) => (
        <button
          key={m.t}
          onClick={() => seek(m.t)}
          className="group flex w-full items-center gap-2.5 rounded-xl border border-white/[0.05] bg-white/[0.012] p-2 text-left transition-all duration-300 hover:border-white/[0.14] hover:bg-white/[0.035]"
        >
          <span className={cn("tnum w-9 shrink-0 rounded-md border px-1 py-0.5 text-center text-[9.5px]", tone[m.kind])}>
            {m.t}s
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[11px] text-white/80">{m.label}</span>
            <span className="block truncate text-[9.5px] text-white/30">{m.note}</span>
          </span>
        </button>
      ))}
    </div>
  );
}

/* ---------- audience + heatmap ---------- */
function Audience() {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="space-y-2">
        <SectionLabel>Audiencia</SectionLabel>
        {AUDIENCE.map((a) => (
          <div key={a.label} className="space-y-1">
            <div className="flex justify-between">
              <span className="text-[9.5px] text-white/45">{a.label}</span>
              <span className="tnum text-[9px] text-white/30">{a.value}%</span>
            </div>
            <Meter value={a.value * 2} height={2} />
          </div>
        ))}
      </div>
      <div className="space-y-2">
        <SectionLabel>Mejor hora</SectionLabel>
        <div className="space-y-[3px]">
          {HEATMAP.slice(0, 7).map((d) => (
            <div key={d.day} className="flex items-center gap-[3px]">
              <span className="micro-sm w-2.5 text-white/25">{d.day}</span>
              {d.slots.map((s, i) => (
                <span
                  key={i}
                  className="h-2.5 flex-1 rounded-[2px] transition-transform duration-300 hover:scale-125"
                  style={{
                    background: `rgba(47,92,255,${0.08 + (s / 100) * 0.72})`,
                    boxShadow: s > 88 ? "0 0 8px 1px rgba(126,163,255,0.55)" : undefined,
                  }}
                />
              ))}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-1.5 pt-1">
          <IconClock className="h-3 w-3 text-beam-200/60" />
          <span className="micro-sm text-white/35">Pico 21:00</span>
        </div>
      </div>
    </div>
  );
}

/* ---------- next best actions ---------- */
function NextActions() {
  const { applied, run, progress } = useEditor();
  const pending = AUTOMATIONS.filter((a) => !applied.includes(a.id))
    .sort((a, b) => b.score + b.reach - (a.score + a.reach))
    .slice(0, 3);

  if (!pending.length)
    return (
      <div className="flex items-center gap-2.5 rounded-xl border border-signal-400/20 bg-signal-400/[0.05] p-3">
        <IconCheck className="h-4 w-4 shrink-0 text-signal-400" />
        <div>
          <div className="text-[11px] text-white/85">Pipeline completo</div>
          <div className="micro-sm mt-1 text-white/30">Máster optimizado al máximo</div>
        </div>
      </div>
    );

  return (
    <div className="space-y-1.5">
      <SectionLabel>Siguiente acción óptima</SectionLabel>
      {pending.map((a, i) => {
        const p = progress[a.id];
        return (
          <div
            key={a.id}
            className={cn(
              "relative overflow-hidden rounded-xl border p-2.5",
              i === 0
                ? "border-beam-400/25 bg-gradient-to-r from-beam-500/[0.1] to-transparent"
                : "border-white/[0.06] bg-white/[0.012]",
            )}
          >
            <div className="flex items-center gap-2.5">
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg border border-beam-400/25 bg-beam-500/10 text-[11px] text-beam-200">
                {a.glyph}
              </span>
              <div className="min-w-0 flex-1">
                <div className="truncate text-[11px] text-white/85">{a.name}</div>
                <div className="micro-sm mt-1 text-white/25">
                  +{a.score} score · +{a.reach} alcance
                </div>
              </div>
              <button
                onClick={() => run(a.id)}
                disabled={p !== undefined}
                className="shrink-0 rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1.5 text-[10px] font-medium text-white/75 transition-all duration-300 hover:border-beam-300/40 hover:bg-beam-500/20 hover:text-white"
              >
                {p !== undefined ? `${Math.round(p)}%` : "Aplicar"}
              </button>
            </div>
            {p !== undefined && (
              <div className="mt-2">
                <Meter value={p} height={2} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ---------- panel ---------- */
export function MetricsPanel() {
  const { metrics, platform, applied, running } = useEditor();
  const pf = PLATFORMS.find((p) => p.id === platform)!;

  return (
    <aside className="glass-soft hidden min-h-0 w-[336px] shrink-0 flex-col rounded-none border-y-0 border-l-0 xl:flex">
      <div className="flex items-center justify-between px-4 pb-3 pt-4">
        <div>
          <h2 className="serif-display text-[17px] leading-none text-white">Escenario viral</h2>
          <p className="micro-sm mt-1.5 text-white/25">Predicción · {pf.handle}</p>
        </div>
        <div className="flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-black/40 px-2 py-1">
          <span className={cn("h-1 w-1 rounded-full", running ? "bg-beam-300 anim-ping" : "bg-signal-400")} />
          <span className="micro-sm text-white/45">{running ? "Recalculando" : "Estable"}</span>
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-3.5 pb-5">
        <ScoreGauge />

        <div className="grid grid-cols-2 gap-2">
          {[
            { l: "Alcance 48 h", v: metrics.reach, f: compact, g: <IconEye className="h-3 w-3" /> },
            { l: "Visualizaciones", v: metrics.views, f: compact, g: <IconChart className="h-3 w-3" /> },
            { l: "Guardados", v: metrics.saves, f: compact, g: <IconBookmark className="h-3 w-3" /> },
            { l: "Compartidos", v: metrics.shares, f: compact, g: <IconSend className="h-3 w-3" /> },
            { l: "Comentarios", v: metrics.comments, f: compact, g: <IconComment className="h-3 w-3" /> },
            { l: "CTR portada", v: metrics.ctr, f: (n: number) => `${n.toFixed(1)}%`, g: <IconFlame className="h-3 w-3" /> },
          ].map((s) => (
            <div key={s.l} className="group relative overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.015] p-2.5 transition-colors hover:border-white/[0.14]">
              <div className="flex items-center justify-between">
                <span className="micro-sm text-white/28">{s.l}</span>
                <span className="text-white/20">{s.g}</span>
              </div>
              <div className="tnum mt-2 text-[16px] font-light leading-none text-white">
                <Counter value={s.v} format={s.f} />
              </div>
              <div className="pointer-events-none absolute inset-x-0 -bottom-6 h-8 bg-beam-500/20 opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100" />
            </div>
          ))}
        </div>

        <RetentionChart />
        <Hairline />
        <Moments />
        <Hairline />
        <Audience />
        <Hairline />
        <NextActions />

        <div className="rounded-xl border border-white/[0.06] bg-black/25 p-3">
          <div className="flex items-center justify-between">
            <span className="micro-sm text-white/30">Publicación sugerida</span>
            <span className="micro-sm text-beam-200/80">{pf.peak}</span>
          </div>
          <p className="mt-2 text-[10px] leading-relaxed text-white/35">
            Ventana óptima detectada con {applied.length} optimizaciones aplicadas.
            Retención media estimada {Math.round(metrics.avg * 100)} %.
          </p>
        </div>
      </div>
    </aside>
  );
}

export function ActivityBar() {
  const { log, toast } = useEditor();
  return (
    <>
      <footer className="glass-deep hidden h-8 shrink-0 items-center gap-3 rounded-none border-x-0 border-b-0 px-3 lg:flex">
        <span className="micro-sm text-white/25">Registro neuronal</span>
        <div className="h-3 w-px bg-white/10" />
        <div className="flex min-w-0 flex-1 items-center gap-4 overflow-hidden">
          {log.slice(0, 5).map((l, i) => (
            <span
              key={l.id}
              className={cn(
                "flex shrink-0 items-center gap-1.5 text-[10px] transition-opacity",
                i === 0 ? "text-white/70" : "text-white/25",
              )}
            >
              <span
                className={cn(
                  "h-1 w-1 rounded-full",
                  l.kind === "warn" ? "bg-ember-400" : l.kind === "info" ? "bg-signal-400" : "bg-beam-400",
                )}
              />
              <span className="tnum text-white/20">{l.at}</span>
              {l.text}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <span className="micro-sm text-white/20">GPU 41 %</span>
          <span className="micro-sm text-white/20">VRAM 6.2 / 16 GB</span>
          <span className="micro-sm text-beam-200/70">48 núcleos tensor</span>
        </div>
      </footer>

      <div
        className={cn(
          "pointer-events-none fixed bottom-16 left-1/2 z-50 -translate-x-1/2 transition-all duration-500",
          toast ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0",
        )}
      >
        <div className="glass flex items-center gap-2.5 rounded-full px-4 py-2.5">
          <IconSparkle className="h-3.5 w-3.5 text-beam-200" />
          <span className="text-[11px] text-white/85">{toast}</span>
        </div>
      </div>
    </>
  );
}

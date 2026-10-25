import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { Collapsible, Meter, SectionLabel } from "./ui";
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

function IconRefresh({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 4v6h-6" />
      <path d="M1 20v-6h6" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

function IconExternalLink({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

function IconBrain({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04z" />
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04z" />
    </svg>
  );
}

interface ChannelVideoItem {
  project_id: string;
  video_id: string;
  title: string;
  channel_id: string;
  channel_title: string;
  channel_tag: string;
  published_at?: string;
  structure_type?: string;
  hook_type?: string;
  metrics: {
    views: number;
    likes: number;
    comments: number;
    shares?: number;
    saves?: number;
    retention_pct: number;
    viral_score: number;
    hook_pct: number;
    ctr_pct: number;
  };
}

interface RankedStructure {
  structure_type: string;
  name: string;
  avg_score: number;
  video_count: number;
}

interface RankedHook {
  hook_type: string;
  name: string;
  avg_retention_pct: number;
  sample_count: number;
}

interface ChannelIntel {
  channel_id: string;
  channel_title: string;
  channel_tag: string;
  total_videos_analyzed: number;
  total_views: number;
  avg_retention_pct: number;
  avg_viral_score: number;
  best_structure?: RankedStructure;
  ranked_structures?: RankedStructure[];
  best_hook?: RankedHook;
  ranked_hooks?: RankedHook[];
  top_video_example?: {
    title: string;
    structure: string;
    score: number;
  };
  anti_patterns?: string[];
}

interface MetricsOverviewData {
  channels: ChannelIntel[];
  total_tracked_videos: number;
  recent_videos: ChannelVideoItem[];
}

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
function ScoreGauge({
  overrideScore,
  customLabel,
  customGrade,
  color = "#2f5cff",
  customHook,
  customRetention,
  customBounce,
}: {
  overrideScore?: number;
  customLabel?: string;
  customGrade?: string;
  color?: string;
  customHook?: number;
  customRetention?: number;
  customBounce?: number;
} = {}) {
  const { score, boost } = useEditor();
  const currentScore = overrideScore !== undefined ? overrideScore : score;
  const L = Math.PI * 64;
  const angle = -90 + (currentScore / 100) * 180;
  const grade =
    customGrade ||
    (currentScore >= 90 ? "Élite" : currentScore >= 80 ? "Alto potencial" : currentScore >= 70 ? "Sólido" : "En desarrollo");

  const hookVal = customHook !== undefined ? customHook : Math.min(98, 58 + boost * 80);
  const retVal = customRetention !== undefined ? customRetention : Math.min(92, (0.41 + boost) * 100);
  const bounceVal = customBounce !== undefined ? customBounce : Math.max(5, 32 - boost * 48);

  return (
    <div className="relative overflow-hidden rounded-xl border border-white/[0.09] bg-black p-3.5">
      <div className="flex items-start justify-between">
        <div>
          <span className="micro-sm text-white/30">{customLabel || "Score viral"}</span>
          <div className="mt-1.5 flex items-baseline gap-1.5">
            <span className="text-glow tnum text-[30px] font-light leading-none text-white">
              <Counter value={currentScore} format={(n) => String(Math.round(n))} />
            </span>
            <span className="text-[11px] text-white/30">/ 100</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <IconFlame className={cn("h-3 w-3", color === "#10b981" ? "text-emerald-400" : "text-ember-400/80")} />
            <span className="text-[10px] text-white/55">{grade}</span>
          </div>
        </div>
        <svg viewBox="0 0 160 96" className="h-[86px] w-[142px]">
          <defs>
            <linearGradient id={`gg-${color.replace('#', '')}`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={color} />
              <stop offset="100%" stopColor={color} />
            </linearGradient>
          </defs>
          <path d="M16 84 A64 64 0 1 1 144 84" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="7" strokeLinecap="round" />
          <path
            d="M16 84 A64 64 0 1 1 144 84"
            fill="none"
            stroke={`url(#gg-${color.replace('#', '')})`}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={L}
            strokeDashoffset={L * (1 - currentScore / 100)}
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
          { l: "Hook", v: hookVal, u: "%" },
          { l: "Retención", v: retVal, u: "%" },
          { l: "Rebote", v: bounceVal, u: "%" },
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
      <div className="flex items-center gap-3 px-1">
        <span className="flex items-center gap-1">
          <span className="h-[2px] w-3 rounded-full bg-beam-300" />
          <span className="micro-sm text-white/35">Proyectada</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="h-[2px] w-3 rounded-full bg-white/20" />
          <span className="micro-sm text-white/25">Base</span>
        </span>
      </div>

      <div
        className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-black p-2"
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
      {MOMENTS.map((m) => (
        <button
          key={m.t}
          onClick={() => seek(m.t)}
          className="group flex w-full items-center gap-2.5 rounded-lg border border-white/[0.08] bg-black p-2 text-left transition-colors duration-200 hover:border-beam-400/40"
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
      {pending.map((a, i) => {
        const p = progress[a.id];
        return (
          <div
            key={a.id}
            className={cn(
              "relative overflow-hidden rounded-lg border p-2.5",
              i === 0
                ? "border-beam-400/40 bg-black"
                : "border-white/[0.08] bg-black",
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
                className="shrink-0 rounded-md border border-beam-400 bg-beam-500 px-2.5 py-1.5 text-[10px] font-medium text-white transition-colors duration-200 hover:bg-beam-400 disabled:opacity-70"
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

/* ---------- producer plan section ---------- */
function ProducerPlanSection() {
  const { producerPlan, setProducerPlan, createVideo, setRatio, flash } = useEditor();
  if (!producerPlan) return null;

  const handleApply = (autoCreate: boolean = true) => {
    if (producerPlan.recommended_format === "reel") {
      setRatio("9:16");
      const dur = producerPlan.recommended_duration_sec || 60;
      if (autoCreate) {
        createVideo(producerPlan.polished_prompt, {
          duration: dur,
          style: "shorts",
          aspect_ratio: "9:16",
        });
        flash(`Creando Reel 9:16 (${dur}s) con datos verificados...`);
      }
    } else {
      setRatio("16:9");
      const dur = producerPlan.recommended_duration_sec || 900;
      const durMin = Math.round(dur / 60);
      if (autoCreate) {
        createVideo(producerPlan.polished_prompt, {
          duration: dur,
          style: "divulgacion",
          aspect_ratio: "16:9",
        });
        flash(`Creando documental 16:9 (${durMin}m) con datos reales...`);
      }
    }
  };

  return (
    <div className="space-y-3 pb-6 animate-in fade-in duration-300">
      {/* Indicador de Aprendizaje del Canal */}
      {producerPlan.channel_learning_applied && (
        <div className="rounded-xl border border-beam-400/30 bg-beam-500/10 p-3 text-[11px] space-y-1.5">
          <div className="flex items-center gap-1.5 text-beam-200 font-medium">
            <IconSparkle className="h-3.5 w-3.5" />
            <span>Fórmula Ganadora del Canal: {producerPlan.channel_name || "Activo"}</span>
          </div>
          <div className="text-[10px] text-white/70 leading-relaxed">
            Estructura optimizada: <span className="text-white font-medium">{producerPlan.chosen_structure}</span> con gancho inicial estilo <span className="text-white font-medium">{producerPlan.chosen_hook_type}</span>.
          </div>
        </div>
      )}

      {/* 1. Medidor de retención auditada */}
      <Collapsible title="Retención Auditada" defaultOpen={true}>
        <ScoreGauge
          overrideScore={producerPlan.retention_score}
          customLabel="Retención estimada"
          customGrade="Élite · Retención > 70%"
          color="#2f5cff"
        />
        {/* Metadatos rápidos */}
        <div className="mt-2 grid grid-cols-2 gap-2 text-[10px]">
          <div className="rounded-lg border border-white/[0.08] bg-black p-2">
            <span className="micro-sm text-white/35">Formato sugerido</span>
            <div className="mt-1 font-semibold text-white/90">
              {producerPlan.recommended_format === "reel" ? "Reel 9:16 vertical" : "Documental 16:9"}
            </div>
          </div>
          <div className="rounded-lg border border-white/[0.08] bg-black p-2">
            <span className="micro-sm text-white/35">Duración óptima</span>
            <div className="mt-1 font-semibold text-white/90">
              {producerPlan.recommended_duration_sec} segundos
            </div>
          </div>
        </div>
      </Collapsible>

      {/* 2. Diagnóstico & Estrategia Anti-Abandono */}
      <Collapsible title="Diagnóstico de Retención" defaultOpen={true}>
        <div className="rounded-xl border border-white/[0.08] bg-black/60 p-3 text-[10.5px] leading-relaxed text-white/70">
          <p>{producerPlan.original_critique}</p>
        </div>
      </Collapsible>

      {/* 3. Gancho 3 Segundos */}
      <Collapsible title="Gancho Inicial (3s)" defaultOpen={true}>
        <div className="rounded-xl border border-white/[0.08] bg-black/50 p-3">
          <div className="micro-sm text-white/35 mb-1.5 flex items-center gap-1.5">
            <span className="h-1 w-1 rounded-full bg-beam-300" />
            <span>Gancho de apertura</span>
          </div>
          <p className="text-[11px] font-normal italic text-white/90 leading-relaxed">
            "{producerPlan.master_hook}"
          </p>
        </div>
      </Collapsible>

      {/* 4. 3 Datos Avalados por la Web */}
      <Collapsible title={`Datos Avalados (${producerPlan.supporting_facts?.length || 0})`} defaultOpen={true}>
        <div className="space-y-2">
          {producerPlan.supporting_facts?.map((f, idx) => (
            <div key={idx} className="rounded-xl border border-white/[0.08] bg-black p-2.5 text-[10.5px] leading-relaxed">
              <div className="text-white/85">{f.fact}</div>
              <div className="mt-1.5 flex items-center gap-1 text-[9px] text-cyan-300/80 font-mono">
                <span className="text-white/30">Fuente:</span>
                <span className="truncate">{f.source_tag}</span>
              </div>
            </div>
          ))}
        </div>
      </Collapsible>

      {/* 5. Dirección Artística */}
      <Collapsible title="Dirección de Arte y Música" defaultOpen={false}>
        <div className="space-y-2 text-[10px]">
          <div className="rounded-xl border border-white/[0.08] bg-black p-2.5">
            <div className="micro-sm text-white/35 mb-1">Atmósfera Visual</div>
            <div className="text-white/70 leading-relaxed">{producerPlan.visual_atmosphere}</div>
          </div>
          <div className="rounded-xl border border-white/[0.08] bg-black p-2.5">
            <div className="micro-sm text-white/35 mb-1">Música Recomendada</div>
            <div className="text-white/70 leading-relaxed">{producerPlan.recommended_bgm}</div>
          </div>
        </div>
      </Collapsible>

      {/* 6. Guión Maestro Pulido */}
      <Collapsible title="Guión Maestro Pulido" defaultOpen={false}>
        <div className="rounded-xl border border-white/[0.08] bg-black p-3 text-[10.5px] text-white/80 leading-relaxed font-mono">
          {producerPlan.polished_prompt}
        </div>
      </Collapsible>

      {/* 7. Barra de Acciones del Productor */}
      <div className="pt-2 flex flex-col gap-2">
        <button
          type="button"
          onClick={() => handleApply(true)}
          className="w-full flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/[0.08] hover:bg-white/[0.14] hover:border-white/25 py-2.5 text-[11px] font-medium text-white transition-all active:scale-98 cursor-pointer shadow-sm"
        >
          <IconSparkle className="h-3.5 w-3.5 text-beam-200" />
          <span>Aplicar y crear video ({producerPlan.recommended_duration_sec}s)</span>
        </button>
        <button
          type="button"
          onClick={() => setProducerPlan(null)}
          className="w-full rounded-lg border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.06] py-1.5 text-[10.5px] font-medium text-white/45 hover:text-white/80 transition-all text-center cursor-pointer"
        >
          Cerrar auditoría
        </button>
      </div>
    </div>
  );
}

/* ---------- panel ---------- */
export function MetricsPanel() {
  const {
    metrics,
    platform,
    applied,
    running,
    theaterMode,
    setTheaterMode,
    producerPlan,
    metricsPanelCollapsed,
    setMetricsPanelCollapsed,
    activeChannelId,
    setActiveChannelId,
    flash,
  } = useEditor();
  const isHidden = metricsPanelCollapsed || theaterMode;
  const pf = PLATFORMS.find((p) => p.id === platform)!;
  const [activeTab, setActiveTab] = useState<"viral" | "producer">("viral");

  const [overview, setOverview] = useState<MetricsOverviewData | null>(null);
  const [fbCorrelations, setFbCorrelations] = useState<Record<string, any>>({});
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [selectedChannelId, setSelectedChannelId] = useState<string>(activeChannelId || "UC_8-TffWIAoiUMMDfiMUm2Q");

  useEffect(() => {
    if (activeChannelId) setSelectedChannelId(activeChannelId);
  }, [activeChannelId]);

  const loadOverview = useCallback(async () => {
    try {
      const res = await fetch("/api/metrics/overview");
      if (res.ok) {
        const data = await res.json();
        setOverview(data);
      }
      fetch("/api/facebook/correlations")
        .then((r) => r.json())
        .then((data) => setFbCorrelations(data))
        .catch(() => {});
    } catch (e) {
      console.warn("No se pudo cargar métricas generales:", e);
    }
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const handleSyncYouTube = async () => {
    try {
      setIsSyncing(true);
      flash("Conectando con YouTube Data API v3...");
      const res = await fetch("/api/metrics/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel_id: selectedChannelId }),
      });
      const data = await res.json();
      if (data.success) {
        flash(`¡Métricas sincronizadas en vivo! ${data.synced_videos_count} videos actualizados.`);
        await loadOverview();
      } else {
        flash("Sincronización finalizada sin cambios nuevos.");
      }
    } catch (err: any) {
      flash(`Error al sincronizar con YouTube: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSelectChannel = (cid: string) => {
    setSelectedChannelId(cid);
    setActiveChannelId(cid);
  };

  useEffect(() => {
    if (producerPlan) {
      setActiveTab("producer");
      setMetricsPanelCollapsed(false);
    }
  }, [producerPlan, setMetricsPanelCollapsed]);

  const currentChannel = overview?.channels?.find((c) => c.channel_id === selectedChannelId) 
    || overview?.channels?.[0];

  const channelVideos = useMemo(() => {
    if (!overview?.recent_videos) return [];
    if (!currentChannel) return overview.recent_videos;
    return overview.recent_videos.filter((v) => v.channel_id === currentChannel.channel_id);
  }, [overview, currentChannel]);

  const totalViews = channelVideos.reduce((acc, v) => acc + (v.metrics?.views || 0), 0);
  const totalLikes = channelVideos.reduce((acc, v) => acc + (v.metrics?.likes || 0), 0);
  const totalComments = channelVideos.reduce((acc, v) => acc + (v.metrics?.comments || 0), 0);

  if (isHidden) {
    return (
      <aside className="hidden min-h-0 w-11 shrink-0 flex-col items-center border-l border-white/[0.08] bg-black py-3 xl:flex">
        <button
          type="button"
          onClick={() => {
            setMetricsPanelCollapsed(false);
            if (theaterMode) setTheaterMode(false);
          }}
          title="Mostrar escenario viral y auditoría de IA"
          className="grid h-8 w-8 place-items-center rounded-lg border border-white/[0.09] text-white/60 transition-colors hover:border-beam-400/50 hover:text-beam-200"
        >
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 6l-6 6 6 6" />
          </svg>
        </button>
        <span className="micro-sm mt-4 text-white/35 [writing-mode:vertical-rl]">
          {producerPlan ? "Producción IA" : "Escenario viral"}
        </span>
      </aside>
    );
  }

  return (
    <aside className="hidden min-h-0 w-[340px] shrink-0 flex-col border-l border-white/[0.08] bg-black xl:flex">
      <div className="flex items-center justify-between px-3.5 pb-2.5 pt-3.5 shrink-0 border-b border-white/[0.06]">
        {/* Pestañas de alternancia superior */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setActiveTab("viral")}
            className={cn(
              "px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all cursor-pointer",
              activeTab === "viral"
                ? "bg-white/[0.10] text-white border border-white/15"
                : "text-white/40 hover:text-white hover:bg-white/[0.04]",
            )}
          >
            Escenario viral
          </button>
          {producerPlan && (
            <button
              type="button"
              onClick={() => setActiveTab("producer")}
              className={cn(
                "px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all flex items-center gap-1.5 cursor-pointer",
                activeTab === "producer"
                  ? "bg-white/[0.10] text-white border border-white/15"
                  : "text-white/40 hover:text-white hover:bg-white/[0.04]",
              )}
            >
              <span>Producción IA</span>
              <span className="tnum text-[9px] px-1 py-0.2 rounded bg-white/[0.08] text-white/70 border border-white/10">
                {producerPlan.retention_score}
              </span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-full border border-white/[0.1] bg-black px-2 py-0.5">
            <span
              className={cn(
                "h-1 w-1 rounded-full",
                isSyncing
                  ? "bg-beam-300 anim-ping"
                  : activeTab === "viral"
                  ? (running ? "bg-beam-300 anim-ping" : "bg-signal-400")
                  : "bg-signal-400",
              )}
            />
            <span className="micro-sm text-white/45">
              {isSyncing
                ? "Sincronizando..."
                : activeTab === "viral"
                ? (running ? "Recalculando" : "YouTube en vivo")
                : "Datos web"}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setMetricsPanelCollapsed(true)}
            title="Ocultar panel"
            className="grid h-7 w-7 place-items-center rounded-lg border border-white/[0.09] text-white/50 transition-colors hover:border-beam-400/50 hover:text-beam-200 cursor-pointer"
          >
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 6l6 6-6 6" />
            </svg>
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3.5 pb-5 pt-3 space-y-3">
        {activeTab === "producer" && producerPlan ? (
          <ProducerPlanSection />
        ) : (
          <>
            {/* 1. Selector de Canal Conectado & Botón Sincronizar en Vivo */}
            <div className="rounded-xl border border-white/[0.09] bg-white/[0.02] p-2.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="micro-sm text-white/35 font-medium">CANAL CONECTADO</span>
                <button
                  type="button"
                  onClick={handleSyncYouTube}
                  disabled={isSyncing}
                  className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium bg-beam-500/15 border border-beam-400/30 text-beam-200 hover:bg-beam-500/25 transition-all cursor-pointer disabled:opacity-50"
                  title="Sincronizar métricas en tiempo real con YouTube Data API"
                >
                  <IconRefresh className={cn("h-3 w-3", isSyncing && "animate-spin")} />
                  <span>{isSyncing ? "Sincronizando..." : "Sincronizar YouTube"}</span>
                </button>
              </div>

              {/* Botones de canales */}
              <div className="grid grid-cols-2 gap-1.5">
                {[
                  {
                    id: "UC_8-TffWIAoiUMMDfiMUm2Q",
                    title: "the Deep dife",
                    tag: "Historia & Ciencia",
                  },
                  {
                    id: "UChQZ2TvHifQBrDzbZRjGDkA",
                    title: "PixelGrama",
                    tag: "Tecnología & IA",
                  },
                ].map((c) => {
                  const isSelected = (currentChannel?.channel_id || selectedChannelId) === c.id;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => handleSelectChannel(c.id)}
                      className={cn(
                        "flex flex-col text-left px-2.5 py-1.5 rounded-lg border transition-all cursor-pointer",
                        isSelected
                          ? "border-beam-400/50 bg-beam-500/10 text-white"
                          : "border-white/[0.06] bg-black hover:border-white/15 text-white/60",
                      )}
                    >
                      <span className="text-[11px] font-medium truncate">{c.title}</span>
                      <span className="text-[9px] text-white/35 truncate">{c.tag}</span>
                    </button>
                  );
                })}
              </div>

              {/* Página Hermana Facebook */}
              {(() => {
                const activeCid = currentChannel?.channel_id || selectedChannelId;
                const fb = fbCorrelations[activeCid]?.facebook_page;
                if (!fb || !fb.enabled) return null;
                return (
                  <div className="mt-2 rounded-lg border border-[#1877F2]/25 bg-[#1877F2]/[0.04] p-2 flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-5 h-5 rounded-md bg-[#1877F2]/20 border border-[#1877F2]/40 flex items-center justify-center shrink-0">
                        <svg className="w-3 h-3 fill-[#1877F2]" viewBox="0 0 24 24">
                          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                        </svg>
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[9px] text-white/40 uppercase tracking-wider font-semibold">Página Hermana Facebook</span>
                          <span className="inline-flex items-center px-1.5 py-0.2 text-[8.5px] font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded-full">
                            Auto Reels ON
                          </span>
                        </div>
                        <p className="text-[11px] font-medium text-white truncate">{fb.page_name}</p>
                      </div>
                    </div>
                    {fb.category && (
                      <span className="text-[9px] text-white/40 shrink-0 border border-white/[0.08] px-1.5 py-0.5 rounded">
                        {fb.category}
                      </span>
                    )}
                  </div>
                );
              })()}
            </div>

            {/* 2. Puntuación Real del Canal */}
            <Collapsible title="Puntuación del Canal" defaultOpen={true}>
              <ScoreGauge
                overrideScore={currentChannel?.avg_viral_score || 74}
                customLabel={currentChannel ? `Score Canal · ${currentChannel.channel_title}` : "Score viral"}
                customGrade={currentChannel ? `${currentChannel.avg_retention_pct}% Retención Promedio` : undefined}
                customRetention={currentChannel?.avg_retention_pct || 75.7}
                customHook={currentChannel?.best_hook?.avg_retention_pct || 83.4}
                customBounce={24}
              />
            </Collapsible>

            {/* 3. Métricas Reales Sincronizadas */}
            <Collapsible title="Métricas Reales de YouTube" defaultOpen={true}>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { l: "Visualizaciones", v: totalViews || metrics.views, f: compact, g: <IconEye className="h-3 w-3" /> },
                  { l: "Me gusta (Likes)", v: totalLikes, f: compact, g: <IconFlame className="h-3 w-3" /> },
                  { l: "Comentarios", v: totalComments, f: compact, g: <IconComment className="h-3 w-3" /> },
                  { l: "Videos en Canal", v: channelVideos.length || 3, f: (n: number) => String(n), g: <IconChart className="h-3 w-3" /> },
                  { l: "CTR Portada Est.", v: 14.8, f: (n: number) => `${n.toFixed(1)}%`, g: <IconSend className="h-3 w-3" /> },
                  { l: "Retención Promedio", v: currentChannel?.avg_retention_pct || 75.7, f: (n: number) => `${n.toFixed(0)}%`, g: <IconBookmark className="h-3 w-3" /> },
                ].map((s) => (
                  <div key={s.l} className="group relative overflow-hidden rounded-lg border border-white/[0.08] bg-black p-2.5 transition-colors hover:border-beam-400/40">
                    <div className="flex items-center justify-between">
                      <span className="micro-sm text-white/30">{s.l}</span>
                      <span className="text-white/20">{s.g}</span>
                    </div>
                    <div className="tnum mt-2 text-[16px] font-light leading-none text-white">
                      <Counter value={s.v} format={s.f} />
                    </div>
                  </div>
                ))}
              </div>
            </Collapsible>

            {/* 4. Cerebro del Modelo: Feedback Inteligente por Canal */}
            <Collapsible title="Aprendizaje del Modelo por Canal" defaultOpen={true}>
              <div className="space-y-2.5">
                {/* Estructura ganadora */}
                <div className="rounded-xl border border-white/[0.09] bg-black p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="micro-sm text-beam-300 font-medium">ESTRUCTURA GANADORA</span>
                    <span className="micro-sm text-signal-400 border border-signal-400/25 bg-signal-400/10 px-1.5 py-0.5 rounded">
                      {currentChannel?.best_structure?.avg_score || 82}% retención
                    </span>
                  </div>
                  <div className="text-[11.5px] font-semibold text-white/95">
                    {currentChannel?.best_structure?.name || "Revelación de Shock / Misterio Oculto"}
                  </div>
                  <p className="text-[10px] text-white/50 leading-relaxed">
                    Esta estructura maximiza la permanencia en «{currentChannel?.channel_title}» al plantear un quiebre de expectativa en los primeros 3 segundos.
                  </p>
                </div>

                {/* Gancho más efectivo */}
                <div className="rounded-xl border border-white/[0.09] bg-black p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="micro-sm text-ember-300 font-medium">GANCHO (HOOK) DE ALTA RETENCIÓN</span>
                    <span className="micro-sm text-ember-400 border border-ember-400/25 bg-ember-400/10 px-1.5 py-0.5 rounded">
                      +35% retención inicial
                    </span>
                  </div>
                  <div className="text-[11.5px] font-semibold text-white/95">
                    {currentChannel?.best_hook?.name || "Declaración de Shock / Revelación Directa"}
                  </div>
                  <p className="text-[10px] text-white/50 leading-relaxed">
                    Evita saludos o intros lentas; inicia con afirmaciones directas que activan el bucle Zeigarnik.
                  </p>
                </div>

                {/* Nota de retroalimentación activa al modelo */}
                <div className="rounded-xl border border-beam-400/30 bg-beam-500/10 p-3 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-beam-200 font-medium text-[11px]">
                    <IconBrain className="h-3.5 w-3.5 shrink-0" />
                    <span>Retroalimentación Activa al Modelo</span>
                  </div>
                  <p className="text-[10px] text-white/70 leading-relaxed">
                    El <strong className="text-white">Productor IA</strong> y el <strong className="text-white">Autopilot</strong> inyectan este aprendizaje en cada nuevo guión generado para este canal. El modelo descarta automáticamente estructuras que no retienen.
                  </p>
                </div>

                {/* Anti-patrones */}
                <div className="rounded-lg border border-white/[0.06] bg-black/60 p-2.5 text-[10px] text-white/45 space-y-1">
                  <span className="micro-sm text-ember-400/80">DESCARTADO POR EL MODELO:</span>
                  <div className="text-white/60">• Introducciones lentas sin revelación en primeros 3s</div>
                  <div className="text-white/60">• Estructuras genéricas sin tarjetas sólidas de datos</div>
                </div>
              </div>
            </Collapsible>

            {/* 5. Videos Publicados y Rendimiento Real */}
            <Collapsible title={`Videos en Canal (${channelVideos.length})`} defaultOpen={true}>
              <div className="space-y-1.5">
                {channelVideos.length === 0 ? (
                  <div className="p-3 text-center text-[10.5px] text-white/40 border border-white/[0.06] rounded-lg">
                    No hay videos sincronizados aún para este canal. Haz clic en "Sincronizar YouTube".
                  </div>
                ) : (
                  channelVideos.map((v) => (
                    <div
                      key={v.video_id}
                      className="group flex flex-col gap-1.5 rounded-lg border border-white/[0.08] bg-black p-2.5 transition-colors hover:border-beam-400/40"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-[11px] font-medium text-white/90 line-clamp-1 leading-snug">
                          {v.title}
                        </span>
                        <a
                          href={`https://youtu.be/${v.video_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="shrink-0 text-beam-300 hover:text-beam-100 p-0.5"
                          title="Ver en YouTube"
                        >
                          <IconExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-white/40 pt-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-white/70 font-medium">
                            {v.metrics?.views ?? 0} {v.metrics?.views === 1 ? "vista" : "vistas"}
                          </span>
                          <span>•</span>
                          <span>{v.metrics?.likes ?? 0} likes</span>
                        </div>
                        <span className="micro-sm text-beam-300/80 bg-beam-500/10 border border-beam-400/20 px-1.5 py-0.2 rounded">
                          {v.structure_type === "revelacion_shock"
                            ? "Revelación"
                            : v.structure_type === "comparativa_versus"
                            ? "Comparativa"
                            : "Problema/Solución"}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Collapsible>

            {/* Curva de retención */}
            <Collapsible title="Curva de retención proyectada" defaultOpen={false}>
              <RetentionChart />
            </Collapsible>

            {/* Momentos clave */}
            <Collapsible title="Momentos clave" defaultOpen={false}>
              <Moments />
            </Collapsible>

            {/* Audiencia y horarios */}
            <Collapsible title="Audiencia y horarios" defaultOpen={false}>
              <Audience />
            </Collapsible>

            {/* Siguiente acción óptima */}
            <Collapsible title="Siguiente acción óptima" defaultOpen={false}>
              <NextActions />
            </Collapsible>

            {/* Publicación sugerida */}
            <Collapsible title="Publicación sugerida" defaultOpen={false}>
              <div className="rounded-lg border border-white/[0.08] bg-black p-3">
                <div className="flex items-center justify-between">
                  <span className="micro-sm text-white/30">Mejor ventana</span>
                  <span className="micro-sm text-beam-200/80">{pf.peak}</span>
                </div>
                <p className="mt-2 text-[10px] leading-relaxed text-white/35">
                  Ventana óptima detectada con {applied.length} optimizaciones aplicadas.
                  Retención media estimada {Math.round(metrics.avg * 100)} %.
                </p>
              </div>
            </Collapsible>
          </>
        )}
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

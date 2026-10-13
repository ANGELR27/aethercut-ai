import { useRef, useState } from "react";
import { DURATION, MOMENTS, TRACKS, type Clip, type TrackId } from "@/lib/data";
import { useEditor } from "@/lib/store";
import { cn } from "@/utils/cn";
import { Hairline, IconButton } from "./ui";
import {
  IconChevron,
  IconLock,
  IconMagnet,
  IconPlus,
  IconSparkle,
  IconVolume,
} from "./Icons";

const TRACK_H: Record<TrackId, number> = { v2: 34, v1: 58, t1: 26, a1: 42 };

const KIND_STYLE: Record<Clip["kind"], string> = {
  scene: "border-white/[0.12] bg-gradient-to-b from-abyss-700/80 to-abyss-900/90",
  broll: "border-beam-300/25 bg-gradient-to-b from-beam-500/22 to-abyss-800/80",
  caption: "border-signal-400/20 bg-gradient-to-b from-signal-400/14 to-abyss-900/70",
  music: "border-white/[0.09] bg-gradient-to-b from-abyss-600/70 to-ink-900/80",
  voice: "border-beam-400/25 bg-gradient-to-b from-beam-500/14 to-abyss-800/70",
  fx: "border-white/10 bg-white/[0.05]",
};

function wave(seed: number, n: number) {
  return Array.from({ length: n }, (_, i) => {
    const a = Math.abs(Math.sin(i * 0.42 + seed) * 0.6 + Math.sin(i * 0.17 + seed * 2) * 0.4);
    return 0.18 + a * 0.8;
  });
}

export function Timeline() {
  const {
    clips,
    time,
    duration,
    seek,
    selected,
    select,
    updateClip,
    pxPerSec,
    setPxPerSec,
  } = useEditor();
  const safeDuration = duration || DURATION;
  const [snap, setSnap] = useState(true);
  const [hover, setHover] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const width = safeDuration * pxPerSec;

  const snapVal = (v: number) => (snap ? Math.round(v * 4) / 4 : v);

  const dragClip = (e: React.PointerEvent, clip: Clip, mode: "move" | "start" | "end") => {
    e.stopPropagation();
    select(clip.id);
    const x0 = e.clientX;
    const s0 = clip.start;
    const d0 = clip.duration;
    const onMove = (ev: PointerEvent) => {
      const dt = (ev.clientX - x0) / pxPerSec;
      if (mode === "move") {
        updateClip(clip.id, { start: Math.max(0, snapVal(s0 + dt)) });
      } else if (mode === "end") {
        updateClip(clip.id, { duration: Math.max(0.5, snapVal(d0 + dt)) });
      } else {
        const ns = Math.max(0, snapVal(s0 + dt));
        updateClip(clip.id, { start: ns, duration: Math.max(0.5, d0 + (s0 - ns)) });
      }
    };
    const up = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", up);
  };

  const scrub = (e: React.PointerEvent) => {
    const el = scrollRef.current;
    if (!el) return;
    const move = (cx: number) => {
      const r = el.getBoundingClientRect();
      seek(((cx - r.left + el.scrollLeft) / pxPerSec));
    };
    move(e.clientX);
    const onMove = (ev: PointerEvent) => move(ev.clientX);
    const up = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", up);
  };

  const ticks = Array.from({ length: Math.ceil(safeDuration) + 1 }, (_, i) => i);
  const step = pxPerSec < 26 ? 4 : pxPerSec < 46 ? 2 : 1;

  return (
    <section className="glass-deep relative z-20 flex h-[268px] shrink-0 flex-col rounded-none border-x-0 border-b-0">
      {/* header */}
      <div className="flex h-10 shrink-0 items-center gap-3 px-3">
        <span className="serif-display text-[15px] leading-none text-white">Línea de tiempo</span>
        <span className="micro-sm text-white/25">{Math.round(safeDuration)} s · 24 fps · 4 pistas</span>
        <div className="flex-1" />
        <IconButton size="sm" active={snap} title="Ajuste magnético" onClick={() => setSnap(!snap)}>
          <IconMagnet className="h-3.5 w-3.5" />
        </IconButton>
        <div className="flex items-center gap-1.5 rounded-xl border border-white/[0.06] bg-black/40 px-2 py-1">
          <button
            onClick={() => setPxPerSec(Math.max(18, pxPerSec - 8))}
            className="text-[13px] leading-none text-white/35 transition-colors hover:text-white"
          >
            −
          </button>
          <span className="micro-sm w-9 text-center text-white/45">Zoom {pxPerSec}</span>
          <button
            onClick={() => setPxPerSec(Math.min(90, pxPerSec + 8))}
            className="text-[13px] leading-none text-white/35 transition-colors hover:text-white"
          >
            +
          </button>
        </div>
        <IconButton size="sm" title="Añadir pista">
          <IconPlus className="h-3.5 w-3.5" />
        </IconButton>
      </div>
      <Hairline />

      {/* body */}
      <div className="flex min-h-0 flex-1">
        {/* track heads */}
        <div className="flex w-[112px] shrink-0 flex-col border-r border-white/[0.05] bg-black/25">
          <div className="h-7 shrink-0 border-b border-white/[0.05]" />
          {TRACKS.map((t) => (
            <div
              key={t.id}
              className="flex items-center gap-2 border-b border-white/[0.04] px-2.5"
              style={{ height: TRACK_H[t.id] }}
            >
              <span className="micro-sm text-beam-200/60">{t.tag}</span>
              <span className="micro-sm truncate text-white/40">{t.name}</span>
              <div className="ml-auto flex items-center gap-1.5 text-white/20">
                {t.id === "a1" ? (
                  <IconVolume className="h-3 w-3" />
                ) : (
                  <IconLock className="h-3 w-3 opacity-40" />
                )}
              </div>
            </div>
          ))}
          <div className="flex min-h-0 flex-1 items-end px-2.5 pb-2">
            <span className="micro-sm text-white/15">Auto-scroll activo</span>
          </div>
        </div>

        {/* lanes */}
        <div
          ref={scrollRef}
          className="relative min-h-0 flex-1 overflow-x-auto overflow-y-hidden"
        >
          <div className="relative" style={{ width }}>
            {/* ruler */}
            <div
              className="relative h-7 cursor-ew-resize border-b border-white/[0.05] bg-black/30"
              onPointerDown={scrub}
              onPointerMove={(e) => {
                const r = e.currentTarget.getBoundingClientRect();
                setHover(Math.max(0, Math.min(safeDuration, (e.clientX - r.left) / pxPerSec)));
              }}
              onPointerLeave={() => setHover(null)}
            >
              {ticks.map((i) =>
                i % step === 0 ? (
                  <div
                    key={i}
                    className="absolute top-0 h-full"
                    style={{ left: i * pxPerSec }}
                  >
                    <span className="absolute left-0 top-0 h-2 w-px bg-white/15" />
                    <span className="tnum absolute left-1 top-2 text-[9px] text-white/25">
                      {i}s
                    </span>
                    <span className="absolute bottom-0 left-0 h-2.5 w-px bg-white/[0.07]" />
                  </div>
                ) : (
                  <span
                    key={i}
                    className="absolute bottom-0 h-1.5 w-px bg-white/[0.07]"
                    style={{ left: i * pxPerSec }}
                  />
                ),
              )}
              {/* key moments */}
              {MOMENTS.map((m) => (
                <div
                  key={m.t}
                  className="group absolute bottom-[3px] z-10 -translate-x-1/2"
                  style={{ left: m.t * pxPerSec }}
                >
                  <span
                    className={cn(
                      "block h-1.5 w-1.5 rounded-full ring-2 ring-black/40",
                      m.kind === "risk" ? "bg-ember-400" : "bg-signal-400",
                    )}
                  />
                  <span className="pointer-events-none absolute bottom-4 left-1/2 z-30 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-white/10 bg-ink-900/95 px-2 py-1 text-[9px] text-white/70 shadow-xl group-hover:block">
                    {m.label} · {m.t}s
                  </span>
                </div>
              ))}
              {hover !== null && (
                <span
                  className="tnum pointer-events-none absolute top-2 text-[9px] text-beam-200/70"
                  style={{ left: hover * pxPerSec + 4 }}
                >
                  {hover.toFixed(1)}s
                </span>
              )}
            </div>

            {/* lanes */}
            {TRACKS.map((t) => (
              <div
                key={t.id}
                className="relative border-b border-white/[0.04]"
                style={{ height: TRACK_H[t.id] }}
                onPointerDown={() => select(null)}
              >
                {clips
                  .filter((c) => c.track === t.id)
                  .map((c) => {
                    const isSel = selected === c.id;
                    const w = c.duration * pxPerSec;
                    return (
                      <div
                        key={c.id}
                        onPointerDown={(e) => dragClip(e, c, "move")}
                        className={cn(
                          "group absolute top-[3px] cursor-grab overflow-hidden rounded-[7px] border transition-shadow duration-200 active:cursor-grabbing",
                          KIND_STYLE[c.kind],
                          isSel
                            ? "shadow-[0_0_0_1px_rgba(126,163,255,0.75),0_10px_28px_-12px_rgba(47,92,255,0.9)]"
                            : "hover:border-white/25",
                        )}
                        style={{ left: c.start * pxPerSec, width: Math.max(14, w), height: TRACK_H[t.id] - 7 }}
                      >
                        {/* video thumbnail strip */}
                        {c.frame && (
                          <div className="absolute inset-0 flex">
                            {Array.from({ length: Math.max(1, Math.ceil(w / 44)) }).map((_, i) => (
                              <img
                                key={i}
                                src={c.frame}
                                alt=""
                                className="no-drag h-full w-[44px] shrink-0 object-cover opacity-45"
                                style={{ filter: "saturate(0.7)" }}
                              />
                            ))}
                          </div>
                        )}
                        {/* waveform for audio */}
                        {(c.kind === "music" || c.kind === "voice") && (
                          <div className="absolute inset-x-1 bottom-0 flex h-[62%] items-end gap-[1.5px] opacity-70">
                            {wave(c.start + c.duration, Math.max(6, Math.floor(w / 3))).map((h, i) => (
                              <span
                                key={i}
                                className="flex-1 rounded-[1px] bg-gradient-to-t from-beam-500/40 to-beam-200/90"
                                style={{ height: `${h * 100}%` }}
                              />
                            ))}
                          </div>
                        )}
                        {c.kind === "caption" && (
                          <div className="absolute inset-0 flex items-center gap-[2px] px-2 opacity-60">
                            {Array.from({ length: Math.max(3, Math.floor(w / 9)) }).map((_, i) => (
                              <span
                                key={i}
                                className="h-[3px] rounded-full bg-signal-400/70"
                                style={{ width: 3 + ((i * 7) % 9) }}
                              />
                            ))}
                          </div>
                        )}

                        <div className="relative flex h-full items-center gap-1.5 px-2">
                          {c.ai && <IconSparkle className="h-3 w-3 shrink-0 text-beam-200/80" />}
                          <span className="truncate text-[10px] font-medium tracking-wide text-white/85">
                            {c.label}
                          </span>
                          {w > 120 && (
                            <span className="tnum ml-auto shrink-0 text-[9px] text-white/40">
                              {c.duration.toFixed(1)}s
                            </span>
                          )}
                        </div>

                        {/* trim handles */}
                        <span
                          onPointerDown={(e) => dragClip(e, c, "start")}
                          className="absolute inset-y-0 left-0 w-1.5 cursor-w-resize bg-gradient-to-r from-white/25 to-transparent opacity-0 transition-opacity group-hover:opacity-100"
                        />
                        <span
                          onPointerDown={(e) => dragClip(e, c, "end")}
                          className="absolute inset-y-0 right-0 w-1.5 cursor-e-resize bg-gradient-to-l from-white/25 to-transparent opacity-0 transition-opacity group-hover:opacity-100"
                        />
                      </div>
                    );
                  })}
              </div>
            ))}

            {/* playhead */}
            <div
              className="pointer-events-none absolute top-0 bottom-0 z-20 w-px bg-beam-300/90 shadow-[0_0_14px_2px_rgba(79,123,255,0.55)]"
              style={{ left: time * pxPerSec }}
            >
              <span className="absolute -left-[5px] -top-[1px] h-2.5 w-[11px] rounded-b-sm bg-beam-300" />
            </div>
          </div>
        </div>
      </div>

      {/* footer */}
      <div className="flex h-8 shrink-0 items-center gap-3 border-t border-white/[0.05] px-3">
        <span className="micro-sm text-white/25">
          {selected ? `${clips.find((c) => c.id === selected)?.label} · seleccionado` : "Sin selección"}
        </span>
        <div className="flex-1" />
        <span className="micro-sm hidden text-white/20 sm:block">
          Espacio reproducir · ← → fotograma · J/L velocidad
        </span>
        <IconChevron className="h-3 w-3 text-white/15" />
      </div>
    </section>
  );
}

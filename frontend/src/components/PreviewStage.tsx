import { useEditor } from "@/lib/store";
import { DURATION, captionAt, sceneAt, timecode, type Ratio } from "@/lib/data";
import { cn } from "@/utils/cn";
import { Hairline, IconButton, SectionLabel } from "./ui";
import {
  IconChart,
  IconCrop,
  IconEnd,
  IconEye,
  IconGrid,
  IconStart,
  IconLoop,
  IconMagnet,
  IconPause,
  IconPlay,
  IconScissors,
  IconSparkle,
  IconType,
  IconVolume,
} from "./Icons";

const RATIO_VALUE: Record<Ratio, number> = {
  "9:16": 9 / 16,
  "4:5": 4 / 5,
  "1:1": 1,
  "16:9": 16 / 9,
};

const RATIOS: Ratio[] = ["9:16", "4:5", "1:1", "16:9"];

function Frame() {
  const { time, ratio, overlays, running, previewVideoUrl, videoRef, duration } = useEditor();
  const scene = sceneAt(time);
  const starts = [0, 11.5, 23.5];
  const idx = starts.findIndex((s) => time >= s);
  const local = Math.min(1, Math.max(0, (time - starts[idx]) / (duration - starts[idx] || 1)));
  const cap = overlays.captions ? captionAt(time) : null;

  const kb = [
    `scale(${1.05 + local * 0.1}) translate(${(1 - local) * 1.4}%, ${local * -1.2}%)`,
    `scale(${1.08 + local * 0.06}) translate(${local * -1.8}%, ${(1 - local) * 1}%)`,
    `scale(${1.04 + local * 0.12}) translate(${local * 1.2}%, ${local * 1.4}%)`,
  ][idx];

  return (
    <div
      className="relative overflow-hidden rounded-[20px] border border-white/[0.09] bg-black shadow-[0_60px_120px_-50px_rgba(0,0,0,1),0_0_120px_-60px_rgba(47,92,255,0.9)]"
      style={{ aspectRatio: String(RATIO_VALUE[ratio]) }}
    >
      {/* footage */}
      {previewVideoUrl ? (
        <video
          ref={videoRef}
          src={previewVideoUrl}
          playsInline
          className="no-drag absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        [
          { f: 0, s: 0 },
          { f: 1, s: 11.5 },
          { f: 2, s: 23.5 },
        ].map((sc) => (
          <img
            key={sc.f}
            src={sceneAt(sc.s + 0.1).frame}
            alt=""
            className="no-drag absolute inset-0 h-full w-full object-cover transition-opacity duration-700"
            style={{ opacity: idx === sc.f ? 1 : 0, transform: idx === sc.f ? kb : "scale(1.05)" }}
          />
        ))
      )}

      {/* grade + bloom */}
      <div className="pointer-events-none absolute inset-0" style={{ background: scene.tint }} />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_80%_at_50%_10%,transparent_35%,rgba(0,0,0,0.55)_100%)]" />
      <div className="pointer-events-none absolute inset-0 film-grain opacity-[0.09] mix-blend-overlay" />
      <div className="pointer-events-none absolute inset-0 scan-lines opacity-25" />
      {running && (
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="sweep-line h-[35%] w-full bg-gradient-to-b from-transparent via-beam-300/10 to-transparent" />
        </div>
      )}

      {/* thirds grid */}
      {overlays.grid && (
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute inset-y-0 left-1/3 w-px bg-white/15" />
          <div className="absolute inset-y-0 left-2/3 w-px bg-white/15" />
          <div className="absolute inset-x-0 top-1/3 h-px bg-white/15" />
          <div className="absolute inset-x-0 top-2/3 h-px bg-white/15" />
        </div>
      )}

      {/* safe areas */}
      {overlays.safe && (
        <>
          <div className="pointer-events-none absolute inset-[6%] rounded-[10px] border border-dashed border-white/12" />
          <div className="pointer-events-none absolute bottom-[6%] right-[6%] top-[6%] w-[13%] rounded-[8px] border border-dashed border-beam-300/20">
            <span className="micro-sm absolute -left-1 top-0 origin-top-left -rotate-90 whitespace-nowrap text-beam-200/40">
              UI
            </span>
          </div>
          <div className="pointer-events-none absolute inset-x-[6%] bottom-[6%] h-[12%] rounded-[8px] border border-dashed border-beam-300/20" />
        </>
      )}

      {/* subject tracking */}
      {overlays.tracking && (
        <div
          className="pointer-events-none absolute h-[34%] w-[52%] transition-all duration-1000 ease-linear"
          style={{
            left: `${26 + Math.sin(time / 3.4) * 4}%`,
            top: `${20 + Math.cos(time / 4.1) * 2.5}%`,
          }}
        >
          <div className="relative h-full w-full">
            {[
              "left-0 top-0 border-l border-t",
              "right-0 top-0 border-r border-t",
              "left-0 bottom-0 border-l border-b",
              "right-0 bottom-0 border-r border-b",
            ].map((c) => (
              <span key={c} className={cn("absolute h-4 w-4 border-beam-300/70", c)} />
            ))}
            <span className="micro-sm absolute -top-5 left-0 whitespace-nowrap bg-black/40 px-1 py-0.5 text-beam-200/80 backdrop-blur-sm">
              Sujeto 98%
            </span>
          </div>
        </div>
      )}

      {/* kinetic captions */}
      {cap && (
        <div className="absolute inset-x-[8%] bottom-[11%]">
          <p
            className={cn(
              "text-center text-[clamp(13px,4.4cqh,26px)] font-semibold uppercase leading-[1.15] tracking-tight",
              cap.hot ? "text-white" : "text-white/85",
            )}
            style={{ textShadow: "0 2px 18px rgba(0,0,0,0.75)" }}
          >
            {cap.words.map((w, i) => (
              <span
                key={i}
                className={cn(
                  "transition-all duration-200",
                  i === cap.index
                    ? "text-beam-200 [text-shadow:0_0_24px_rgba(79,123,255,0.95)]"
                    : "opacity-55",
                )}
              >
                {w}{" "}
              </span>
            ))}
          </p>
          <div className="mx-auto mt-2 h-px w-10 bg-beam-300/60" />
        </div>
      )}

      {/* top HUD */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between p-2.5">
        <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-black/45 px-2 py-1 backdrop-blur-md">
          <span className="h-1 w-1 rounded-full bg-ember-400 anim-ping" />
          <span className="micro-sm text-white/70">En vivo</span>
        </div>
        <span className="tnum rounded-full border border-white/10 bg-black/45 px-2 py-1 text-[10px] text-white/70 backdrop-blur-md">
          {timecode(time)}
        </span>
      </div>

      {/* bottom HUD */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between p-2.5">
        <span className="micro-sm text-white/45">{scene.name}</span>
        <span className="micro-sm text-white/35">{ratio} · 4K</span>
      </div>

      {running && (
        <div className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-2 rounded-full border border-beam-300/25 bg-black/50 px-3 py-1.5 backdrop-blur-md">
          <IconSparkle className="h-3.5 w-3.5 text-beam-200" />
          <span className="micro-sm text-beam-100/90">IA recalculando máster</span>
        </div>
      )}
    </div>
  );
}

function Scopes() {
  const { time, overlays } = useEditor();
  const hist = Array.from({ length: 26 }, (_, i) => {
    const v = Math.abs(Math.sin(i * 0.55 + Math.floor(time * 1.6) * 0.4) * 0.7 + 0.25);
    return 0.25 + v * 0.7;
  });
  const l = 0.4 + Math.abs(Math.sin(time * 2.6)) * 0.55;
  const r = 0.35 + Math.abs(Math.cos(time * 2.2)) * 0.55;

  if (!overlays.scopes) return null;

  return (
    <div className="glass-soft flex w-[132px] shrink-0 flex-col gap-4 rounded-none border-y-0 border-r-0 p-3">
      <div className="space-y-2">
        <SectionLabel>Scopes</SectionLabel>
        <div className="flex h-16 items-end gap-[2px] rounded-lg border border-white/[0.06] bg-black/40 p-1.5">
          {hist.map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-[1px] bg-gradient-to-t from-beam-500/30 to-beam-200/80"
              style={{ height: `${h * 100}%` }}
            />
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <SectionLabel>Audio</SectionLabel>
        {[
          { k: "L", v: l },
          { k: "R", v: r },
        ].map((ch) => (
          <div key={ch.k} className="flex items-center gap-2">
            <span className="micro-sm w-2 text-white/30">{ch.k}</span>
            <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-beam-400 to-signal-400"
                style={{ width: `${ch.v * 100}%` }}
              />
            </div>
            <span className="tnum w-6 text-right text-[8.5px] text-white/35">
              {Math.round(ch.v * -6)}
            </span>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <SectionLabel>Detecciones</SectionLabel>
        {[
          { l: "Rostro", v: 98 },
          { l: "Manos", v: 84 },
          { l: "Texto", v: 76 },
          { l: "Producto", v: 61 },
        ].map((d) => (
          <div key={d.l} className="space-y-1">
            <div className="flex justify-between">
              <span className="text-[9.5px] text-white/50">{d.l}</span>
              <span className="tnum text-[9px] text-white/30">{d.v}%</span>
            </div>
            <div className="h-[2px] w-full overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-abyss-600 to-beam-300"
                style={{ width: `${d.v}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PreviewStage() {
  const { ratio, setRatio, overlays, toggleOverlay, playing, toggle } = useEditor();

  return (
    <div className="relative flex min-h-0 flex-1">
      {/* ambient */}
      <div className="pointer-events-none absolute inset-0 grid-lines opacity-60" />
      <div className="pointer-events-none absolute -left-24 top-0 h-72 w-72 rounded-full bg-beam-500/12 blur-[110px] anim-breathe" />
      <div className="pointer-events-none absolute bottom-0 right-10 h-64 w-64 rounded-full bg-abyss-600/50 blur-[110px]" />

      {/* stage */}
      <div
        className="relative grid min-h-0 flex-1 place-items-center overflow-hidden p-5 sm:p-8"
        style={{ containerType: "size" }}
      >
        <div
          className="relative"
          style={{ width: `min(100cqw - 2rem, calc((100cqh - 2.5rem) * ${RATIO_VALUE[ratio]}))` }}
        >
          {/* bleed glow */}
          <div className="pointer-events-none absolute -inset-8 -z-10 overflow-hidden rounded-[32px]">
            <div className="absolute inset-0 bg-beam-500/10 blur-3xl" />
          </div>
          <Frame />
          <div
            className={cn(
              "absolute -bottom-6 left-1/2 -translate-x-1/2 whitespace-nowrap transition-opacity duration-500",
              playing ? "opacity-100" : "opacity-0",
            )}
          >
            <span className="micro-sm text-white/20">Renderizado local · 24 fps · latencia 8 ms</span>
          </div>
        </div>

        {/* floating tools */}
        <div className="absolute bottom-4 left-4 flex flex-col gap-1.5">
          <IconButton
            size="sm"
            title="Relación de aspecto"
            active={ratio !== "9:16"}
            onClick={() => setRatio(RATIOS[(RATIOS.indexOf(ratio) + 1) % RATIOS.length])}
          >
            <IconCrop className="h-3.5 w-3.5" />
          </IconButton>
          <IconButton size="sm" title="Reencuadre automático" active>
            <IconMagnet className="h-3.5 w-3.5" />
          </IconButton>
          <IconButton size="sm" title="Cortar en el cursor" onClick={() => {}}>
            <IconScissors className="h-3.5 w-3.5" />
          </IconButton>
          <IconButton
            size="sm"
            title="Scopes y detecciones"
            active={overlays.scopes}
            onClick={() => toggleOverlay("scopes")}
          >
            <IconChart className="h-3.5 w-3.5" />
          </IconButton>
        </div>

        <div className="absolute bottom-4 right-4 flex flex-col items-end gap-1.5">
          <div className="glass-soft flex overflow-hidden rounded-xl">
            {RATIOS.map((r) => (
              <button
                key={r}
                onClick={() => setRatio(r)}
                className={cn(
                  "px-2 py-1.5 text-[9.5px] font-medium tracking-wider transition-all",
                  ratio === r ? "bg-white/[0.1] text-white" : "text-white/30 hover:text-white/70",
                )}
              >
                {r}
              </button>
            ))}
          </div>
          <div className="flex gap-1.5">
            <IconButton
              size="sm"
              title="Subtítulos"
              active={overlays.captions}
              onClick={() => toggleOverlay("captions")}
            >
              <IconType className="h-3.5 w-3.5" />
            </IconButton>
            <IconButton
              size="sm"
              title="Zonas seguras"
              active={overlays.safe}
              onClick={() => toggleOverlay("safe")}
            >
              <IconEye className="h-3.5 w-3.5" />
            </IconButton>
            <IconButton
              size="sm"
              title="Rejilla"
              active={overlays.grid}
              onClick={() => toggleOverlay("grid")}
            >
              <IconGrid className="h-3.5 w-3.5" />
            </IconButton>
          </div>
        </div>

        {/* big play affordance */}
        <button
          onClick={toggle}
          className={cn(
            "absolute left-1/2 top-1/2 grid h-16 w-16 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-white/10 bg-black/40 text-white/80 backdrop-blur-md transition-all duration-500",
            playing ? "pointer-events-none scale-75 opacity-0" : "opacity-100 hover:scale-105",
          )}
        >
          <IconPlay className="h-6 w-6" />
        </button>
      </div>

      <Scopes />
      <Hairline className="absolute inset-x-0 bottom-0" />
    </div>
  );
}

export function Transport() {
  const { playing, toggle, seek, time, duration, rate, setRate, loop, setLoop } = useEditor();
  const safeDuration = duration || DURATION;
  const pct = (time / safeDuration) * 100;

  return (
    <div className="glass-deep relative z-20 flex h-[52px] shrink-0 items-center gap-3 border-x-0 border-b-0 px-3 sm:h-[58px]">
      <div className="flex items-center gap-1">
        <IconButton size="sm" title="Inicio" onClick={() => seek(0)}>
          <IconStart className="h-3.5 w-3.5" />
        </IconButton>
        <IconButton size="sm" title="Final" onClick={() => seek(safeDuration - 0.05)}>
          <IconEnd className="h-3.5 w-3.5" />
        </IconButton>
        <IconButton title="Anterior corte" size="sm" onClick={() => seek(Math.max(0, time - 11.5))}>
          <IconScissors className="h-3.5 w-3.5" />
        </IconButton>
        <button
          onClick={toggle}
          className="grid h-10 w-10 place-items-center rounded-xl border border-white/12 bg-gradient-to-b from-white/[0.14] to-white/[0.03] text-white shadow-[0_1px_0_0_rgba(255,255,255,0.2)_inset,0_10px_26px_-14px_rgba(47,92,255,1)] transition-all duration-300 hover:border-beam-300/40 hover:from-beam-500/25"
        >
          {playing ? <IconPause className="h-4 w-4" /> : <IconPlay className="h-4 w-4" />}
        </button>
        <IconButton
          size="sm"
          title="Bucle"
          active={loop}
          onClick={() => setLoop(!loop)}
        >
          <IconLoop className="h-3.5 w-3.5" />
        </IconButton>
        <IconButton size="sm" title="Silencio">
          <IconVolume className="h-3.5 w-3.5" />
        </IconButton>
      </div>

      {/* scrub */}
      <div
        className="group relative h-8 flex-1 cursor-pointer"
        onPointerDown={(e) => {
          const el = e.currentTarget;
          const move = (cx: number) => {
            const r = el.getBoundingClientRect();
            seek(((cx - r.left) / r.width) * safeDuration);
          };
          const onMove = (ev: PointerEvent) => move(ev.clientX);
          move(e.clientX);
          const up = () => {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", up);
          };
          window.addEventListener("pointermove", onMove);
          window.addEventListener("pointerup", up);
        }}
      >
        <div className="absolute inset-x-0 top-1/2 h-[3px] -translate-y-1/2 overflow-hidden rounded-full bg-white/[0.07]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-abyss-600 via-beam-500 to-beam-300"
            style={{ width: `${pct}%` }}
          />
        </div>
        {[11.5, 23.5].map((t) => (
          <span
            key={t}
            className="absolute top-1/2 h-2.5 w-[2px] -translate-y-1/2 rounded-full bg-white/25"
            style={{ left: `${(t / safeDuration) * 100}%` }}
          />
        ))}
        <span
          className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/60 bg-white shadow-[0_0_16px_3px_rgba(79,123,255,0.65)] transition-transform group-hover:scale-110"
          style={{ left: `${pct}%` }}
        />
      </div>

      <div className="hidden items-baseline gap-1 sm:flex">
        <span className="tnum text-[12px] font-light text-white">{timecode(time)}</span>
        <span className="tnum text-[10px] text-white/25">/ {timecode(safeDuration)}</span>
      </div>

      <div className="hidden items-center gap-0.5 rounded-xl border border-white/[0.06] bg-black/40 p-0.5 md:flex">
        {[0.25, 0.5, 1, 2].map((r) => (
          <button
            key={r}
            onClick={() => setRate(r)}
            className={cn(
              "rounded-[9px] px-2 py-1 text-[10px] font-medium transition-all",
              rate === r ? "bg-white/[0.1] text-white" : "text-white/30 hover:text-white/65",
            )}
          >
            {r}×
          </button>
        ))}
      </div>
    </div>
  );
}

import { useMemo, useEffect } from "react";
import { useEditor } from "@/lib/store";
import { CAPTIONS, DURATION, captionAt, sceneAt, timecode, type Ratio } from "@/lib/data";
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
  const {
    time,
    ratio,
    overlays,
    running,
    previewVideoUrl,
    videoRef,
    duration,
    captions,
    subtitleStyle,
    subtitleFont,
    isMuted,
    setDuration,
    setPlaying,
    loop,
    toggle,
  } = useEditor();

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.volume = 1.0;
      videoRef.current.muted = isMuted;
    }
  }, [isMuted, previewVideoUrl, videoRef]);
  const scene = sceneAt(time);
  const starts = [0, 11.5, 23.5];
  const idx = starts.findIndex((s) => time >= s);
  const local = Math.min(1, Math.max(0, (time - starts[idx]) / (duration - starts[idx] || 1)));

  const cap = useMemo(() => {
    if (!overlays.captions) return null;
    const list = captions && captions.length > 0 ? captions : CAPTIONS;
    const c = list.find((x) => time >= x.start && time <= x.end);
    if (!c) return null;

    const rawWords = c.text.trim().split(/\s+/).filter(Boolean);
    if (rawWords.length === 0) return null;

    const span = Math.max(0.1, c.end - c.start);

    // Ponderación fonética por longitud de caracteres y pausas de puntuación para sincronía precisa con la voz
    const weights = rawWords.map((w) => {
      const letters = w.replace(/[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑüÜ]/g, "").length;
      let wt = Math.max(1.2, letters);
      if (/[,\-;:–—]/.test(w)) wt += 1.8;
      if (/[.!?]/.test(w)) wt += 2.6;
      return wt;
    });

    const totalWeight = weights.reduce((a, b) => a + b, 0) || 1;

    let currTime = c.start;
    const timedWords = rawWords.map((w, idx) => {
      const wordDur = (weights[idx] / totalWeight) * span;
      const item = {
        word: w,
        start: currTime,
        end: currTime + wordDur,
        globalIndex: idx,
      };
      currTime += wordDur;
      return item;
    });

    // Subdividir en fragmentos cortos de 2 a 4 palabras para que los subtítulos jamás ocupen más de 1 o 2 líneas
    const chunks: { words: typeof timedWords; start: number; end: number }[] = [];
    let curChunk: typeof timedWords = [];

    for (let i = 0; i < timedWords.length; i++) {
      curChunk.push(timedWords[i]);
      const hasPunct = /[.,!?;:]/.test(timedWords[i].word);
      const remaining = timedWords.length - (i + 1);
      const shouldBreak =
        curChunk.length >= 4 ||
        (curChunk.length >= 3 && remaining >= 2) ||
        (curChunk.length >= 2 && hasPunct && remaining !== 1);

      if (shouldBreak) {
        chunks.push({
          words: curChunk,
          start: curChunk[0].start,
          end: curChunk[curChunk.length - 1].end,
        });
        curChunk = [];
      }
    }

    if (curChunk.length > 0) {
      if (curChunk.length === 1 && chunks.length > 0 && chunks[chunks.length - 1].words.length <= 3) {
        chunks[chunks.length - 1].words.push(...curChunk);
        chunks[chunks.length - 1].end = curChunk[curChunk.length - 1].end;
      } else {
        chunks.push({
          words: curChunk,
          start: curChunk[0].start,
          end: curChunk[curChunk.length - 1].end,
        });
      }
    }

    // Ubicar el fragmento activo según el tiempo actual
    let activeChunk = chunks.find((ch) => time >= ch.start && time < ch.end);
    if (!activeChunk) {
      activeChunk = time >= c.end ? chunks[chunks.length - 1] : chunks[0];
    }

    // Ubicar palabra activa dentro del fragmento
    let activeIdx = activeChunk.words.findIndex((w) => time >= w.start && time < w.end);
    if (activeIdx === -1) {
      activeIdx = time >= activeChunk.end ? activeChunk.words.length - 1 : 0;
    }

    return {
      chunk: activeChunk,
      words: activeChunk.words,
      activeIdx,
      hot: c.hot,
      text: c.text,
    };
  }, [overlays.captions, captions, time]);

  const fontStyle = useMemo(() => {
    switch (subtitleFont) {
      case "Instrument":
        return { fontFamily: "'Instrument Serif', Georgia, serif" };
      case "Neue Haas":
        return { fontFamily: "'Helvetica Neue', Arial, sans-serif" };
      case "Söhne Mono":
        return { fontFamily: "'Consolas', 'Courier New', monospace" };
      case "Inter Tight":
      default:
        return { fontFamily: "'Inter Tight', 'Inter', sans-serif" };
    }
  }, [subtitleFont]);

  const kb = [
    `scale(${1.05 + local * 0.1}) translate(${(1 - local) * 1.4}%, ${local * -1.2}%)`,
    `scale(${1.08 + local * 0.06}) translate(${local * -1.8}%, ${(1 - local) * 1}%)`,
    `scale(${1.04 + local * 0.12}) translate(${local * 1.2}%, ${local * 1.4}%)`,
  ][idx];

  return (
    <div
      onClick={toggle}
      className="relative cursor-pointer overflow-hidden rounded-[20px] border border-white/[0.09] bg-black shadow-[0_60px_120px_-50px_rgba(0,0,0,1),0_0_120px_-60px_rgba(47,92,255,0.9)]"
      style={{ aspectRatio: String(RATIO_VALUE[ratio]) }}
    >
      {/* ambient shadows & tints (detrás del video para que no lo oscurezcan) */}
      <div className="pointer-events-none absolute inset-0 z-0" style={{ background: scene.tint }} />
      <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(120%_80%_at_50%_10%,transparent_35%,rgba(0,0,0,0.55)_100%)]" />

      {/* footage (video y tomas DELANTE de las sombras para máxima visibilidad y claridad) */}
      {previewVideoUrl ? (
        <video
          ref={videoRef}
          src={previewVideoUrl}
          playsInline
          muted={isMuted}
          onLoadedMetadata={(e) => {
            const d = e.currentTarget.duration;
            if (d && isFinite(d) && d > 0) {
              setDuration(Math.round(d));
            }
          }}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => {
            if (!loop) setPlaying(false);
          }}
          onError={(e) => {
            console.error("[PreviewStage] Error en video tag:", e);
          }}
          className="no-drag absolute inset-0 z-10 h-full w-full object-cover"
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
            className="no-drag absolute inset-0 z-10 h-full w-full object-cover transition-opacity duration-700"
            style={{ opacity: idx === sc.f ? 1 : 0, transform: idx === sc.f ? kb : "scale(1.05)" }}
          />
        ))
      )}

      {/* micro efectos sutiles sobre el video */}
      <div className="pointer-events-none absolute inset-0 z-20 film-grain opacity-[0.04] mix-blend-overlay" />
      {running && (
        <div className="pointer-events-none absolute inset-0 z-20 overflow-hidden">
          <div className="sweep-line h-[35%] w-full bg-gradient-to-b from-transparent via-beam-300/10 to-transparent" />
        </div>
      )}

      {/* thirds grid */}
      {overlays.grid && (
        <div className="pointer-events-none absolute inset-0 z-20">
          <div className="absolute inset-y-0 left-1/3 w-px bg-white/15" />
          <div className="absolute inset-y-0 left-2/3 w-px bg-white/15" />
          <div className="absolute inset-x-0 top-1/3 h-px bg-white/15" />
          <div className="absolute inset-x-0 top-2/3 h-px bg-white/15" />
        </div>
      )}

      {/* safe areas */}
      {overlays.safe && (
        <div className="pointer-events-none absolute inset-0 z-20">
          <div className="absolute inset-[6%] rounded-[10px] border border-dashed border-white/10" />
          <div className="absolute bottom-[6%] right-[6%] top-[6%] w-[12%] rounded-[8px] border border-dashed border-beam-300/20">
            <span className="micro-sm absolute bottom-1 right-1 text-[8px] text-beam-200/40 font-mono">
              UI
            </span>
          </div>
          <div className="absolute inset-x-[6%] bottom-[6%] h-[12%] rounded-[8px] border border-dashed border-beam-300/20" />
        </div>
      )}

      {/* subject tracking */}
      {overlays.tracking && (
        <div
          className="pointer-events-none absolute h-[28%] w-[48%] transition-all duration-1000 ease-linear z-20"
          style={{
            left: `${26 + Math.sin(time / 3.4) * 3}%`,
            top: `${28 + Math.cos(time / 4.1) * 2}%`,
          }}
        >
          <div className="relative h-full w-full">
            {[
              "left-0 top-0 border-l border-t",
              "right-0 top-0 border-r border-t",
              "left-0 bottom-0 border-l border-b",
              "right-0 bottom-0 border-r border-b",
            ].map((c) => (
              <span key={c} className={cn("absolute h-3 w-3 border-beam-300/60", c)} />
            ))}
            <span className="micro-sm absolute bottom-1 left-1.5 whitespace-nowrap bg-black/60 px-1.5 py-0.5 rounded text-[8px] text-beam-200/80 backdrop-blur-sm border border-white/[0.08]">
              Sujeto 98%
            </span>
          </div>
        </div>
      )}

      {/* interactive live captions (unburned preview with live styling) */}
      {cap && (
        <div
          className={cn(
            "absolute inset-x-[6%] z-20 pointer-events-none select-none flex justify-center items-end transition-all duration-300",
            ratio === "9:16" ? "bottom-[16%] sm:bottom-[18%]" : "bottom-[8%] sm:bottom-[10%]"
          )}
          style={fontStyle}
        >
          {subtitleStyle === "karaoke" ? (
            <div className="inline-block max-w-[90%] px-3 py-1 sm:px-3.5 sm:py-1.5 rounded-xl bg-black/75 backdrop-blur-md border border-white/10 shadow-[0_4px_20px_rgba(0,0,0,0.65)]">
              <p className="text-center text-xs sm:text-[13px] md:text-sm font-bold leading-snug">
                {cap.words.map((w, i) => {
                  const isCurrent = i === cap.activeIdx;
                  const isPast = time >= w.end;
                  return (
                    <span
                      key={w.globalIndex}
                      className={cn(
                        "transition-all duration-100 inline-block mx-0.5 px-1 py-0.5 rounded",
                        isCurrent
                          ? "bg-beam-500 text-white font-extrabold shadow-[0_0_12px_rgba(79,123,255,0.9)] scale-105"
                          : isPast
                            ? "text-white opacity-95"
                            : "text-white/35",
                      )}
                    >
                      {w.word}
                    </span>
                  );
                })}
              </p>
            </div>
          ) : subtitleStyle === "minimal" ? (
            <div className="inline-block max-w-[90%] px-3.5 py-1 rounded-full bg-black/80 backdrop-blur-md border border-white/12 shadow-[0_4px_16px_rgba(0,0,0,0.55)]">
              <p className="text-center text-[11px] sm:text-xs md:text-[12.5px] font-medium text-white/90 leading-tight">
                {cap.words.map((w, i) => {
                  const isCurrent = i === cap.activeIdx;
                  const isPast = time >= w.end;
                  return (
                    <span
                      key={w.globalIndex}
                      className={cn(
                        "transition-colors duration-100 inline-block mx-0.5",
                        isCurrent
                          ? "text-beam-300 font-bold scale-105"
                          : isPast
                            ? "text-white"
                            : "text-white/40",
                      )}
                    >
                      {w.word}
                    </span>
                  );
                })}
              </p>
            </div>
          ) : subtitleStyle === "outline" ? (
            <div className="inline-block max-w-[90%]">
              <p
                className="text-center text-xs sm:text-sm md:text-[15px] font-black uppercase leading-tight tracking-wide text-yellow-300"
                style={{
                  WebkitTextStroke: "1px #000",
                  textShadow:
                    "1.5px 1.5px 0 #000, -1.5px -1.5px 0 #000, 1.5px -1.5px 0 #000, -1.5px 1.5px 0 #000, 0 3px 12px rgba(0,0,0,0.9)",
                }}
              >
                {cap.words.map((w, i) => {
                  const isCurrent = i === cap.activeIdx;
                  return (
                    <span
                      key={w.globalIndex}
                      className={cn(
                        "transition-transform duration-100 inline-block mx-0.5 sm:mx-1",
                        isCurrent
                          ? "scale-110 text-cyan-300 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]"
                          : "scale-100",
                      )}
                    >
                      {w.word}
                    </span>
                  );
                })}
              </p>
            </div>
          ) : (
            /* Kinetic Bold (default) */
            <div className="inline-block max-w-[90%]">
              <p
                className={cn(
                  "text-center text-xs sm:text-sm md:text-[14.5px] font-extrabold uppercase leading-tight tracking-tight",
                  cap.hot ? "text-white" : "text-white/95",
                )}
                style={{ textShadow: "0 2px 14px rgba(0,0,0,0.9), 0 1px 3px rgba(0,0,0,0.95)" }}
              >
                {cap.words.map((w, i) => {
                  const isCurrent = i === cap.activeIdx;
                  const isPast = time >= w.end;
                  return (
                    <span
                      key={w.globalIndex}
                      className={cn(
                        "transition-all duration-100 inline-block mx-0.5",
                        isCurrent
                          ? "text-beam-300 scale-105 [text-shadow:0_0_14px_rgba(79,123,255,0.95)]"
                          : isPast
                            ? "text-white opacity-90"
                            : "text-white/45",
                      )}
                    >
                      {w.word}
                    </span>
                  );
                })}
              </p>
              <div className="mx-auto mt-1 h-0.5 w-6 rounded-full bg-beam-300/60 shadow-[0_0_6px_rgba(126,163,255,0.7)]" />
            </div>
          )}
        </div>
      )}

      {/* top HUD (contador y en vivo con márgenes seguros y tipografía nítida) */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between p-3 sm:p-3.5 z-20">
        <div className="flex items-center gap-1.5 rounded-full border border-white/12 bg-black/60 px-2.5 py-0.5 backdrop-blur-md shadow-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-ember-400 anim-ping shrink-0" />
          <span className="text-[9px] font-semibold text-white/80 uppercase tracking-wider">En vivo</span>
        </div>
        <span className="tnum font-mono rounded-full border border-white/12 bg-black/60 px-2.5 py-0.5 text-[9.5px] font-medium text-white/90 backdrop-blur-md shadow-sm shrink-0 whitespace-nowrap">
          {timecode(time)}
        </span>
      </div>

      {/* bottom HUD (nombres limpios sin desbordamiento) */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-between p-3 sm:p-3.5 z-20">
        <span className="text-[9px] font-medium text-white/55 bg-black/60 px-2 py-0.5 rounded-md border border-white/10 backdrop-blur-md shadow-sm truncate max-w-[130px]">
          {scene.name}
        </span>
        <span className="text-[9px] font-mono text-white/45 bg-black/60 px-1.5 py-0.5 rounded-md border border-white/10 backdrop-blur-md shadow-sm shrink-0">
          {ratio} · 4K
        </span>
      </div>

      {running && (
        <div className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-2 rounded-full border border-beam-300/25 bg-black/50 px-3 py-1.5 backdrop-blur-md z-30">
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
            "absolute left-1/2 top-1/2 grid h-14 w-14 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-white/15 bg-black/50 text-white/90 backdrop-blur-md shadow-[0_8px_32px_rgba(0,0,0,0.6)] transition-all duration-300 z-30",
            playing ? "pointer-events-none scale-75 opacity-0" : "opacity-100 hover:scale-105 active:scale-95",
          )}
        >
          <IconPlay className="h-5 w-5 ml-0.5 text-white" />
        </button>
      </div>

      <Scopes />
      <Hairline className="absolute inset-x-0 bottom-0" />
    </div>
  );
}

export function Transport() {
  const {
    playing,
    toggle,
    seek,
    time,
    duration,
    rate,
    setRate,
    loop,
    setLoop,
    isMuted,
    toggleMute,
  } = useEditor();
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
        <IconButton
          size="sm"
          title={isMuted ? "Activar audio" : "Silenciar"}
          active={!isMuted}
          onClick={toggleMute}
        >
          <IconVolume className={cn("h-3.5 w-3.5", isMuted && "opacity-40")} />
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

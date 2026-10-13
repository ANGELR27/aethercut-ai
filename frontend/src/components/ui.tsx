import type { ReactNode } from "react";
import { cn } from "@/utils/cn";

export function Panel({
  children,
  className,
  tone = "glass",
}: {
  children: ReactNode;
  className?: string;
  tone?: "glass" | "soft" | "deep";
}) {
  return (
    <div
      className={cn(
        tone === "glass" && "glass",
        tone === "soft" && "glass-soft",
        tone === "deep" && "glass-deep",
        "rounded-2xl",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SectionLabel({
  children,
  right,
  className,
}: {
  children: ReactNode;
  right?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between gap-3 px-1", className)}>
      <span className="micro text-white/35">{children}</span>
      {right}
    </div>
  );
}

export function IconButton({
  children,
  onClick,
  active,
  title,
  className,
  size = "md",
}: {
  children: ReactNode;
  onClick?: () => void;
  active?: boolean;
  title?: string;
  className?: string;
  size?: "sm" | "md" | "lg";
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      className={cn(
        "group relative grid place-items-center rounded-xl border transition-all duration-300",
        size === "sm" && "h-7 w-7",
        size === "md" && "h-9 w-9",
        size === "lg" && "h-11 w-11",
        active
          ? "border-beam-400/40 bg-beam-500/12 text-beam-200 glow-beam"
          : "border-white/[0.07] bg-white/[0.02] text-white/45 hover:border-white/15 hover:bg-white/[0.05] hover:text-white/85",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Toggle({
  on,
  onChange,
  label,
  hint,
}: {
  on: boolean;
  onChange: () => void;
  label: string;
  hint?: string;
}) {
  return (
    <button
      onClick={onChange}
      className="flex w-full items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-white/[0.03]"
    >
      <span className="min-w-0">
        <span className="block text-[11px] leading-tight text-white/70">{label}</span>
        {hint && <span className="micro-sm mt-1 block text-white/25">{hint}</span>}
      </span>
      <span
        className={cn(
          "relative h-[14px] w-[26px] shrink-0 rounded-full border transition-all duration-300",
          on
            ? "border-beam-400/50 bg-beam-500/25 shadow-[0_0_14px_-2px_rgba(47,92,255,0.7)]"
            : "border-white/10 bg-white/[0.03]",
        )}
      >
        <span
          className={cn(
            "absolute top-[1.5px] h-[9px] w-[9px] rounded-full transition-all duration-300",
            on ? "left-[14px] bg-beam-200" : "left-[2px] bg-white/35",
          )}
        />
      </span>
    </button>
  );
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
  className,
}: {
  options: { id: T; label: string; glyph?: string }[];
  value: T;
  onChange: (v: T) => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-0.5 rounded-xl border border-white/[0.06] bg-black/40 p-0.5",
        className,
      )}
    >
      {options.map((o) => (
        <button
          key={o.id}
          onClick={() => onChange(o.id)}
          className={cn(
            "relative flex-1 rounded-[9px] px-2 py-[5px] text-[10px] font-medium tracking-wide transition-all duration-300",
            value === o.id
              ? "bg-gradient-to-b from-white/[0.12] to-white/[0.04] text-white shadow-[0_1px_0_0_rgba(255,255,255,0.1)_inset,0_6px_16px_-10px_rgba(47,92,255,0.9)]"
              : "text-white/35 hover:text-white/65",
          )}
        >
          {o.glyph && <span className="mr-1 opacity-60">{o.glyph}</span>}
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Meter({
  value,
  tone = "beam",
  height = 3,
}: {
  value: number;
  tone?: "beam" | "signal" | "ember";
  height?: number;
}) {
  const grad =
    tone === "beam"
      ? "linear-gradient(90deg,#142a5e,#2f5cff 60%,#7ea3ff)"
      : tone === "signal"
        ? "linear-gradient(90deg,#0d3a34,#46e0c0)"
        : "linear-gradient(90deg,#4a1f14,#ff7a59)";
  return (
    <div
      className="w-full overflow-hidden rounded-full bg-white/[0.05]"
      style={{ height }}
    >
      <div
        className="h-full rounded-full transition-[width] duration-700 ease-out"
        style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: grad }}
      />
    </div>
  );
}

export function Stat({
  label,
  value,
  unit,
  delta,
  glyph,
}: {
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  glyph?: ReactNode;
}) {
  return (
    <div className="group relative overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.015] p-2.5 transition-colors hover:border-white/[0.12]">
      <div className="flex items-center justify-between">
        <span className="micro-sm text-white/30">{label}</span>
        {glyph && <span className="text-white/20">{glyph}</span>}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="tnum text-[17px] font-light leading-none text-white">{value}</span>
        {unit && <span className="text-[10px] text-white/35">{unit}</span>}
      </div>
      {delta && (
        <div className="mt-1.5 text-[9.5px] font-medium tracking-wide text-signal-400">
          {delta}
        </div>
      )}
      <div className="pointer-events-none absolute inset-x-0 -bottom-6 h-8 bg-beam-500/20 blur-2xl transition-opacity duration-500 opacity-0 group-hover:opacity-100" />
    </div>
  );
}

export function Hairline({ className }: { className?: string }) {
  return <div className={cn("hairline h-px w-full opacity-60", className)} />;
}

export function Glyph({ children, tone = "beam" }: { children: ReactNode; tone?: "beam" | "signal" }) {
  return (
    <span
      className={cn(
        "grid h-6 w-6 shrink-0 place-items-center rounded-lg border text-[11px] leading-none",
        tone === "beam"
          ? "border-beam-400/25 bg-beam-500/10 text-beam-200"
          : "border-signal-400/25 bg-signal-400/10 text-signal-400",
      )}
    >
      {children}
    </span>
  );
}

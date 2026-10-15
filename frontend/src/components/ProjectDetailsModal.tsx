import { useState, useEffect } from "react";
import { IconCheck, IconClose, IconCopy, IconShare } from "./Icons";

interface ProjectDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string | null;
  projectTitle: string;
  thumbnailUrl?: string | null;
  durationSec?: number | null;
}

interface PublishInfo {
  title: string;
  description: string;
  tags: string[];
  hashtags: string[];
  hashtags_str: string;
}

export function ProjectDetailsModal({
  isOpen,
  onClose,
  projectId,
  projectTitle,
  thumbnailUrl,
  durationSec,
}: ProjectDetailsModalProps) {
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState<PublishInfo | null>(null);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !projectId) {
      setInfo(null);
      return;
    }

    let isMounted = true;
    setLoading(true);

    fetch(`/api/projects/${projectId}/publish-info`)
      .then((res) => {
        if (!res.ok) throw new Error("Error cargando detalles");
        return res.json();
      })
      .then((data: PublishInfo) => {
        if (isMounted) {
          setInfo(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          // Fallback con datos locales disponibles
          const baseTags = ["#Viral", "#Tendencias", "#AetherCut", "#Shorts", "#Reels", "#IA"];
          setInfo({
            title: projectTitle || "Video KAI",
            description: `${projectTitle}\n\n🎬 Video producido con Inteligencia Artificial.\n🔔 ¡Suscríbete y activa la campana!\n💬 ¿Qué opinas? Déjamelo en los comentarios.`,
            tags: ["Viral", "Tendencias", "AetherCut", "Shorts", "Reels", "IA"],
            hashtags: baseTags,
            hashtags_str: baseTags.join(" "),
          });
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, projectId, projectTitle]);

  if (!isOpen) return null;

  const copyToClipboard = (text: string, sectionId: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
    } else {
      const el = document.createElement("textarea");
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
    }

    setCopiedSection(sectionId);
    window.setTimeout(() => {
      setCopiedSection((cur) => (cur === sectionId ? null : cur));
    }, 2200);
  };

  const currentTitle = info?.title || projectTitle || "Video KAI";
  const currentDesc = info?.description || "";
  const currentTags = info?.hashtags_str || "";

  const handleCopyAll = () => {
    const fullText = `${currentTitle}\n\n${currentDesc}\n\n${currentTags}`.trim();
    copyToClipboard(fullText, "all");
  };

  const durStr = durationSec
    ? durationSec >= 60
      ? `${Math.floor(durationSec / 60)}m ${Math.round(durationSec % 60)}s`
      : `${Math.round(durationSec)}s`
    : null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      {/* Backdrop */}
      <div className="absolute inset-0" onClick={onClose} />

      <div className="relative w-full max-w-xl max-h-[90vh] overflow-hidden rounded-2xl border border-white/12 bg-ink-950/98 p-5 sm:p-6 shadow-[0_25px_80px_rgba(0,0,0,0.85),0_0_80px_-20px_rgba(79,123,255,0.35)] backdrop-blur-2xl z-10 flex flex-col text-left">
        {/* Glow ambient */}
        <div className="pointer-events-none absolute -right-20 -top-20 h-44 w-44 rounded-full bg-beam-500/15 blur-3xl" />
        <div className="pointer-events-none absolute -left-20 -bottom-20 h-44 w-44 rounded-full bg-purple-500/10 blur-3xl" />

        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-white/[0.08] shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-beam-400/30 bg-beam-500/15 text-beam-300 shadow-[0_0_20px_rgba(79,123,255,0.25)]">
              <IconShare className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-white truncate">Detalles y Publicación</h3>
              <p className="text-[11px] text-white/40 truncate">
                Copia título, descripción y hashtags listos para TikTok, Shorts y Reels
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/[0.05] transition-colors shrink-0"
          >
            <IconClose className="h-4 w-4" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
          {/* Card Preview Banner */}
          <div className="flex items-center gap-3 p-2.5 rounded-xl border border-white/[0.06] bg-white/[0.02]">
            {thumbnailUrl ? (
              <img
                src={thumbnailUrl}
                alt=""
                className="h-14 w-10 object-cover rounded-lg border border-white/10 shrink-0"
              />
            ) : null}
            <div className="min-w-0 flex-1">
              <div className="text-[12px] font-medium text-white truncate">{currentTitle}</div>
              <div className="mt-1 flex items-center gap-2 text-[10px] text-white/40">
                {durStr && <span className="font-mono bg-white/[0.05] px-1.5 py-0.5 rounded">⏱ {durStr}</span>}
                <span className="text-emerald-400/90 font-medium">✓ Listo para publicar</span>
              </div>
            </div>
          </div>

          {/* Botón Principal: Copiar TODO */}
          <button
            type="button"
            onClick={handleCopyAll}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium text-[12px] text-white bg-gradient-to-r from-beam-600 via-indigo-600 to-purple-600 hover:from-beam-500 hover:to-purple-500 shadow-[0_0_25px_rgba(79,123,255,0.4)] transition-all active:scale-[0.99]"
          >
            {copiedSection === "all" ? (
              <>
                <IconCheck className="h-4 w-4 text-emerald-300" />
                <span className="text-emerald-200">¡Todo copiado al portapapeles!</span>
              </>
            ) : (
              <>
                <IconCopy className="h-4 w-4" />
                <span>Copiar Todo (Título + Descripción + Hashtags)</span>
              </>
            )}
          </button>

          {/* Sección 1: TÍTULO */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-semibold uppercase tracking-wider text-white/50">Título del Video</span>
              <button
                type="button"
                onClick={() => copyToClipboard(currentTitle, "title")}
                className="flex items-center gap-1 text-beam-300 hover:text-beam-200 text-[10.5px] font-medium"
              >
                {copiedSection === "title" ? (
                  <>
                    <IconCheck className="h-3 w-3 text-emerald-400" />
                    <span className="text-emerald-300">Copiado</span>
                  </>
                ) : (
                  <>
                    <IconCopy className="h-3 w-3" />
                    <span>Copiar Título</span>
                  </>
                )}
              </button>
            </div>
            <div className="p-3 rounded-xl border border-white/[0.08] bg-black/40 text-[12px] text-white/90 font-medium select-all">
              {loading ? "Cargando..." : currentTitle}
            </div>
          </div>

          {/* Sección 2: DESCRIPCIÓN */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-semibold uppercase tracking-wider text-white/50">Descripción / Gancho</span>
              <button
                type="button"
                onClick={() => copyToClipboard(currentDesc, "desc")}
                className="flex items-center gap-1 text-beam-300 hover:text-beam-200 text-[10.5px] font-medium"
              >
                {copiedSection === "desc" ? (
                  <>
                    <IconCheck className="h-3 w-3 text-emerald-400" />
                    <span className="text-emerald-300">Copiado</span>
                  </>
                ) : (
                  <>
                    <IconCopy className="h-3 w-3" />
                    <span>Copiar Descripción</span>
                  </>
                )}
              </button>
            </div>
            <div className="p-3 rounded-xl border border-white/[0.08] bg-black/40 text-[11.5px] text-white/80 whitespace-pre-line leading-relaxed select-all max-h-36 overflow-y-auto">
              {loading ? "Generando descripción estructurada..." : currentDesc}
            </div>
          </div>

          {/* Sección 3: HASHTAGS */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-semibold uppercase tracking-wider text-white/50">Hashtags Virales (#)</span>
              <button
                type="button"
                onClick={() => copyToClipboard(currentTags, "tags")}
                className="flex items-center gap-1 text-beam-300 hover:text-beam-200 text-[10.5px] font-medium"
              >
                {copiedSection === "tags" ? (
                  <>
                    <IconCheck className="h-3 w-3 text-emerald-400" />
                    <span className="text-emerald-300">Copiado</span>
                  </>
                ) : (
                  <>
                    <IconCopy className="h-3 w-3" />
                    <span>Copiar Hashtags</span>
                  </>
                )}
              </button>
            </div>
            <div className="p-3 rounded-xl border border-white/[0.08] bg-black/40 text-[11px] text-beam-200/90 font-mono select-all flex flex-wrap gap-1.5">
              {loading ? (
                <span className="text-white/40">Cargando hashtags...</span>
              ) : info?.hashtags && info.hashtags.length > 0 ? (
                info.hashtags.map((tag, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded-md bg-beam-500/10 border border-beam-400/20 text-beam-200 text-[10.5px]"
                  >
                    {tag}
                  </span>
                ))
              ) : (
                <span>{currentTags}</span>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-white/[0.08] flex justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl border border-white/10 bg-white/[0.04] text-[11.5px] font-medium text-white/80 hover:bg-white/[0.08]"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

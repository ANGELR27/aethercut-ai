import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  AUTOMATIONS,
  BASE_RETENTION,
  CLIPS,
  DURATION,
  PLATFORMS,
  type Clip,
  type PlatformId,
  type Ratio,
  retentionAt,
  type Automation,
} from "./data";

export type LogEntry = {
  id: number;
  text: string;
  kind: "ai" | "info" | "warn";
  at: string;
};

export type BackendProject = {
  id: string;
  name: string;
  status: string;
  duration: number;
  updated_at?: string;
  thumbnail_url?: string | null;
  master_video_url?: string | null;
  has_plan?: boolean;
  has_result?: boolean;
};

type Ctx = {
  /* playback */
  playing: boolean;
  time: number;
  duration: number;
  rate: number;
  loop: boolean;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  seek: (t: number) => void;
  setRate: (r: number) => void;
  setLoop: (v: boolean) => void;

  /* viewer */
  ratio: Ratio;
  setRatio: (r: Ratio) => void;
  overlays: Record<string, boolean>;
  toggleOverlay: (k: string) => void;
  previewVideoUrl: string | null;
  videoRef: React.RefObject<HTMLVideoElement | null>;

  /* timeline */
  clips: Clip[];
  selected: string | null;
  select: (id: string | null) => void;
  updateClip: (id: string, patch: Partial<Clip>) => void;
  pxPerSec: number;
  setPxPerSec: (v: number) => void;

  /* ai */
  progress: Record<string, number>;
  applied: string[];
  run: (id: string) => void;
  running: boolean;

  /* metrics */
  platform: PlatformId;
  setPlatform: (p: PlatformId) => void;
  score: number;
  boost: number;
  metrics: {
    reach: number;
    views: number;
    saves: number;
    comments: number;
    shares: number;
    watch: number;
    ctr: number;
    avg: number;
    velocity: number;
  };

  /* backend integration */
  projects: BackendProject[];
  activeProjectId: string | null;
  activeProjectTitle: string;
  isUploading: boolean;
  isCreating: boolean;
  createProgress: number;
  createStatusMessage: string;
  selectProject: (id: string) => void;
  loadProjects: () => Promise<void>;
  loadProject: (id: string) => Promise<void>;
  exportMaster: () => Promise<void>;
  importVideo: (file: File) => Promise<void>;
  createVideo: (topic: string, opts?: { duration?: number; style?: string }) => Promise<string | null>;

  /* voice */
  selectedVoice: string;
  setSelectedVoice: (v: string) => void;
  playingVoiceId: string | null;
  previewVoice: (voiceId: string) => void;

  flash: (msg: string) => void;
  log: LogEntry[];
  toast: string | null;
};

const EditorCtx = createContext<Ctx | null>(null);

let logId = 0;

export function EditorProvider({ children }: { children: ReactNode }) {
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(DURATION);
  const [rate, setRate] = useState(1);
  const [loop, setLoop] = useState(true);

  const [ratio, setRatio] = useState<Ratio>("9:16");
  const [overlays, setOverlays] = useState<Record<string, boolean>>({
    safe: true,
    captions: true,
    grid: false,
    tracking: true,
    scopes: true,
  });

  const [clips, setClips] = useState<Clip[]>(CLIPS);
  const [selected, setSelected] = useState<string | null>("c1");
  const [pxPerSec, setPxPerSec] = useState(46);

  const [progress, setProgress] = useState<Record<string, number>>({});
  const [applied, setApplied] = useState<string[]>(["silence", "captions"]);
  const [platform, setPlatform] = useState<PlatformId>("tiktok");
  const [log, setLog] = useState<LogEntry[]>([
    { id: logId++, kind: "ai", at: "00:00", text: "Estudio iniciado · Conectado al backend" },
  ]);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<number | null>(null);

  /* Backend project state */
  const [projects, setProjects] = useState<BackendProject[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeProjectTitle, setActiveProjectTitle] = useState<string>("Ritmo Nocturno — EP.02");
  const [previewVideoUrl, setPreviewVideoUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createProgress, setCreateProgress] = useState(0);
  const [createStatusMessage, setCreateStatusMessage] = useState("");
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const pushLog = useCallback((text: string, kind: LogEntry["kind"] = "ai") => {
    const now = new Date();
    const at = `${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
    setLog((l) => [{ id: logId++, text, kind, at }, ...l].slice(0, 30));
  }, []);

  const flash = useCallback((text: string) => {
    setToast(text);
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 2600);
  }, []);

  /* Voice selection with persistent localStorage */
  const [selectedVoice, setSelectedVoiceState] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("lumen_selected_voice") || "es-MX-JorgeNeural";
    }
    return "es-MX-JorgeNeural";
  });

  const setSelectedVoice = useCallback(
    (voiceId: string) => {
      setSelectedVoiceState(voiceId);
      if (typeof window !== "undefined") {
        try {
          localStorage.setItem("lumen_selected_voice", voiceId);
        } catch (_) {}
      }
      pushLog(`Voz de locución activa: ${voiceId}`, "info");
      flash("Voz seleccionada para los próximos videos");
    },
    [pushLog, flash],
  );

  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const audioPreviewRef = useRef<HTMLAudioElement | null>(null);

  const previewVoice = useCallback(
    (voiceId: string) => {
      try {
        if (audioPreviewRef.current) {
          audioPreviewRef.current.pause();
          audioPreviewRef.current.currentTime = 0;
          audioPreviewRef.current = null;
        }

        if (playingVoiceId === voiceId) {
          setPlayingVoiceId(null);
          return;
        }

        setPlayingVoiceId(voiceId);
        pushLog(`Escuchando muestra de locución: ${voiceId}`, "info");

        const audioUrl = `/api/tts-preview?voice=${encodeURIComponent(voiceId)}&t=${Date.now()}`;
        const audio = new Audio(audioUrl);
        audioPreviewRef.current = audio;

        audio.onended = () => {
          setPlayingVoiceId(null);
          audioPreviewRef.current = null;
        };

        audio.onerror = () => {
          setPlayingVoiceId(null);
          audioPreviewRef.current = null;
          pushLog("No se pudo reproducir la muestra de voz", "warn");
        };

        audio.play().catch((e) => {
          console.warn("Reproducción de audio prevenida:", e);
          setPlayingVoiceId(null);
        });
      } catch (err: any) {
        setPlayingVoiceId(null);
        console.warn("Error en previewVoice:", err);
      }
    },
    [playingVoiceId, pushLog],
  );

  /* ---------------- playback engine ---------------- */
  const raf = useRef<number>(0);
  const last = useRef<number>(0);

  useEffect(() => {
    if (!playing) return;
    last.current = performance.now();
    const tick = (now: number) => {
      if (videoRef.current && previewVideoUrl) {
        setTime(videoRef.current.currentTime);
        if (videoRef.current.ended) {
          if (loop) {
            videoRef.current.currentTime = 0;
            videoRef.current.play().catch(() => {});
          } else {
            setPlaying(false);
          }
        }
      } else {
        const dt = ((now - last.current) / 1000) * rate;
        last.current = now;
        setTime((t) => {
          const n = t + dt;
          if (n >= duration) {
            if (loop) return n - duration;
            setPlaying(false);
            return duration;
          }
          return n;
        });
      }
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [playing, rate, loop, duration, previewVideoUrl]);

  const seek = useCallback(
    (t: number) => {
      const target = Math.max(0, Math.min(duration, t));
      setTime(target);
      if (videoRef.current) {
        videoRef.current.currentTime = target;
      }
    },
    [duration],
  );

  const play = useCallback(() => {
    setPlaying(true);
    if (videoRef.current) {
      videoRef.current.play().catch(() => {});
    }
  }, []);

  const pause = useCallback(() => {
    setPlaying(false);
    if (videoRef.current) {
      videoRef.current.pause();
    }
  }, []);

  const toggle = useCallback(() => {
    setPlaying((p) => {
      const next = !p;
      if (videoRef.current) {
        if (next) videoRef.current.play().catch(() => {});
        else videoRef.current.pause();
      }
      return next;
    });
  }, []);

  const handleSetRate = useCallback((r: number) => {
    setRate(r);
    if (videoRef.current) {
      videoRef.current.playbackRate = r;
    }
  }, []);

  /* ---------------- backend project loading ---------------- */
  const loadProject = useCallback(
    async (id: string) => {
      try {
        pushLog(`Cargando proyecto ${id}...`, "info");
        const res = await fetch(`/api/projects/${id}`);
        if (!res.ok) throw new Error("Proyecto no encontrado");
        const data = await res.json();
        const proj = data.project || {};
        const title = proj.original_name || (proj.result && proj.result.title) || `Proyecto ${id}`;
        setActiveProjectId(id);
        setActiveProjectTitle(title);

        const dur =
          proj.result?.duration ||
          (data.editor?.scenes
            ? data.editor.scenes.reduce((acc: number, s: any) => acc + (s.duration || 0), 0)
            : 0);
        if (dur && dur > 0) {
          setDuration(Math.round(dur));
        }

        // Conectar url de previsualización
        setPreviewVideoUrl(`/api/projects/${id}/preview?v=${Date.now()}`);

        // Intentar obtener broadcast-plan para escenas reales
        try {
          const bpRes = await fetch(`/api/projects/${id}/broadcast-plan`);
          if (bpRes.ok) {
            const bp = await bpRes.json();
            if (bp.scenes && bp.scenes.length > 0) {
              let cursor = 0;
              const mapped: Clip[] = bp.scenes.map((sc: any, i: number) => {
                const scDur = sc.duration || 6;
                const clip: Clip = {
                  id: `sc-${sc.scene_id || i}`,
                  track: "v1",
                  start: cursor,
                  duration: scDur,
                  label: sc.headline || sc.name || `Escena ${i + 1}`,
                  kind: "scene",
                  frame: sc.thumb_url,
                };
                cursor += scDur;
                return clip;
              });
              setClips(mapped);
            }
          }
        } catch (_) {}

        pushLog(`✓ Proyecto cargado: ${title}`, "ai");
        flash(`Cargado: ${title}`);
        (window as any).currentProjectId = id;
      } catch (err: any) {
        pushLog(`Error cargando proyecto: ${err.message}`, "warn");
      }
    },
    [pushLog, flash],
  );

  const loadProjects = useCallback(async () => {
    try {
      const res = await fetch("/api/projects");
      if (!res.ok) return;
      const data = await res.json();
      if (data.projects && Array.isArray(data.projects)) {
        setProjects(data.projects);

        const urlParams = new URLSearchParams(window.location.search);
        const qProj = urlParams.get("project") || urlParams.get("task");
        if (qProj) {
          loadProject(qProj);
        } else if (data.projects.length > 0 && !activeProjectId) {
          const ready = data.projects.find((p: any) => p.has_result) || data.projects[0];
          if (ready && ready.id) {
            loadProject(ready.id);
          }
        }
      }
    } catch (err) {
      console.warn("[EditorProvider] No se pudieron cargar proyectos:", err);
    }
  }, [activeProjectId, loadProject]);

  useEffect(() => {
    loadProjects();
    (window as any).openProject = (id: string) => {
      loadProject(id);
    };
  }, [loadProjects, loadProject]);

  const selectProject = useCallback(
    (id: string) => {
      loadProject(id);
    },
    [loadProject],
  );

  const exportMaster = useCallback(async () => {
    if (!activeProjectId) {
      flash("Selecciona un proyecto primero");
      return;
    }
    try {
      pushLog(`Exportando máster del proyecto ${activeProjectId}...`, "info");
      const a = document.createElement("a");
      a.href = `/api/projects/${activeProjectId}/download`;
      a.download = `${activeProjectTitle || "video_master"}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      flash("Descarga del máster iniciada");
    } catch (e: any) {
      flash(`Error al exportar: ${e.message}`);
    }
  }, [activeProjectId, activeProjectTitle, pushLog, flash]);

  const importVideo = useCallback(
    async (file: File) => {
      try {
        setIsUploading(true);
        pushLog(`Iniciando subida: ${file.name}...`, "info");
        flash(`Subiendo ${file.name}...`);
        const form = new FormData();
        form.append("video", file);
        form.append("silence_threshold", "1.5");
        form.append("broll", "true");
        form.append("cards", "true");
        form.append("captions", "true");
        form.append("shorts", "true");
        form.append("voice", selectedVoice);

        const res = await fetch("/api/process-video", {
          method: "POST",
          body: form,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Error en el servidor al recibir video");

        const taskId = data.task_id;
        pushLog(`Procesando video (Tarea: ${taskId})...`, "ai");
        flash(`Tarea ${taskId} en proceso`);

        const es = new EventSource(`/api/stream-progress/${taskId}`);
        es.onmessage = (ev) => {
          try {
            const p = JSON.parse(ev.data);
            if (p.message) pushLog(p.message, "ai");
            if (p.completed) {
              es.close();
              setIsUploading(false);
              flash("¡Video procesado con éxito!");
              loadProjects();
              loadProject(taskId);
            } else if (p.error) {
              es.close();
              setIsUploading(false);
              pushLog(`Error en pipeline: ${p.error}`, "warn");
              flash(`Error: ${p.error}`);
            }
          } catch (_) {}
        };
      } catch (err: any) {
        setIsUploading(false);
        pushLog(`Fallo al importar video: ${err.message}`, "warn");
        flash(`Error: ${err.message}`);
      }
    },
    [pushLog, flash, loadProjects, loadProject],
  );

  const createVideo = useCallback(
    async (topic: string, opts?: { duration?: number; style?: string }) => {
      const cleanTopic = topic.trim();
      if (!cleanTopic) return null;

      try {
        setIsCreating(true);
        setCreateProgress(10);
        setCreateStatusMessage(`Investigando: «${cleanTopic}»...`);
        pushLog(`Iniciando creación de video: ${cleanTopic}`, "ai");
        flash(`Creando video: ${cleanTopic.slice(0, 30)}...`);

        const res = await fetch("/api/streamer/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            topic: cleanTopic,
            duration_sec: opts?.duration || 45,
            aspect_ratio: ratio || "16:9",
            style: opts?.style || "divulgacion",
            voice: selectedVoice,
          }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Error al iniciar la creación");

        const taskId = data.task_id || data.project_id;
        pushLog(`Tarea iniciada con ID: ${taskId}`, "info");

        const es = new EventSource(`/api/stream-progress/${taskId}`);
        es.onmessage = (ev) => {
          try {
            const p = JSON.parse(ev.data);
            if (typeof p.progress === "number") {
              setCreateProgress(Math.max(10, Math.min(100, p.progress)));
            }
            if (p.message) {
              setCreateStatusMessage(p.message);
              pushLog(p.message, "ai");
            }
            if (p.completed) {
              es.close();
              setCreateProgress(100);
              setCreateStatusMessage("¡Video creado con éxito!");
              setIsCreating(false);
              flash("¡Video creado y masterizado!");
              loadProjects();
              loadProject(taskId);
            } else if (p.error) {
              es.close();
              setIsCreating(false);
              setCreateStatusMessage(`Error: ${p.error}`);
              pushLog(`Error en creación: ${p.error}`, "warn");
              flash(`Error: ${p.error}`);
            }
          } catch (_) {}
        };
        return taskId;
      } catch (err: any) {
        setIsCreating(false);
        setCreateStatusMessage(`Fallo: ${err.message}`);
        pushLog(`Error al crear video: ${err.message}`, "warn");
        flash(`Error: ${err.message}`);
        return null;
      }
    },
    [ratio, pushLog, flash, loadProjects, loadProject],
  );

  /* ---------------- keyboard ---------------- */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.code === "Space") {
        e.preventDefault();
        toggle();
      }
      if (e.code === "ArrowRight") seek(time + (e.shiftKey ? 1 : 1 / 12));
      if (e.code === "ArrowLeft") seek(time - (e.shiftKey ? 1 : 1 / 12));
      if (e.key === "l") handleSetRate(Math.min(2, rate + 0.25));
      if (e.key === "j") handleSetRate(Math.max(0.25, rate - 0.25));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [seek, time, toggle, handleSetRate, rate]);

  /* ---------------- AI engine ---------------- */
  const running = Object.keys(progress).length > 0 || isUploading || isCreating;

  const run = useCallback(
    (id: string) => {
      const auto = AUTOMATIONS.find((a) => a.id === id);
      if (!auto || applied.includes(id) || progress[id] !== undefined) return;
      setProgress((p) => ({ ...p, [id]: 0 }));
      pushLog(`Ejecutando · ${auto.name}`);
      const step = 100 / (auto.ms / 80);
      let v = 0;
      const timer = window.setInterval(() => {
        v += step;
        if (v >= 100) {
          window.clearInterval(timer);
          setProgress((p) => {
            const { [id]: _drop, ...rest } = p;
            return rest;
          });
          setApplied((a) => (a.includes(id) ? a : [...a, id]));
          pushLog(`✓ ${auto.name} aplicado`, "info");
          flash(`${auto.name} · aplicado al máster`);
          return;
        }
        setProgress((p) => ({ ...p, [id]: v }));
      }, 80);
    },
    [applied, progress, pushLog, flash],
  );

  /* ---------------- metrics ---------------- */
  const { score, boost } = useMemo(() => {
    const s = applied.reduce(
      (acc, id) => acc + (AUTOMATIONS.find((a) => a.id === id)?.score ?? 0),
      0,
    );
    const r = applied.reduce(
      (acc, id) => acc + (AUTOMATIONS.find((a) => a.id === id)?.retention ?? 0),
      0,
    );
    return { score: Math.min(99, 58 + s), boost: Math.min(0.46, r * 0.012) };
  }, [applied]);

  const metrics = useMemo(() => {
    const mult = PLATFORMS.find((p) => p.id === platform)?.mult ?? 1;
    const reachSum = applied.reduce(
      (acc, id) => acc + (AUTOMATIONS.find((a) => a.id === id)?.reach ?? 0),
      0,
    );
    const reachMul = 1 + reachSum / 46;
    const reach = 96_000 * mult * reachMul;
    const samples = BASE_RETENTION.map((_, i) => retentionAt(i, boost));
    const avg = samples.reduce((a, b) => a + b, 0) / samples.length;
    const hook = samples.slice(0, 12).reduce((a, b) => a + b, 0) / 12;
    return {
      reach,
      views: reach * 1.34,
      saves: reach * 0.061 * (1 + boost),
      comments: reach * 0.014,
      shares: reach * 0.019 * (1 + boost * 1.4),
      watch: samples[samples.length - 1],
      ctr: 6.4 + score * 0.14,
      avg,
      velocity: hook * 100,
    };
  }, [applied, boost, platform, score]);

  const value: Ctx = {
    playing,
    time,
    duration,
    rate,
    loop,
    play,
    pause,
    toggle,
    seek,
    setRate: handleSetRate,
    setLoop,
    ratio,
    setRatio,
    overlays,
    toggleOverlay: (k) => setOverlays((o) => ({ ...o, [k]: !o[k] })),
    previewVideoUrl,
    videoRef,
    clips,
    selected,
    select: setSelected,
    updateClip: (id, patch) =>
      setClips((cs) => cs.map((c) => (c.id === id ? { ...c, ...patch } : c))),
    pxPerSec,
    setPxPerSec,
    progress,
    applied,
    run,
    running,
    platform,
    setPlatform,
    score,
    boost,
    metrics,
    projects,
    activeProjectId,
    activeProjectTitle,
    isUploading,
    isCreating,
    createProgress,
    createStatusMessage,
    selectProject,
    loadProjects,
    loadProject,
    exportMaster,
    importVideo,
    createVideo,
    selectedVoice,
    setSelectedVoice,
    playingVoiceId,
    previewVoice,
    flash,
    log,
    toast,
  };

  return <EditorCtx.Provider value={value}>{children}</EditorCtx.Provider>;
}

export function useEditor() {
  const ctx = useContext(EditorCtx);
  if (!ctx) throw new Error("useEditor must be used inside EditorProvider");
  return ctx;
}

export type { Automation };

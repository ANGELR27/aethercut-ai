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
  CAPTIONS,
  DURATION,
  PLATFORMS,
  type Clip,
  type Caption,
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
  setDuration: (d: number) => void;

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
  exportMaster: (opts?: { burnSubtitles?: boolean; style?: string; title?: string }) => Promise<void>;
  importVideo: (file: File) => Promise<void>;
  createVideo: (topic: string, opts?: { duration?: number; style?: string; aspect_ratio?: Ratio }) => Promise<string | null>;
  deleteProject: (id: string) => Promise<void>;
  cancelCreation: () => Promise<void>;
  resumeProject: (taskId: string) => Promise<void>;

  /* voice */
  selectedVoice: string;
  setSelectedVoice: (v: string) => void;
  playingVoiceId: string | null;
  previewVoice: (voiceId: string) => void;

  /* subtitles */
  captions: Caption[];
  setCaptions: React.Dispatch<React.SetStateAction<Caption[]>>;
  updateCaption: (index: number, text: string) => void;
  subtitleStyle: string;
  setSubtitleStyle: (s: string) => void;
  subtitleFont: string;
  setSubtitleFont: (f: string) => void;

  /* audio / sound */
  isMuted: boolean;
  setIsMuted: (m: boolean) => void;
  toggleMute: () => void;

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
  const [activeProjectId, setActiveProjectId] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      return urlParams.get("project") || urlParams.get("task") || localStorage.getItem("lumen_active_project") || null;
    }
    return null;
  });
  const [activeProjectTitle, setActiveProjectTitle] = useState<string>("Ritmo Nocturno — EP.02");
  const [previewVideoUrl, setPreviewVideoUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createProgress, setCreateProgress] = useState(0);
  const [createStatusMessage, setCreateStatusMessage] = useState("");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const activeEsRef = useRef<EventSource | null>(null);

  /* Subtitle & Sound interactive state */
  const [captions, setCaptions] = useState<Caption[]>(CAPTIONS);
  const [subtitleStyle, setSubtitleStyle] = useState<string>("kinetic");
  const [subtitleFont, setSubtitleFont] = useState<string>("Inter Tight");
  const [isMuted, setIsMuted] = useState<boolean>(false);

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      if (videoRef.current) {
        videoRef.current.muted = next;
      }
      return next;
    });
  }, []);

  const updateCaption = useCallback((index: number, text: string) => {
    setCaptions((prev) => {
      const copy = [...prev];
      if (copy[index]) {
        copy[index] = { ...copy[index], text };
      }
      return copy;
    });
  }, []);

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
        if (typeof window !== "undefined") {
          try {
            localStorage.setItem("lumen_active_project", id);
            const url = new URL(window.location.href);
            if (url.searchParams.get("project") !== id) {
              url.searchParams.set("project", id);
              window.history.replaceState({}, "", url.toString());
            }
          } catch (_) {}
        }

        const sceneSum = data.editor?.scenes
          ? data.editor.scenes.reduce((acc: number, s: any) => acc + (s.duration || 0), 0)
          : 0;
        const dur =
          (data.editor?.duration && data.editor.duration > 0 ? data.editor.duration : null) ||
          (sceneSum > 0 ? sceneSum : null) ||
          proj.result?.duration ||
          45;
        if (dur && dur > 0) {
          setDuration(Math.round(dur));
        }

        // Conectar url de previsualización sin subtítulos quemados
        setPreviewVideoUrl(`/api/projects/${id}/preview?v=${Date.now()}`);

        // Construir pistas sincronizadas desde el editor real
        if (data.editor && data.editor.scenes && data.editor.scenes.length > 0) {
          const editor = data.editor;
          const mappedClips: Clip[] = [];

          // 1. Pista V1: Escenas de video
          editor.scenes.forEach((sc: any, i: number) => {
            const scDur = sc.duration || 6;
            const scStart = typeof sc.start === "number" ? sc.start : 0;
            mappedClips.push({
              id: `sc-${sc.scene_id || i}`,
              track: "v1",
              start: scStart,
              duration: scDur,
              label: sc.headline || sc.name || `Escena ${i + 1}`,
              kind: "scene",
              frame: sc.thumb_url,
            });
          });

          // 2. Pista V2: Tarjetas informativas y B-rolls
          if (editor.cards && editor.cards.length > 0) {
            editor.cards.forEach((cd: any, i: number) => {
              mappedClips.push({
                id: cd.id || `card-${i}`,
                track: "v2",
                start: cd.start || 0,
                duration: Math.max(1.8, Math.min(cd.duration || 3.5, 4.5)),
                label: `Inserto · ${cd.headline || cd.title || "Dato clave"}`,
                kind: "broll",
                frame: cd.card_url,
                ai: true,
              });
            });
          } else if (editor.brolls && editor.brolls.length > 0) {
            editor.brolls.forEach((br: any, i: number) => {
              mappedClips.push({
                id: br.id || `broll-${i}`,
                track: "v2",
                start: br.start || 0,
                duration: br.duration || 3,
                label: `B-Roll · ${br.concept || br.title || "Inserto"}`,
                kind: "broll",
                ai: true,
              });
            });
          }

          // 3. Pista T1: Subtítulos cinéticos sincronizados
          if (editor.captions && editor.captions.length > 0) {
            editor.scenes.forEach((sc: any, i: number) => {
              const sid = sc.scene_id || (i + 1);
              const scCaps = editor.captions.filter((c: any) => c.scene_id === sid);
              if (scCaps.length > 0) {
                const cStart = scCaps[0].start;
                const cEnd = scCaps[scCaps.length - 1].end;
                mappedClips.push({
                  id: `cap-sc-${sid}`,
                  track: "t1",
                  start: cStart,
                  duration: Math.max(1, cEnd - cStart),
                  label: "Subtítulos cinéticos",
                  kind: "caption",
                  ai: true,
                });
              } else {
                mappedClips.push({
                  id: `cap-sc-${sid}`,
                  track: "t1",
                  start: sc.start + 0.3,
                  duration: Math.max(1, (sc.duration || 6) - 0.6),
                  label: "Subtítulos cinéticos",
                  kind: "caption",
                  ai: true,
                });
              }
            });
            setCaptions(
              editor.captions.map((c: any) => ({
                start: c.start,
                end: c.end,
                text: c.text,
                hot: c.text.length < 35,
              }))
            );
          } else {
            editor.scenes.forEach((sc: any, i: number) => {
              const sid = sc.scene_id || (i + 1);
              mappedClips.push({
                id: `cap-sc-${sid}`,
                track: "t1",
                start: sc.start + 0.3,
                duration: Math.max(1, (sc.duration || 6) - 0.6),
                label: "Subtítulos cinéticos",
                kind: "caption",
                ai: true,
              });
            });
          }

          // 4. Pista A1: Locución de audio sincronizada por escena sin solapamientos
          editor.scenes.forEach((sc: any, i: number) => {
            const sid = sc.scene_id || (i + 1);
            const speechText = sc.speech || "";
            const shortLabel = speechText ? speechText.slice(0, 24) + "..." : (sc.name || `E${sid}`);
            mappedClips.push({
              id: `voice-${sid}`,
              track: "a1",
              start: sc.start,
              duration: sc.duration,
              label: `Locución · E${sid}: ${shortLabel}`,
              kind: "voice",
              ai: true,
            });
          });

          setClips(mappedClips);
        }

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
        const qProj =
          urlParams.get("project") ||
          urlParams.get("task") ||
          (typeof window !== "undefined" ? localStorage.getItem("lumen_active_project") : null);
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

  const attachCreationStream = useCallback(
    (taskId: string) => {
      if (activeEsRef.current) {
        try {
          activeEsRef.current.close();
        } catch (_) {}
        activeEsRef.current = null;
      }

      setIsCreating(true);
      if (typeof window !== "undefined") {
        try {
          localStorage.setItem("lumen_active_creation_task", taskId);
          localStorage.setItem("lumen_active_project", taskId);
          const url = new URL(window.location.href);
          url.searchParams.set("project", taskId);
          window.history.replaceState({}, "", url.toString());
        } catch (_) {}
      }

      const es = new EventSource(`/api/stream-progress/${encodeURIComponent(taskId)}`);
      activeEsRef.current = es;

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
            activeEsRef.current = null;
            setCreateProgress(100);
            setCreateStatusMessage("¡Video creado con éxito!");
            setIsCreating(false);
            if (typeof window !== "undefined") {
              try {
                localStorage.removeItem("lumen_active_creation_task");
              } catch (_) {}
            }
            flash("¡Video creado y masterizado!");
            loadProjects();
            loadProject(taskId);
          } else if (p.error) {
            es.close();
            activeEsRef.current = null;
            setIsCreating(false);
            if (typeof window !== "undefined") {
              try {
                localStorage.removeItem("lumen_active_creation_task");
              } catch (_) {}
            }
            setCreateStatusMessage(p.error);
            pushLog(`Aviso tarea: ${p.error}`, "warn");
            flash(`Aviso: ${p.error}`);
            loadProjects();
          }
        } catch (_) {}
      };

      es.onerror = () => {
        // Desconexión transitoria
      };
    },
    [pushLog, flash, loadProjects, loadProject],
  );

  const cancelCreation = useCallback(async () => {
    const taskId =
      (typeof window !== "undefined" ? localStorage.getItem("lumen_active_creation_task") : null) ||
      activeProjectId;
    if (!taskId) {
      setIsCreating(false);
      return;
    }
    try {
      pushLog(`Cancelando tarea ${taskId}...`, "warn");
      await fetch(`/api/cancel-task/${taskId}`, { method: "POST" });
      if (activeEsRef.current) {
        try {
          activeEsRef.current.close();
        } catch (_) {}
        activeEsRef.current = null;
      }
      setIsCreating(false);
      if (typeof window !== "undefined") {
        try {
          localStorage.removeItem("lumen_active_creation_task");
        } catch (_) {}
      }
      flash("Proceso cancelado.");
      loadProjects();
    } catch (err: any) {
      setIsCreating(false);
      flash(`Error al cancelar: ${err.message}`);
    }
  }, [activeProjectId, pushLog, flash, loadProjects]);

  const resumeProject = useCallback(
    async (taskId: string) => {
      try {
        setIsCreating(true);
        setCreateStatusMessage("Reanudando proceso...");
        pushLog(`Reanudando proyecto ${taskId}...`, "ai");
        flash("Reanudando proyecto...");
        const res = await fetch(`/api/projects/${taskId}/resume`, { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Error al reanudar proyecto");
        attachCreationStream(taskId);
      } catch (err: any) {
        setIsCreating(false);
        flash(`Error al reanudar: ${err.message}`);
        pushLog(`Error al reanudar: ${err.message}`, "warn");
      }
    },
    [pushLog, flash, attachCreationStream],
  );

  const deleteProject = useCallback(
    async (id: string) => {
      try {
        pushLog(`Eliminando proyecto ${id}...`, "info");
        const res = await fetch(`/api/projects/${id}`, { method: "DELETE" });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Error al eliminar proyecto");
        }
        flash("Proyecto eliminado.");
        pushLog(`✓ Proyecto ${id} eliminado y espacio liberado`, "ai");
        await loadProjects();
        if (activeProjectId === id) {
          const remaining = projects.filter((p) => p.id !== id);
          if (remaining.length > 0) {
            loadProject(remaining[0].id);
          }
        }
      } catch (err: any) {
        flash(`Error al eliminar: ${err.message}`);
        pushLog(`Fallo al eliminar proyecto: ${err.message}`, "warn");
      }
    },
    [activeProjectId, projects, flash, pushLog, loadProjects, loadProject],
  );

  useEffect(() => {
    loadProjects();
    (window as any).openProject = (id: string) => {
      loadProject(id);
    };

    const checkActiveTasks = async () => {
      try {
        const res = await fetch("/api/tasks/active");
        if (res.ok) {
          const data = await res.json();
          if (data.active_tasks && data.active_tasks.length > 0) {
            const active = data.active_tasks[0];
            pushLog(`Reconectado a tarea activa: ${active.task_id}`, "ai");
            setCreateProgress(active.progress || 10);
            setCreateStatusMessage(active.message || "Procesando video...");
            attachCreationStream(active.task_id);
            return;
          }
        }

        const savedTaskId =
          typeof window !== "undefined" ? localStorage.getItem("lumen_active_creation_task") : null;
        if (savedTaskId) {
          const pRes = await fetch(`/api/progress/${savedTaskId}`);
          if (pRes.ok) {
            const pData = await pRes.json();
            if (pData.is_running) {
              attachCreationStream(savedTaskId);
            } else if (pData.completed) {
              if (typeof window !== "undefined") {
                try {
                  localStorage.removeItem("lumen_active_creation_task");
                } catch (_) {}
              }
              setIsCreating(false);
              loadProject(savedTaskId);
            } else {
              if (typeof window !== "undefined") {
                try {
                  localStorage.removeItem("lumen_active_creation_task");
                } catch (_) {}
              }
              setIsCreating(false);
            }
          } else {
            if (typeof window !== "undefined") {
              try {
                localStorage.removeItem("lumen_active_creation_task");
              } catch (_) {}
            }
            setIsCreating(false);
          }
        }
      } catch (_) {}
    };

    checkActiveTasks();

    return () => {
      if (activeEsRef.current) {
        try {
          activeEsRef.current.close();
        } catch (_) {}
      }
    };
  }, [loadProjects, loadProject, attachCreationStream, pushLog]);

  const selectProject = useCallback(
    (id: string) => {
      loadProject(id);
    },
    [loadProject],
  );

  const exportMaster = useCallback(
    async (opts?: { burnSubtitles?: boolean; style?: string; title?: string }) => {
      const targetId = activeProjectId || (projects.length > 0 ? projects[0].id : null);
      if (!targetId) {
        flash("No hay proyectos en el servidor para exportar");
        return;
      }
      const burnSubs = typeof opts?.burnSubtitles === "boolean" ? opts.burnSubtitles : overlays.captions;
      const subStyle = opts?.style || subtitleStyle;
      const downloadTitle = (opts?.title || activeProjectTitle || "video_master").trim();
      const safeBase = downloadTitle.replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "_") || `master_${targetId}`;
      const finalMp4Name = safeBase.toLowerCase().endsWith(".mp4") ? safeBase : `${safeBase}.mp4`;

      try {
        pushLog(`Guardando en Descargas: ${downloadTitle} (${burnSubs ? "Con subtítulos" : "Video limpio"})...`, "info");
        flash("Exportando directamente a tu carpeta de Descargas...");

        // 1. Petición directa a la API local para transferir a C:\Users\angel\Downloads
        let savedDirectly = false;
        try {
          const exportRes = await fetch(`/api/projects/${targetId}/export-to-downloads`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              burn_subtitles: burnSubs,
              style: subStyle,
              title: downloadTitle,
            }),
          });

          const exportData = await exportRes.json();
          if (exportRes.ok && exportData.ok) {
            savedDirectly = true;
            pushLog(`✓ ¡Video guardado en Descargas!: ${exportData.path}`, "ai");
            flash(`¡Guardado en Descargas!: ${exportData.filename}`);
          }
        } catch {
          savedDirectly = false;
        }

        // 2. Si falló la copia local directa, recurrir a la descarga estándar del navegador
        if (!savedDirectly) {
          const downloadUrl = `/api/projects/${targetId}/download/${encodeURIComponent(finalMp4Name)}?burn_subtitles=${burnSubs ? "true" : "false"}&style=${encodeURIComponent(subStyle)}`;
          const a = document.createElement("a");
          a.href = downloadUrl;
          a.download = finalMp4Name;
          document.body.appendChild(a);
          a.click();
          setTimeout(() => a.remove(), 1500);
          pushLog(`Descargando a través del navegador: ${finalMp4Name}`, "info");
        }
      } catch (e: any) {
        pushLog(`Fallo en exportación: ${e.message}`, "warn");
        flash(`Error al exportar: ${e.message}`);
      }
    },
    [activeProjectId, projects, activeProjectTitle, overlays.captions, subtitleStyle, pushLog, flash],
  );

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
        attachCreationStream(taskId);
      } catch (err: any) {
        setIsUploading(false);
        pushLog(`Fallo al importar video: ${err.message}`, "warn");
        flash(`Error: ${err.message}`);
      }
    },
    [pushLog, flash, selectedVoice, attachCreationStream],
  );

  const createVideo = useCallback(
    async (topic: string, opts?: { duration?: number; style?: string; aspect_ratio?: Ratio }) => {
      const cleanTopic = topic.trim();
      if (!cleanTopic) return null;

      try {
        const targetRatio = opts?.aspect_ratio || ratio || "16:9";
        if (opts?.aspect_ratio && opts.aspect_ratio !== ratio) {
          setRatio(opts.aspect_ratio);
        }
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
            aspect_ratio: targetRatio,
            style: opts?.style || "divulgacion",
            voice: selectedVoice,
          }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Error al iniciar la creación");

        const taskId = data.task_id || data.project_id;
        pushLog(`Tarea iniciada con ID: ${taskId}`, "info");
        attachCreationStream(taskId);
        return taskId;
      } catch (err: any) {
        setIsCreating(false);
        setCreateStatusMessage(`Fallo: ${err.message}`);
        pushLog(`Error al crear video: ${err.message}`, "warn");
        flash(`Error: ${err.message}`);
        return null;
      }
    },
    [ratio, selectedVoice, pushLog, flash, attachCreationStream],
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
    deleteProject,
    cancelCreation,
    resumeProject,
    selectedVoice,
    setSelectedVoice,
    playingVoiceId,
    previewVoice,
    captions,
    setCaptions,
    updateCaption,
    subtitleStyle,
    setSubtitleStyle,
    subtitleFont,
    setSubtitleFont,
    isMuted,
    setIsMuted,
    toggleMute,
    setDuration,
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

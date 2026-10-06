document.addEventListener("DOMContentLoaded", () => {
    const $ = (id) => document.getElementById(id);
    const form = $("uploadForm");
    const fileInput = $("videoFileInput");
    const dropzone = $("dropzone");
    const controls = $("uploadControls");
    const startBtn = $("startBtn");
    const startBtnText = $("startBtnText");
    const fileBadge = $("selectedFileBadge");
    const fileName = $("selectedFileName");
    const feed = $("activityFeed");
    const cancelBtn = $("cancelTaskBtn");
    const emptyFeed = $("emptyActivity");
    const results = $("resultsSection");
    const statusBadge = $("connectionStatus");
    const phaseIds = ["phase-input", "phase-analyze", "phase-cut", "phase-enrich", "phase-render"];
    const stageLabels = {
        init: "Preparando la tarea", queued: "En cola", inspect: "Revisando el archivo",
        transcribe: "Transcripción local", gemini: "Análisis con Gemini", silence: "Detección de pausas",
        visual: "Análisis visual local", enrich: "B-Roll y búsqueda de fuentes", cards: "Diseño de apoyos visuales", quality: "Control técnico",
        render: "Render del video", subtitles: "Composición y subtítulos",
        finalizing: "Short vertical", done: "Edición terminada", error: "Edición detenida",
        cancelling: "Cancelando edición", cancelled: "Edición cancelada",
    };
    const stagePhase = {
        init: 0, queued: 0, inspect: 0, transcribe: 0,
        gemini: 1, silence: 2, visual: 2, enrich: 3, cards: 3, quality: 3,
        render: 4, subtitles: 4, finalizing: 4, done: 4,
    };
    const fmtDuration = (seconds) => {
        const s = Math.max(0, Math.floor(seconds || 0));
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = s % 60;
        return h ? `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`
            : `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
    };
    const ageLabel = (seconds) => seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
    const eventTime = (value) => {
        const date = value ? new Date(value) : new Date();
        return Number.isNaN(date.valueOf()) ? "—" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    };
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

    let selectedFile = null;
    let activeStream = null;
    let currentState = null;
    let renderedEvents = "";
    let didShowResults = false;
    let connectionLost = false;
    let observedTaskId = "";
    let legacyStartedAt = null;
    let legacyStepStartedAt = null;
    let legacyUpdatedAt = null;
    let legacyStep = "";
    let legacyMessage = "";
    let legacyEvents = [];
    let editorState = null;
    let selectedEditorItem = null;
    let editorDirty = false;
    let thumbnailsKey = "";

    function percent(value, duration) {
        return `${Math.max(0, Math.min(100, (Number(value || 0) / Math.max(1, Number(duration || 1))) * 100))}%`;
    }

    function setPreviewTime(seconds) {
        const preview = $("projectPreview");
        if (!Number.isFinite(Number(seconds))) return;
        preview.currentTime = Math.max(0, Number(seconds));
    }

    function waitForEvent(element, eventName) {
        return new Promise((resolve, reject) => {
            element.addEventListener(eventName, resolve, { once: true });
            element.addEventListener("error", () => reject(new Error("No se pudo leer la vista previa.")), { once: true });
        });
    }

    async function buildTimelineThumbnails(source, duration) {
        const strip = $("timelineThumbnails");
        const status = $("thumbnailStatus");
        const key = `${source}|${duration}`;
        if (key === thumbnailsKey) return;
        thumbnailsKey = key;
        strip.replaceChildren();
        strip.hidden = true;
        if (!("VideoFrame" in window) || !source || duration <= 0) {
            status.textContent = "La vista previa está lista; este navegador no expone miniaturas WebCodecs.";
            return;
        }
        status.textContent = "Generando miniaturas locales con WebCodecs…";
        const sampler = document.createElement("video");
        sampler.preload = "auto";
        sampler.muted = true;
        sampler.src = source;
        try {
            await waitForEvent(sampler, "loadedmetadata");
            const count = Math.max(4, Math.min(10, Math.ceil(duration / 45)));
            for (let index = 0; index < count; index += 1) {
                sampler.currentTime = Math.min(Math.max(0, duration - 0.05), duration * (index + 0.5) / count);
                await waitForEvent(sampler, "seeked");
                const frame = new VideoFrame(sampler);
                const canvas = document.createElement("canvas");
                canvas.width = 160; canvas.height = 90;
                canvas.getContext("2d").drawImage(frame, 0, 0, canvas.width, canvas.height);
                frame.close();
                const button = document.createElement("button");
                button.type = "button";
                button.className = "timeline-thumbnail";
                const at = duration * (index + 0.5) / count;
                button.title = `Ir a ${fmtDuration(at)}`;
                button.append(canvas);
                button.addEventListener("click", () => setPreviewTime(at));
                strip.append(button);
            }
            strip.hidden = false;
            status.textContent = "Miniaturas listas: pulsa una para mover la previsualización.";
        } catch (_error) {
            if (key === thumbnailsKey) status.textContent = "La vista previa sigue disponible; no se pudieron generar las miniaturas.";
        } finally {
            sampler.removeAttribute("src"); sampler.load();
        }
    }

    function markEditorDirty() {
        editorDirty = true;
        $("saveTimelineBtn").disabled = false;
        $("exportTimelineBtn").disabled = true;
        $("editorSaveState").textContent = "Tienes cambios sin guardar en este proyecto.";
    }

    function getSelectedItem() {
        if (!editorState || !selectedEditorItem) return null;
        const list = selectedEditorItem.type === "card" ? editorState.cards : editorState.brolls;
        return list.find((item) => item.id === selectedEditorItem.id) || null;
    }

    function renderInspector() {
        const inspector = $("editorInspector");
        const item = getSelectedItem();
        if (!item) {
            inspector.innerHTML = "<b>Selecciona un elemento de la línea de tiempo</b><p>Podrás cambiar su momento, duración, posición o retirarlo antes de una nueva exportación.</p>";
            return;
        }
        const kind = selectedEditorItem.type === "card" ? "Tarjeta verificada" : "Apoyo B-Roll";
        const title = selectedEditorItem.type === "card" ? item.headline : item.concept;
        const end = selectedEditorItem.type === "card" ? Number(item.start) + Number(item.duration || 7) : item.end;
        const context = selectedEditorItem.type === "card" ? (item.body || item.note || item.claim) : item.status;
        const positions = ["auto", "upper_left", "upper_right", "lower_left", "lower_right"];
        inspector.innerHTML = `<b>${esc(kind)} · ${esc(title)}</b><p>${esc(context || "Aún se está preparando.")}</p>
            <label>Activo <input id="editEnabled" type="checkbox" ${item.enabled === false ? "" : "checked"}></label>
            <label>Inicio <input id="editStart" type="number" min="0" step="0.1" value="${Number(item.start || 0).toFixed(1)}"></label>
            <label>Fin <input id="editEnd" type="number" min="0" step="0.1" value="${Number(end || 0).toFixed(1)}"></label>
            ${selectedEditorItem.type === "card" ? `<label>Posición <select id="editPosition">${positions.map((position) => `<option value="${position}" ${item.position === position ? "selected" : ""}>${position.replace("_", " ")}</option>`).join("")}</select></label>
            ${item.avatar_spoken_text ? `<div style="margin:8px 0 4px 0; font-size:12px; color:#38bdf8; background:rgba(56,189,248,0.1); border-left:3px solid #38bdf8; padding:6px 10px; border-radius:6px; line-height:1.4;">⚡ <b>KAI Copilot (Voz Neural):</b><br>«${esc(item.avatar_spoken_text)}»</div>` : ""}` : ""}`;
        $("editEnabled").addEventListener("change", (event) => { item.enabled = event.target.checked; markEditorDirty(); renderTimeline(); });
        $("editStart").addEventListener("change", (event) => {
            item.start = Math.max(0, Number(event.target.value || 0));
            if (selectedEditorItem.type === "card") item.duration = Math.max(4.5, Number(item.duration || 7));
            else item.end = Math.max(item.start + 1, Number(item.end || item.start + 1));
            markEditorDirty(); renderTimeline();
        });
        $("editEnd").addEventListener("change", (event) => {
            const value = Math.max(Number(item.start || 0) + (selectedEditorItem.type === "card" ? 4.5 : 1), Number(event.target.value || 0));
            if (selectedEditorItem.type === "card") item.duration = Math.min(12, value - Number(item.start || 0));
            else item.end = value;
            markEditorDirty(); renderTimeline();
        });
        if (selectedEditorItem.type === "card") $("editPosition").addEventListener("change", (event) => { item.position = event.target.value; markEditorDirty(); });
    }

    function timelineClip(item, type, duration) {
        const button = document.createElement("button");
        const end = type === "card" ? Number(item.start) + Number(item.duration || 7) : Number(item.end);
        button.type = "button";
        button.className = `clip clip-${type}${item.enabled === false ? " is-muted" : ""}${selectedEditorItem?.type === type && selectedEditorItem.id === item.id ? " is-selected" : ""}`;
        button.style.left = percent(item.start, duration);
        button.style.width = `max(2.2%, ${percent(Math.max(1, end - Number(item.start)), duration)})`;
        button.textContent = type === "card" ? item.headline : (type === "broll" ? item.concept : item.title);
        button.title = `${button.textContent} · ${fmtDuration(item.start)}`;
        button.addEventListener("click", () => {
            selectedEditorItem = (type === "card" || type === "broll") ? { type, id: item.id } : null;
            setPreviewTime(item.start);
            renderTimeline();
            renderInspector();
        });
        return button;
    }

    function renderTimeline() {
        if (!editorState) return;
        const duration = Number(editorState.duration || 1);
        const ruler = $("timelineRuler");
        const tracks = $("timelineTracks");
        ruler.replaceChildren();
        tracks.replaceChildren();
        const marks = Math.max(4, Math.min(12, Math.ceil(duration / 60)));
        for (let i = 0; i <= marks; i += 1) {
            const label = document.createElement("span");
            label.style.left = `${(i / marks) * 100}%`;
            label.textContent = fmtDuration((duration / marks) * i);
            ruler.append(label);
        }
        const rows = [
            ["Tarjetas", "card", editorState.cards || []],
            ["B-Roll", "broll", editorState.brolls || []],
            ["Shorts", "short", editorState.shorts || []],
            ["Cortes", "cut", editorState.cuts || []],
        ];
        rows.forEach(([label, type, items]) => {
            const row = document.createElement("div"); row.className = "track";
            const name = document.createElement("span"); name.className = "track-name"; name.textContent = label;
            const lane = document.createElement("div"); lane.className = "track-lane";
            items.forEach((item, index) => {
                const mapped = type === "cut" ? { id: `cut-${index}`, start: item.start_sec, end: item.end_sec, title: "Pausa eliminada", enabled: true } : item;
                lane.append(timelineClip(mapped, type, duration));
            });
            row.append(name, lane); tracks.append(row);
        });
    }

    function renderStudio(editor, previewUrl) {
        if (!editor) return;
        const changed = JSON.stringify(editor) !== JSON.stringify(editorState);
        if (changed && !editorDirty) editorState = JSON.parse(JSON.stringify(editor));
        if (!editorState) editorState = JSON.parse(JSON.stringify(editor));
        const duration = Number(editorState.duration || 0);
        $("studioSection").hidden = false;
        $("exportTimelineBtn").disabled = editorDirty || !observedTaskId;
        $("studioSummary").textContent = `${(editorState.cards || []).length} tarjetas · ${(editorState.brolls || []).length} B-Rolls · ${(editorState.shorts || []).length} Shorts`;
        $("studioIntro").textContent = editorState.summary || "El agente está estructurando los elementos de la edición.";
        $("previewDuration").textContent = fmtDuration(duration);
        const preview = $("projectPreview");
        if (previewUrl && preview.dataset.source !== previewUrl) {
            preview.dataset.source = previewUrl;
            preview.src = previewUrl;
            preview.load();
            $("previewEmpty").hidden = true;
            preview.addEventListener("loadedmetadata", () => buildTimelineThumbnails(previewUrl, Number(preview.duration || duration)), { once: true });
        }
        $("timelineCursor").max = String(Math.max(1, duration));
        renderTimeline(); renderInspector();
    }

    async function openProject(projectId) {
        const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "No se pudo abrir el proyecto.");
        observedTaskId = projectId;
        editorDirty = false;
        selectedEditorItem = null;
        renderStudio(data.editor, `/api/projects/${encodeURIComponent(projectId)}/preview`);
        if (data.project?.result) showResults(data.project.result);
        const url = new URL(window.location.href);
        url.searchParams.delete("task");
        url.searchParams.set("project", projectId);
        window.history.replaceState({}, "", url);
    }

    async function loadSavedProjects() {
        try {
            const response = await fetch("/api/projects");
            const data = await response.json();
            const projects = Array.isArray(data.projects) ? data.projects : [];
            const card = $("savedProjectsCard");
            const list = $("savedProjectsList");
            list.replaceChildren();
            card.hidden = !projects.length;
            projects.forEach((project) => {
                const row = document.createElement("div");
                row.className = "saved-project-row";
                row.style.cssText = "display:flex; align-items:center; gap:6px; width:100%;";

                const button = document.createElement("button");
                button.type = "button"; button.className = "saved-project";
                button.style.flex = "1";
                const copy = document.createElement("span");
                const name = document.createElement("b"); name.textContent = project.name || "Video sin nombre";
                const detail = document.createElement("span"); detail.textContent = project.has_result ? "Edición terminada" : project.has_plan ? "Plan listo para revisar" : "Carga conservada · reanudar sin subir";
                copy.append(name, detail);
                const status = document.createElement("em"); status.textContent = project.status || "guardado";
                button.append(copy, status);
                button.addEventListener("click", () => {
                    const action = project.has_plan ? openProject(project.id) : fetch(`/api/projects/${encodeURIComponent(project.id)}/resume`, { method: "POST" })
                        .then((response) => response.json().then((data) => ({ response, data })))
                        .then(({ response, data }) => {
                            if (!response.ok) throw new Error(data.detail || "No se pudo reanudar el proyecto.");
                            localStorage.setItem("currentTaskId", project.id);
                            listen(project.id);
                        });
                    action.catch((error) => {
                        $("pipelineStatusText").textContent = error.message;
                        setConnection("error", "No se pudo abrir");
                    });
                });

                const delBtn = document.createElement("button");
                delBtn.type = "button";
                delBtn.className = "del-project-btn";
                delBtn.title = "Eliminar proyecto y liberar espacio";
                delBtn.textContent = "×";
                delBtn.style.cssText = "width:28px; height:28px; border-radius:8px; border:1px solid var(--border); background:var(--surface-inset); color:var(--tertiary); cursor:pointer; font-size:16px; display:grid; place-items:center; flex-shrink:0;";
                delBtn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    if (!confirm(`¿Eliminar proyecto «${project.name}»? Se liberará el espacio ocupado.`)) return;
                    try {
                        const res = await fetch(`/api/projects/${encodeURIComponent(project.id)}`, { method: "DELETE" });
                        if (res.ok) {
                            loadSavedProjects();
                        }
                    } catch (err) {
                        console.error("Error eliminando proyecto:", err);
                    }
                });

                row.append(button, delBtn);
                list.append(row);
            });
        } catch { /* la edición nueva funciona aunque no se pueda leer el historial */ }
    }

    const cleanupBtn = $("cleanupStorageBtn");
    if (cleanupBtn) {
        cleanupBtn.addEventListener("click", async () => {
            cleanupBtn.disabled = true;
            cleanupBtn.textContent = "Limpiando…";
            try {
                const res = await fetch("/api/cleanup", { method: "POST" });
                const data = await res.json();
                alert(`Limpieza completada:\n• Espacio liberado: ${data.freed_mb || 0} MB (${data.freed_gb || 0} GB)\n• Archivos temporales eliminados: ${data.deleted_files || 0}`);
                loadSavedProjects();
            } catch (err) {
                alert("Error durante la limpieza: " + err.message);
            } finally {
                cleanupBtn.disabled = false;
                cleanupBtn.textContent = "🧹 Limpiar";
            }
        });
    }

    function setConnection(kind, label) {
        statusBadge.className = `live-badge ${kind ? `is-${kind}` : ""}`.trim();
        statusBadge.querySelector("span").textContent = label;
    }

    function paintPhases(step, failedStep) {
        phaseIds.forEach((id, index) => {
            const item = $(id);
            item.classList.remove("is-active", "is-complete", "is-error");
            if (step === "done") {
                item.classList.add("is-complete");
                return;
            }
            const current = stagePhase[step] ?? stagePhase[failedStep] ?? -1;
            if (step === "error" && index === (stagePhase[failedStep] ?? current)) item.classList.add("is-error");
            else if (current >= 0 && index < current) item.classList.add("is-complete");
            else if (current === index) item.classList.add("is-active");
        });
    }

    function renderActivity(events, error) {
        const list = Array.isArray(events) ? events.slice(-80) : [];
        if (error) list.push({ step: "error", message: `Error: ${error}`, at: new Date().toISOString() });
        const signature = JSON.stringify(list);
        if (signature === renderedEvents) return;
        renderedEvents = signature;
        feed.replaceChildren();
        if (!list.length) {
            feed.appendChild(emptyFeed);
            emptyFeed.hidden = false;
            $("activityCount").textContent = "0 eventos";
            return;
        }
        emptyFeed.hidden = true;
        list.forEach((event) => {
            const row = document.createElement("div");
            row.className = "activity-item";
            row.dataset.step = event.step || "";
            const marker = document.createElement("i");
            marker.className = "activity-marker";
            marker.setAttribute("aria-hidden", "true");
            const copy = document.createElement("div");
            copy.className = "activity-copy";
            const phase = document.createElement("span");
            phase.className = "activity-step";
            phase.textContent = stageLabels[event.step] || "Actividad";
            const message = document.createElement("span");
            message.textContent = event.message || "Actualización del proceso.";
            copy.append(phase, message);
            const time = document.createElement("time");
            time.dateTime = event.at || "";
            time.textContent = eventTime(event.at);
            row.append(marker, copy, time);
            feed.appendChild(row);
        });
        $("activityCount").textContent = `${list.length} ${list.length === 1 ? "evento" : "eventos"}`;
        feed.scrollTop = feed.scrollHeight;
    }

    function refreshClocks() {
        if (!currentState) return;
        const now = Date.now();
        const created = Date.parse(currentState.created_at || "");
        const stageStarted = Date.parse(currentState.step_started_at || "");
        const updated = Date.parse(currentState.updated_at || "");
        const active = !currentState.completed && !currentState.error;
        $("totalElapsedLabel").textContent = currentState.legacy_state ? "Desde reconexión" : "Tiempo total";
        $("totalElapsed").textContent = Number.isFinite(created) ? fmtDuration((now - created) / 1000) : "00:00";
        $("stageElapsed").textContent = Number.isFinite(stageStarted) ? fmtDuration((now - stageStarted) / 1000) : "00:00";
        const age = Number.isFinite(updated) ? Math.max(0, Math.floor((now - updated) / 1000)) : null;
        $("signalAge").textContent = age === null ? "—" : ageLabel(age);
        $("lastUpdateText").textContent = age === null ? "Esperando primera señal" : `Último reporte hace ${ageLabel(age)}`;

        const note = $("waitNote");
        if (active && age >= 25) {
            note.hidden = false;
            if (currentState.step === "gemini") {
                note.textContent = `Gemini aún no ha devuelto el plan de edición (${ageLabel(age)} desde la última respuesta real). Todavía no han empezado los cortes, la investigación ni el render. AetherCut cambiará de proyecto o detendrá esta etapa si se alcanza el límite de espera.`;
            } else {
                note.textContent = `Esta etapa sigue esperando una respuesta real desde hace ${ageLabel(age)}. La actividad de arriba muestra la última acción confirmada; no se están inventando avances.`;
            }
            setConnection("warning", "Sin señal reciente");
        } else if (active && connectionLost) {
            note.hidden = true;
            setConnection("warning", "Reconectando");
        } else if (active && activeStream) {
            note.hidden = true;
            setConnection("active", "Actualizando en vivo");
        } else if (!active) {
            note.hidden = true;
        }
    }

    function applyState(incomingState, taskId) {
        const state = { ...incomingState };
        state.legacy_state = !Array.isArray(state.events) || !state.updated_at;
        if (taskId !== observedTaskId) {
            observedTaskId = taskId;
            legacyStartedAt = null;
            legacyStepStartedAt = null;
            legacyUpdatedAt = null;
            legacyStep = "";
            legacyMessage = "";
            legacyEvents = [];
        }
        // Compatibilidad con tareas que empezaron antes de actualizar el servidor.
        if (!state.updated_at) {
            const now = new Date().toISOString();
            legacyStartedAt ||= now;
            const changed = state.step !== legacyStep || state.message !== legacyMessage;
            if (!legacyStepStartedAt || state.step !== legacyStep) legacyStepStartedAt = now;
            if (changed) {
                legacyUpdatedAt = now;
                legacyEvents.push({ step: state.step, progress: state.progress, message: state.message, at: now });
                legacyEvents = legacyEvents.slice(-80);
            }
            legacyStep = state.step || "";
            legacyMessage = state.message || "";
            state.created_at = legacyStartedAt;
            state.step_started_at = legacyStepStartedAt;
            state.updated_at = legacyUpdatedAt || now;
            state.events = legacyEvents;
        }
        currentState = state;
        const step = state.step || "init";
        const isError = Boolean(state.error);
        const isCancelled = Boolean(state.cancelled);
        const isDone = Boolean(state.completed) && !isCancelled;
        const cancelling = Boolean(state.cancel_requested);
        const active = !isError && !isDone && !isCancelled;
        $("statusTitle").textContent = isError ? "No se pudo completar la edición"
            : isCancelled ? "Edición cancelada"
                : cancelling ? "Cancelando edición"
            : isDone ? "Edición terminada"
                : (stageLabels[step] || "Procesando video");
        $("pipelineStatusText").textContent = isError ? state.error
            : isCancelled ? (state.message || "La edición se canceló.")
                : (state.message || "Esperando una actualización del proceso.");
        $("jobFileName").textContent = state.file_name || (selectedFile ? selectedFile.name : "Video en proceso");
        const percent = Math.max(0, Math.min(100, Number(state.progress || 0)));
        $("progressPctText").textContent = `${Math.round(percent)}%`;
        $("progressBarFill").style.width = `${percent}%`;
        $("progressBarFill").parentElement.setAttribute("aria-valuenow", String(Math.round(percent)));
        const icon = $("workIndicator");
        icon.classList.toggle("is-active", active);
        icon.classList.toggle("is-done", isDone);
        icon.classList.toggle("is-error", isError);
        paintPhases(step === "cancelling" || step === "cancelled" ? state.cancelled_step : step, state.failed_step);
        renderActivity(state.events, state.error);
        renderStudio(state.editor, state.preview_url);

        if (isCancelled) {
            setConnection("warning", "Cancelado");
            $("waitNote").hidden = true;
            controls.disabled = false;
            startBtn.disabled = !selectedFile;
            startBtnText.textContent = selectedFile ? "Procesar de nuevo" : "Selecciona un video";
            cancelBtn.hidden = true;
            localStorage.removeItem("currentTaskId");
            const url = new URL(window.location.href);
            url.searchParams.delete("task");
            window.history.replaceState({}, "", url);
        } else if (isError) {
            setConnection("error", "Requiere atención");
            $("waitNote").hidden = true;
            controls.disabled = false;
            startBtn.disabled = !selectedFile;
            startBtnText.textContent = selectedFile ? "Intentar de nuevo" : "Selecciona un video";
            cancelBtn.hidden = true;
            localStorage.removeItem("currentTaskId");
        } else if (isDone) {
            setConnection("", "Completado");
            $("waitNote").hidden = true;
            controls.disabled = false;
            startBtn.disabled = !selectedFile;
            startBtnText.textContent = selectedFile ? "Procesar de nuevo" : "Selecciona un video";
            cancelBtn.hidden = true;
            localStorage.removeItem("currentTaskId");
            const url = new URL(window.location.href);
            url.searchParams.delete("task");
            url.searchParams.set("project", taskId);
            window.history.replaceState({}, "", url);
            if (state.result && !didShowResults) {
                didShowResults = true;
                showResults(state.result);
            }
        } else {
            controls.disabled = true;
            startBtn.disabled = true;
            startBtnText.textContent = "Procesando video…";
            cancelBtn.hidden = !state.cancel_supported;
            cancelBtn.disabled = cancelling;
            cancelBtn.textContent = cancelling ? "Cancelando…" : "Cancelar edición";
        }
        refreshClocks();
    }

    function listen(taskId) {
        if (activeStream) activeStream.close();
        connectionLost = false;
        setConnection("active", "Conectando");
        activeStream = new EventSource(`/api/stream-progress/${encodeURIComponent(taskId)}`);
        activeStream.onopen = () => {
            connectionLost = false;
            setConnection("active", "Actualizando en vivo");
        };
        activeStream.onmessage = (event) => {
            let state;
            try { state = JSON.parse(event.data); }
            catch { return; }
            applyState(state, taskId);
            if (state.completed || state.error || state.cancelled) {
                activeStream.close();
                activeStream = null;
            }
        };
        activeStream.onerror = () => {
            connectionLost = true;
            setConnection("warning", "Reconectando");
            // EventSource vuelve a conectar por sí solo; se conserva el estado visible.
        };
    }

    cancelBtn.addEventListener("click", async () => {
        if (!observedTaskId || cancelBtn.disabled) return;
        cancelBtn.disabled = true;
        cancelBtn.textContent = "Solicitando…";
        try {
            const response = await fetch(`/api/cancel-task/${encodeURIComponent(observedTaskId)}`, { method: "POST" });
            let result = {};
            try { result = await response.json(); } catch { /* respuesta sin cuerpo JSON */ }
            if (!response.ok) throw new Error(result.detail || "No se pudo solicitar la cancelación.");
            cancelBtn.textContent = "Cancelando…";
            $("pipelineStatusText").textContent = result.message || "Cancelación solicitada.";
        } catch (error) {
            cancelBtn.disabled = false;
            cancelBtn.textContent = "Cancelar edición";
            $("pipelineStatusText").textContent = `No se pudo cancelar: ${error.message}`;
        }
    });

    function chooseFile(file) {
        if (!file) return;
        const allowed = [".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"];
        const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
        if (!allowed.includes(ext)) {
            selectedFile = null;
            fileBadge.hidden = true;
            startBtn.disabled = true;
            $("statusTitle").textContent = "Formato de video no admitido";
            $("pipelineStatusText").textContent = "Elige un archivo MP4, MOV, MKV, WEBM, AVI o M4V.";
            setConnection("error", "Revisa el archivo");
            return;
        }
        if (file.size > 2 * 1024 * 1024 * 1024) {
            selectedFile = null;
            fileBadge.hidden = true;
            startBtn.disabled = true;
            $("statusTitle").textContent = "El archivo supera el límite";
            $("pipelineStatusText").textContent = "El tamaño máximo de carga es 2 GB.";
            setConnection("error", "Revisa el tamaño");
            return;
        }
        selectedFile = file;
        fileName.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`;
        fileBadge.hidden = false;
        startBtn.disabled = false;
        startBtnText.textContent = "Iniciar edición";
        $("statusTitle").textContent = "Video listo para editar";
        $("pipelineStatusText").textContent = "Ajusta las opciones y comienza. El avance detallado aparecerá aquí.";
        $("jobFileName").textContent = file.name;
        $("progressPctText").textContent = "0%";
        $("progressBarFill").style.width = "0%";
        setConnection("", "Listo para iniciar");
    }

    function showResults(result) {
        results.hidden = false;
        $("masterVideoPlayer").src = result.master_video_url || "";
        $("downloadMasterBtn").href = result.master_video_url || "#";
        $("masterVideoPlayer").load();
        const hasShort = Boolean(result.short_video_url);
        $("shortContainer").hidden = !hasShort;
        if (hasShort) {
            $("shortVideoPlayer").src = result.short_video_url;
            $("downloadShortBtn").href = result.short_video_url;
            $("shortVideoPlayer").load();
        }
        const shortsList = $("shortsList");
        const shorts = Array.isArray(result.shorts) ? result.shorts : [];
        shortsList.replaceChildren();
        shortsList.hidden = shorts.length < 2;
        shorts.forEach((short, index) => {
            const link = document.createElement("a");
            link.href = short.url || "#";
            link.download = "";
            link.textContent = `Short ${index + 1}: ${short.title || "clip"}`;
            shortsList.append(link);
        });
        $("statCuts").textContent = result.silences_cut_count ?? 0;
        $("statBRolls").textContent = result.brolls_count ?? 0;
        $("statCards").textContent = result.cards_shown ?? 0;
        $("statTimeSaved").textContent = `${Number(result.time_saved_sec || 0).toFixed(1)} s`;
        renderFacts(result.cards || []);
        results.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    $("projectPreview").addEventListener("timeupdate", () => {
        const preview = $("projectPreview");
        $("previewCurrentTime").textContent = fmtDuration(preview.currentTime);
        $("timelineCursor").value = String(preview.currentTime || 0);
    });
    $("timelineCursor").addEventListener("input", (event) => setPreviewTime(event.target.value));

    $("saveTimelineBtn").addEventListener("click", async () => {
        if (!observedTaskId || !editorState || !editorDirty) return;
        const button = $("saveTimelineBtn");
        button.disabled = true;
        $("editorSaveState").textContent = "Guardando cambios de edición…";
        const payload = {
            cards: (editorState.cards || []).map((card) => ({ id: card.id, enabled: card.enabled !== false, start: card.start, duration: card.duration, position: card.position || "auto", avatar_spoken_text: card.avatar_spoken_text, avatar_enabled: card.avatar_enabled !== false })),
            brolls: (editorState.brolls || []).map((broll) => ({ id: broll.id, enabled: broll.enabled !== false, start: broll.start, end: broll.end })),
        };
        try {
            const response = await fetch(`/api/projects/${encodeURIComponent(observedTaskId)}/timeline`, {
                method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "No se pudieron guardar los cambios.");
            editorState = data.editor;
            editorDirty = false;
            $("exportTimelineBtn").disabled = false;
            $("editorSaveState").textContent = data.message || "Cambios guardados en este proyecto.";
            renderTimeline(); renderInspector();
        } catch (error) {
            $("editorSaveState").textContent = `No se guardaron los cambios: ${error.message}`;
            button.disabled = false;
        }
    });

    $("exportTimelineBtn").addEventListener("click", async () => {
        if (!observedTaskId || editorDirty) return;
        const button = $("exportTimelineBtn");
        button.disabled = true;
        $("editorSaveState").textContent = "Iniciando una nueva exportación…";
        try {
            const response = await fetch(`/api/projects/${encodeURIComponent(observedTaskId)}/export`, { method: "POST" });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "No se pudo iniciar la exportación.");
            didShowResults = false;
            listen(data.task_id);
        } catch (error) {
            $("editorSaveState").textContent = `No se pudo exportar: ${error.message}`;
            button.disabled = false;
        }
    });

    function renderFacts(cards) {
        const list = $("factsList");
        list.replaceChildren();
        $("factsWrap").hidden = !cards.length;
        const supported = cards.filter((card) => card.verdict === "supported").length;
        $("factsSummary").textContent = `${supported} de ${cards.length} confirmados`;
        const verdicts = {
            supported: ["ok", "Confirmado"],
            contradicted: ["bad", "Corregido"],
            insufficient: ["na", "Sin evidencia"],
        };
        cards.forEach((card) => {
            const [style, label] = verdicts[card.verdict] || verdicts.insufficient;
            const item = document.createElement("li");
            item.className = "fact";
            const sources = (card.sources || []).map((source) => {
                const link = /^https:\/\//i.test(source.url || "") ? source.url : "#";
                return `<a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${esc(source.domain || "fuente")}</a>`;
            }).join("");
            const detail = card.verdict === "supported" ? card.body
                : card.verdict === "contradicted" ? (card.note || "Se detectó una diferencia con las fuentes consultadas.")
                : (card.note || "No se encontró evidencia suficiente.");
            const avatarHtml = card.avatar_spoken_text
                ? `<div class="avatar-voice" style="margin-top:8px; font-size:12px; color:#38bdf8; background:rgba(56,189,248,0.08); padding:6px 10px; border-radius:6px; border-left:3px solid #38bdf8; display:flex; align-items:center; gap:6px;"><span>⚡ <b>KAI Copilot:</b></span> <span>«${esc(card.avatar_spoken_text)}»</span></div>`
                : "";
            item.innerHTML = `<div class="fact-top"><b>${esc(card.headline)}</b><span class="badge ${style}">${label}${card.shown ? " · en el video" : ""}</span></div>
                <p class="claim">Afirmación (${esc(card.at_sec)} s): ${esc(card.claim)}</p>
                <p>${esc(detail)}</p>${avatarHtml}${sources ? `<div class="srcs">${sources}</div>` : ""}`;
            list.appendChild(item);
        });
    }

    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("dragover", (event) => { event.preventDefault(); dropzone.classList.add("drag-active"); });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-active"));
    dropzone.addEventListener("drop", (event) => {
        event.preventDefault();
        dropzone.classList.remove("drag-active");
        chooseFile(event.dataTransfer.files?.[0]);
    });
    fileInput.addEventListener("change", () => chooseFile(fileInput.files?.[0]));
    $("removeFileBtn").addEventListener("click", () => {
        selectedFile = null;
        fileInput.value = "";
        fileBadge.hidden = true;
        startBtn.disabled = true;
        startBtnText.textContent = "Selecciona un video";
        $("jobFileName").textContent = "Sin archivo seleccionado";
        $("statusTitle").textContent = "Carga un video para empezar";
        $("pipelineStatusText").textContent = "Aquí verás qué etapa está activa y la última acción reportada por el proceso.";
    });
    $("silenceThreshold").addEventListener("input", (event) => {
        $("silenceVal").textContent = `${Number(event.target.value).toFixed(1)} s`;
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!selectedFile) return;
        controls.disabled = true;
        startBtn.disabled = true;
        results.hidden = true;
        didShowResults = false;
        renderedEvents = "";
        feed.replaceChildren(emptyFeed);
        emptyFeed.hidden = false;
        $("totalElapsed").textContent = "00:00";
        $("stageElapsed").textContent = "00:00";
        $("signalAge").textContent = "—";
        $("waitNote").hidden = true;
        setConnection("active", "Subiendo video");
        $("statusTitle").textContent = "Subiendo el video";
        $("pipelineStatusText").textContent = "La carga se envía al servidor local; al terminar comenzará el análisis.";
        $("jobFileName").textContent = selectedFile.name;
        $("progressPctText").textContent = "5%";
        $("progressBarFill").style.width = "5%";

        const body = new FormData();
        body.append("video", selectedFile);
        body.append("silence_threshold", $("silenceThreshold").value);
        body.append("enable_broll", $("enableBRoll").checked);
        body.append("enable_cards", $("enableCards").checked);
        body.append("enable_captions", $("enableCaptions").checked);
        body.append("enable_shorts", $("enableShorts").checked);
        try {
            const data = await new Promise((resolve, reject) => {
                const request = new XMLHttpRequest();
                request.open("POST", "/api/process-video");
                request.upload.onprogress = (progress) => {
                    if (!progress.lengthComputable) return;
                    const uploadPct = progress.loaded / progress.total;
                    $("statusTitle").textContent = "Subiendo el video al servidor local";
                    $("pipelineStatusText").textContent = `${(progress.loaded / 1024 / 1024).toFixed(1)} de ${(progress.total / 1024 / 1024).toFixed(1)} MB recibidos.`;
                    $("progressPctText").textContent = `${Math.round(uploadPct * 100)}%`;
                    $("progressBarFill").style.width = `${uploadPct * 100}%`;
                };
                request.onload = () => {
                    let payload = {};
                    try { payload = JSON.parse(request.responseText); } catch { /* error de respuesta */ }
                    if (request.status >= 200 && request.status < 300) resolve(payload);
                    else reject(new Error(payload.detail || "No se pudo cargar el video."));
                };
                request.onerror = () => reject(new Error("Se perdió la conexión durante la carga."));
                request.send(body);
            });
            localStorage.setItem("currentTaskId", data.task_id);
            listen(data.task_id);
        } catch (error) {
            controls.disabled = false;
            startBtn.disabled = false;
            startBtnText.textContent = "Intentar de nuevo";
            setConnection("error", "Error de carga");
            $("statusTitle").textContent = "No se pudo iniciar la tarea";
            $("pipelineStatusText").textContent = error.message;
        }
    });

    setInterval(refreshClocks, 1000);
    const currentUrl = new URLSearchParams(window.location.search);
    const taskFromUrl = currentUrl.get("task");
    const projectFromUrl = currentUrl.get("project");
    const savedTaskId = localStorage.getItem("currentTaskId") || taskFromUrl;
    if (taskFromUrl) localStorage.setItem("currentTaskId", taskFromUrl);
    if (savedTaskId) {
        controls.disabled = true;
        startBtn.disabled = true;
        $("statusTitle").textContent = "Recuperando el estado de la edición";
        $("pipelineStatusText").textContent = "Reconectando con el servidor local…";
        listen(savedTaskId);
    }
    if (projectFromUrl && !savedTaskId) {
        openProject(projectFromUrl).catch(() => { /* el proyecto puede haberse movido o eliminado */ });
    }
    loadSavedProjects();
});

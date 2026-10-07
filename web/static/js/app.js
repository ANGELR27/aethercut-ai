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
        research: "Investigación web en vivo", script: "Redacción de guión KAI", voice: "Voz neural de KAI",
        avatar: "Animación y Lip-Sync KAI", broll: "Fondos y tarjetas Bento",
        render: "Render del video", subtitles: "Composición y subtítulos",
        finalizing: "Short vertical", done: "Edición terminada", error: "Edición detenida",
        cancelling: "Cancelando edición", cancelled: "Edición cancelada",
    };
    const stagePhase = {
        init: 0, queued: 0, inspect: 0, transcribe: 0, research: 0,
        gemini: 1, script: 1,
        silence: 2, visual: 2, voice: 2, avatar: 2,
        enrich: 3, cards: 3, quality: 3, broll: 3,
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
    let activeMode = "streamer";


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
        if (activeMode === "studio") $("studioSection").hidden = false;
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

        // Asegurar que el modo esté en streamer para que el monitor y controles sean visibles
        switchMode("streamer");

        // Reactivar y desbloquear botón de transmisión
        const startStreamerBtn = $("startStreamerBtn");
        const startStreamerBtnText = $("startStreamerBtnText");
        if (startStreamerBtn) {
            startStreamerBtn.disabled = false;
            if (startStreamerBtnText) startStreamerBtnText.textContent = "🚀 Iniciar Transmisión de KAI";
        }

        const previewUrl = `/api/projects/${encodeURIComponent(projectId)}/preview`;
        if (data.project?.result) {
            didShowResults = true;
            showResults(data.project.result, projectId);
        } else {
            const previewBox = $("previewContainer");
            if (previewBox) {
                previewBox.hidden = false;
                previewBox.style.display = "block";
            }
            const dropWrap = $("copilotDropWrap");
            if (dropWrap) {
                dropWrap.hidden = true;
                dropWrap.style.display = "none";
            }
            const preview = $("projectPreview");
            if (preview) {
                preview.hidden = false;
                preview.style.display = "block";
                preview.controls = false;
                preview.volume = 1;
                preview.muted = false;
                preview.src = previewUrl;
                preview.load();
            }
            const monitorBar = $("monitorDownloadBar");
            if (monitorBar) {
                monitorBar.hidden = false;
                monitorBar.style.display = "flex";
            }
            const dlBtn = $("downloadMasterBtn");
            if (dlBtn) {
                dlBtn.href = "#";
                dlBtn.onclick = (e) => {
                    e.preventDefault();
                    triggerDownload(`/api/projects/${encodeURIComponent(projectId)}/download`, `KAI_${projectId}.mp4`);
                };
            }
        }

        if (data.editor) {
            renderStudio(data.editor, previewUrl);
        }

        const url = new URL(window.location.href);
        url.searchParams.delete("task");
        url.searchParams.set("project", projectId);
        window.history.replaceState({}, "", url);
    }

    let allLoadedProjects = [];
    let currentProjectFilter = "all";
    let currentProjectSearch = "";

    function renderProjectsGrid() {
        const list = $("savedProjectsList");
        if (!list) return;
        list.replaceChildren();

        let filtered = allLoadedProjects.filter(p => {
            const matchesSearch = !currentProjectSearch || (p.name || "").toLowerCase().includes(currentProjectSearch.toLowerCase());
            const st = (p.status || "").toLowerCase();
            let matchesFilter = true;
            if (currentProjectFilter === "done") matchesFilter = (st === "done" || p.has_result);
            else if (currentProjectFilter === "progress") matchesFilter = (st !== "done" && !p.has_result && st !== "error");
            return matchesSearch && matchesFilter;
        });

        if (!filtered.length) {
            const empty = document.createElement("div");
            empty.style.cssText = "grid-column: 1 / -1; color:var(--text-muted); font-size:13px; text-align:center; padding:36px; background:rgba(255,255,255,0.02); border-radius:14px; border:1px dashed rgba(255,255,255,0.08);";
            empty.textContent = currentProjectSearch ? "No se encontraron proyectos con ese criterio." : "No hay proyectos guardados en esta categoría.";
            list.append(empty);
            return;
        }

        filtered.forEach((project) => {
            const card = document.createElement("div");
            card.className = "saved-project-card";

            const header = document.createElement("div");
            header.className = "saved-project-card-header";

            const left = document.createElement("div");
            left.style.cssText = "display:flex; align-items:flex-start; gap:10px;";
            const iconBadge = document.createElement("div");
            iconBadge.className = "project-icon-badge";
            iconBadge.textContent = project.has_result ? "🎬" : "📝";

            const title = document.createElement("h4");
            title.className = "saved-project-card-title";
            title.textContent = project.name || "Transmisión sin título";
            left.append(iconBadge, title);

            const st = (project.status || "done").toLowerCase();
            const statusBadge = document.createElement("span");
            statusBadge.className = `saved-project-badge ${st === "done" ? "badge-done" : st === "error" ? "badge-error" : "badge-render"}`;
            statusBadge.textContent = st === "done" ? "Listo" : st === "error" ? "Error" : "En curso";
            header.append(left, statusBadge);

            const metaRow = document.createElement("div");
            metaRow.className = "saved-project-meta-row";
            const dt = project.updated_at ? new Date(project.updated_at).toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
            const metaText = document.createElement("span");
            metaText.textContent = dt ? `Actualizado ${dt}` : "Reciente";

            const actions = document.createElement("div");
            actions.className = "saved-project-actions";

            const openBtn = document.createElement("button");
            openBtn.type = "button";
            openBtn.className = "project-open-btn";
            openBtn.innerHTML = `<span>Abrir</span> <span>→</span>`;
            openBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                openProject(project.id).catch((error) => console.error("Error abriendo proyecto:", error));
            });

            const delBtn = document.createElement("button");
            delBtn.type = "button";
            delBtn.className = "del-project-btn";
            delBtn.title = "Eliminar proyecto";
            delBtn.innerHTML = `✕`;
            delBtn.addEventListener("click", async (e) => {
                e.stopPropagation();
                if (!confirm(`¿Eliminar proyecto «${project.name}»? Se liberará el espacio en disco.`)) return;
                try {
                    const res = await fetch(`/api/projects/${encodeURIComponent(project.id)}`, { method: "DELETE" });
                    if (res.ok) {
                        loadSavedProjects();
                    }
                } catch (err) {
                    console.error("Error eliminando:", err);
                }
            });

            actions.append(openBtn, delBtn);
            metaRow.append(metaText, actions);

            card.append(header, metaRow);
            card.addEventListener("click", () => {
                openProject(project.id).catch((error) => console.error("Error abriendo proyecto:", error));
            });
            list.append(card);
        });
    }

    async function loadSavedProjects() {
        try {
            const response = await fetch("/api/projects");
            const data = await response.json();
            allLoadedProjects = Array.isArray(data.projects) ? data.projects : [];
            const card = $("savedProjectsCard");
            
            if ($("tabModeProjects")?.classList.contains("active")) {
                if (card) card.hidden = false;
            }
            renderProjectsGrid();
        } catch { /* ignorar fallo silencioso de red */ }
    }

    $("projectSearchInput")?.addEventListener("input", (e) => {
        currentProjectSearch = e.target.value.trim();
        renderProjectsGrid();
    });

    document.querySelectorAll("#projectFilterPills .subcard-pill-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("#projectFilterPills .subcard-pill-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentProjectFilter = btn.dataset.filter || "all";
            renderProjectsGrid();
        });
    });

    $("refreshProjectsBtn")?.addEventListener("click", () => {
        loadSavedProjects();
    });

    const cleanupBtn = $("cleanupStorageBtn");
    if (cleanupBtn) {
        cleanupBtn.addEventListener("click", async () => {
            cleanupBtn.disabled = true;
            cleanupBtn.textContent = "Limpiando…";
            try {
                const res = await fetch("/api/cleanup", { method: "POST" });
                const data = await res.json();
                alert(`Limpieza completada:\n• Espacio liberado: ${data.freed_mb || 0} MB (${data.freed_gb || 0} GB)\n• Archivos temporales eliminados: ${data.deleted_files || 0}`);
            } catch (err) {
                alert("Error durante la limpieza: " + err.message);
            } finally {
                cleanupBtn.disabled = false;
                cleanupBtn.textContent = "🧹 Limpiar";
            }
        });
    }

    function setConnection(kind, label) {
        if (!statusBadge) return;
        statusBadge.className = `live-badge ${kind ? `is-${kind}` : ""}`.trim();
        const span = statusBadge.querySelector("span");
        if (span) {
            span.textContent = label;
        } else {
            statusBadge.textContent = label;
        }
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
        const donutText = $("donutPctText");
        const donutArc = $("donutProgressArc");
        const donutLabel = $("donutLabelText");
        if (donutText) donutText.textContent = `${Math.round(percent)}%`;
        if (donutArc) {
            donutArc.style.strokeDashoffset = 100 - percent;
        }
        if (donutLabel) donutLabel.textContent = isDone ? "Completado" : active ? "En emisión" : isError ? "Error" : "Listo";
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
            if ($("waitNote")) $("waitNote").hidden = true;
            controls.disabled = false;
            startBtn.disabled = !selectedFile;
            startBtnText.textContent = selectedFile ? "Procesar de nuevo" : "Selecciona un video";
            if (startStreamerBtn) {
                startStreamerBtn.disabled = false;
                startStreamerBtnText.textContent = "🚀 Iniciar Transmisión de KAI";
            }
            cancelBtn.hidden = true;
            localStorage.removeItem("currentTaskId");
            const url = new URL(window.location.href);
            url.searchParams.delete("task");
            window.history.replaceState({}, "", url);
        } else if (isError) {
            setConnection("error", "Requiere atención");
            if ($("waitNote")) $("waitNote").hidden = true;
            controls.disabled = false;
            startBtn.disabled = !selectedFile;
            startBtnText.textContent = selectedFile ? "Intentar de nuevo" : "Selecciona un video";
            if (startStreamerBtn) {
                startStreamerBtn.disabled = false;
                startStreamerBtnText.textContent = "🚀 Iniciar Transmisión de KAI";
            }
            cancelBtn.hidden = true;
            localStorage.removeItem("currentTaskId");
        } else if (isDone) {
            setConnection("", "Completado");
            if ($("waitNote")) $("waitNote").hidden = true;
            controls.disabled = false;
            startBtn.disabled = !selectedFile;
            startBtnText.textContent = selectedFile ? "Procesar de nuevo" : "Selecciona un video";
            if (startStreamerBtn) {
                startStreamerBtn.disabled = false;
                startStreamerBtnText.textContent = "🚀 Iniciar Transmisión de KAI";
            }
            cancelBtn.hidden = true;
            localStorage.removeItem("currentTaskId");
            const url = new URL(window.location.href);
            url.searchParams.delete("task");
            url.searchParams.set("project", taskId);
            window.history.replaceState({}, "", url);
            if (taskId) {
                openProject(taskId).catch(() => {
                    if (state.result && !didShowResults) {
                        didShowResults = true;
                        showResults(state.result, taskId);
                    }
                });
            } else if (state.result && !didShowResults) {
                didShowResults = true;
                showResults(state.result, taskId);
            }
        } else {
            controls.disabled = true;
            startBtn.disabled = true;
            startBtnText.textContent = "Procesando video…";
            if (startStreamerBtn) {
                startStreamerBtn.disabled = true;
                startStreamerBtnText.textContent = "Transmitiendo con KAI…";
            }
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
        const targetId = observedTaskId;
        cancelBtn.disabled = true;
        cancelBtn.textContent = "Cancelando…";
        try {
            const response = await fetch(`/api/cancel-task/${encodeURIComponent(targetId)}`, { method: "POST" });
            let result = {};
            try { result = await response.json(); } catch { /* respuesta sin cuerpo JSON */ }
            if (!response.ok) throw new Error(result.detail || "No se pudo cancelar el proceso.");
            
            // Limpieza inmediata de UI y estado local para permitir iniciar otro video al instante
            cancelBtn.hidden = true;
            cancelBtn.disabled = false;
            cancelBtn.textContent = "Cancelar Transmisión";
            controls.disabled = false;
            if (startStreamerBtn) {
                startStreamerBtn.disabled = false;
                startStreamerBtnText.textContent = "🚀 Iniciar Transmisión de KAI";
            }
            startBtn.disabled = !selectedFile;
            $("statusTitle").textContent = "Transmisión cancelada";
            $("pipelineStatusText").textContent = "Listo para iniciar una nueva transmisión.";
            setConnection("warning", "Cancelado");
            
            localStorage.removeItem("currentTaskId");
            const url = new URL(window.location.href);
            url.searchParams.delete("task");
            window.history.replaceState({}, "", url);
            
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            observedTaskId = null;
        } catch (error) {
            cancelBtn.disabled = false;
            cancelBtn.textContent = "Cancelar Transmisión";
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

    function showResults(result, explicitTaskId) {
        results.hidden = false;
        const videoUrl = result.master_video_url || result.media_url || "";
        const taskId = explicitTaskId || observedTaskId || "";
        if (taskId) observedTaskId = taskId;
        const cleanTitle = (result.title || "KAI_Broadcast").replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "_").slice(0, 40);
        const mp4Filename = `${cleanTitle || "KAI_Broadcast"}.mp4`;
        const downloadEndpoint = taskId ? `/api/projects/${taskId}/download` : (videoUrl || "#");
        const zipEndpoint = taskId ? `/api/projects/${taskId}/materials-zip` : "#";
        
        // 1. Cambiar a modo streamer para que la mesa de emisión y monitor estén activos
        switchMode("streamer");

        // Reactivar y dejar listo el botón de emisión
        const startStreamerBtn = $("startStreamerBtn");
        const startStreamerBtnText = $("startStreamerBtnText");
        if (startStreamerBtn) {
            startStreamerBtn.disabled = false;
            if (startStreamerBtnText) startStreamerBtnText.textContent = "🚀 Iniciar Transmisión de KAI";
        }

        // Mostrar Banner de Éxito 바로 visible bajo la barra de progreso
        const banner = $("broadcastCompleteBanner");
        if (banner) {
            banner.style.display = "flex";
            const bannerWatchBtn = $("bannerWatchBtn");
            if (bannerWatchBtn) {
                bannerWatchBtn.onclick = () => {
                    results.hidden = false;
                    setTimeout(() => results.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
                    const masterPlayer = $("masterVideoPlayer");
                    if (masterPlayer) masterPlayer.play().catch(() => {});
                };
            }
            const bannerDlBtn = $("bannerDownloadBtn");
            if (bannerDlBtn) {
                bannerDlBtn.href = "#";
                bannerDlBtn.onclick = (e) => {
                    e.preventDefault();
                    fetch(downloadEndpoint)
                        .then(r => r.blob())
                        .then(blob => {
                            const a = document.createElement("a");
                            a.href = URL.createObjectURL(blob);
                            a.download = mp4Filename;
                            document.body.appendChild(a);
                            a.click();
                            setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
                        })
                        .catch(() => window.open(downloadEndpoint, "_blank"));
                };
            }
        }

        // 2. Asegurarse absolutamente de que previewContainer esté visible y dropWrap oculto
        const previewBox = $("previewContainer");
        if (previewBox) {
            previewBox.hidden = false;
            previewBox.style.display = "block";
        }
        const dropWrap = $("copilotDropWrap");
        if (dropWrap) {
            dropWrap.hidden = true;
            dropWrap.style.display = "none";
        }

        // 3. Cargar video en el Monitor Principal superior (con Custom Studio HUD)
        const preview = $("projectPreview");
        const playUrl = taskId ? `/api/projects/${encodeURIComponent(taskId)}/preview` : videoUrl;
        if (preview && playUrl) {
            preview.hidden = false;
            preview.style.display = "block";
            preview.controls = false;
            preview.volume = 1;
            preview.muted = false;
            if (preview.src !== playUrl && !preview.src.endsWith(playUrl)) {
                preview.src = playUrl;
                preview.load();
            }
        }

        // 4. Cargar video en el Reproductor Cine Master del Apartado Exclusivo
        const masterPlayer = $("masterVideoPlayer");
        if (masterPlayer && playUrl) {
            masterPlayer.style.display = "block";
            masterPlayer.hidden = false;
            masterPlayer.controls = false;
            masterPlayer.volume = 1;
            masterPlayer.muted = false;
            if (masterPlayer.src !== playUrl && !masterPlayer.src.endsWith(playUrl)) {
                masterPlayer.src = playUrl;
                masterPlayer.load();
            }
        }

        // 5. Configurar botones de descarga con guardado directo y blob-fetch garantizando .MP4
        async function openFolder() {
            if (!taskId) return;
            try {
                const res = await fetch(`/api/projects/${taskId}/open-folder`, { method: "POST" });
                const d = await res.json();
                if (d.status === "ok") {
                    console.log("Carpeta abierta en Windows:", d.path);
                }
            } catch (err) {
                console.error("Error abriendo carpeta:", err);
            }
        }

        async function saveDirectToDownloads() {
            if (!taskId) return;
            try {
                const res = await fetch(`/api/projects/${taskId}/save-to-downloads`, { method: "POST" });
                const d = await res.json();
                if (d.status === "ok") {
                    alert(`✅ Video guardado directamente en Descargas:\n${d.path}`);
                    return;
                }
            } catch (err) {
                console.warn("Fallo guardado directo a Descargas, usando descarga de navegador:", err);
            }
            blobDownload(downloadEndpoint, mp4Filename);
        }

        function blobDownload(url, filename) {
            // Intentar guardado directo en Windows si es proyecto activo
            if (taskId && url.includes("/download")) {
                fetch(`/api/projects/${taskId}/save-to-downloads`, { method: "POST" })
                    .then(r => r.json())
                    .then(d => {
                        if (d.status === "ok") {
                            console.log("Guardado en descargas local:", d.path);
                        }
                    })
                    .catch(() => {});
            }

            const a = document.createElement("a");
            a.href = url;
            a.setAttribute("download", filename);
            document.body.appendChild(a);
            a.click();
            setTimeout(() => a.remove(), 1000);
        }

        const bannerFolderBtn = $("bannerFolderBtn");
        if (bannerFolderBtn) {
            bannerFolderBtn.onclick = (e) => { e.preventDefault(); openFolder(); };
        }

        const bannerDlBtn = $("bannerDownloadBtn");
        if (bannerDlBtn) {
            bannerDlBtn.href = downloadEndpoint;
            bannerDlBtn.onclick = (e) => { e.preventDefault(); saveDirectToDownloads(); };
        }

        const dlBtn = $("downloadMasterBtn");
        if (dlBtn) {
            dlBtn.href = downloadEndpoint;
            dlBtn.onclick = (e) => { e.preventDefault(); saveDirectToDownloads(); };
        }

        const dlSec = $("downloadMasterBtnSec");
        if (dlSec) {
            dlSec.href = downloadEndpoint;
            dlSec.onclick = (e) => { e.preventDefault(); saveDirectToDownloads(); };
        }

        const zipBtn = $("downloadZipBtn");
        if (zipBtn) {
            zipBtn.href = zipEndpoint;
            zipBtn.onclick = (e) => {
                e.preventDefault();
                const a = document.createElement("a");
                a.href = zipEndpoint;
                a.setAttribute("download", `${cleanTitle}_Materiales.zip`);
                document.body.appendChild(a);
                a.click();
                setTimeout(() => a.remove(), 1000);
            };
            zipBtn.hidden = !taskId;
        }

        const openFBtn = $("openFolderBtn");
        if (openFBtn) {
            openFBtn.hidden = !taskId;
            openFBtn.onclick = (e) => { e.preventDefault(); openFolder(); };
        }

        // 6. Barra de descarga del monitor superior
        const monitorBar = $("monitorDownloadBar");
        if (monitorBar) {
            monitorBar.hidden = false;
            monitorBar.style.display = "flex";
        }

        // 7. Textos y métricas del Apartado Exclusivo
        if ($("resVideoTitle")) $("resVideoTitle").textContent = result.title || "Producción KAI Master";
        if ($("resVideoSub")) $("resVideoSub").textContent = `Tema: ${result.topic || ""} · Duración: ${fmtDuration(result.duration || 0)} · Formato: 1080p FHD Broadcast`;
        if ($("resScenesCount")) $("resScenesCount").textContent = (result.scenes || []).length || (result.scenes_count || 0);

        // 8. Desglose visual de escenas dirigidas
        const scenesList = $("resScenesList");
        const scenes = Array.isArray(result.scenes) ? result.scenes : [];
        if (scenesList) {
            scenesList.replaceChildren();
            const typeBadges = {
                "avatar_cam": "👤 Presentador KAI",
                "video_reaction": "🎬 Video Reacción (PIP)",
                "card_focus": "📊 Tarjeta Bento Clave",
                "chat_debate": "💬 Debate en Vivo",
                "breaking_news": "🚨 Titular Urgente"
            };
            scenes.forEach((sc, idx) => {
                const scCard = document.createElement("div");
                scCard.style.cssText = "background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:10px 12px; display:flex; flex-direction:column; gap:4px; transition:border-color 0.2s;";
                const typeLabel = typeBadges[sc.type] || sc.type;
                scCard.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="font-size:12px; color:#fff;">Escena ${sc.id || (idx + 1)}: ${sc.name || "Escena"}</strong>
                        <span style="font-size:10px; background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; color:var(--accent-ivory); font-weight:600;">${sc.emotion || "normal"}</span>
                    </div>
                    <span style="font-size:11px; color:var(--text-muted);">${typeLabel}</span>
                `;
                scenesList.append(scCard);
            });
        }

        // 9. Cargar lista de materiales generados desde el servidor
        if (taskId) {
            fetch(`/api/projects/${taskId}/materials`).then(r => r.json()).then(mat => {
                const filesList = $("resFilesList");
                if (filesList && Array.isArray(mat.files) && mat.files.length) {
                    filesList.replaceChildren();
                    mat.files.forEach(f => {
                        const pill = document.createElement("a");
                        pill.className = "subcard-pill-btn";
                        pill.style.cssText = "font-size:11px; padding:5px 10px; text-decoration:none; display:inline-flex; align-items:center; gap:6px; background:rgba(255,255,255,0.04);";
                        pill.href = `/storage/projects/${taskId}/work/${f.rel_path}`;
                        pill.setAttribute("download", f.name);
                        pill.download = f.name;
                        const icon = f.ext === ".mp4" ? "🎬" : f.ext === ".mp3" ? "🎙️" : f.ext === ".srt" ? "💬" : f.ext === ".png" ? "🖼️" : f.ext === ".jpg" ? "📷" : "📄";
                        pill.textContent = `${icon} ${f.name} (${f.size_kb} KB)`;
                        filesList.append(pill);
                    });
                }
            }).catch(() => {});
        }

        // Métricas de corte y tarjetas
        if ($("statCuts")) $("statCuts").textContent = result.silences_cut_count ?? 0;
        if ($("statBRolls")) $("statBRolls").textContent = result.brolls_count ?? 0;
        if ($("statCards")) $("statCards").textContent = result.cards_shown ?? 0;
        if ($("statTimeSaved")) $("statTimeSaved").textContent = `${Number(result.time_saved_sec || 0).toFixed(1)} s`;
        renderFacts(result.cards || []);

        // Scroll suave al apartado exclusivo de producción con retardo para permitir repintado completo
        results.hidden = false;
        setTimeout(() => {
            results.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 150);
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
            const curUrl = new URL(window.location.href);
            curUrl.searchParams.set("task", data.task_id);
            curUrl.searchParams.delete("project");
            window.history.replaceState({}, "", curUrl);
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

    if (projectFromUrl) {
        localStorage.removeItem("currentTaskId");
        openProject(projectFromUrl).catch(err => {
            console.error("Error abriendo proyecto de URL:", err);
            switchMode("streamer");
        });
    } else {
        const savedTaskId = localStorage.getItem("currentTaskId") || taskFromUrl;
        if (taskFromUrl) localStorage.setItem("currentTaskId", taskFromUrl);
        if (savedTaskId) {
            controls.disabled = true;
            startBtn.disabled = true;
            $("statusTitle").textContent = "Recuperando el estado de la edición";
            $("pipelineStatusText").textContent = "Reconectando con el servidor local…";
            listen(savedTaskId);
        } else {
            switchMode("streamer");
        }
    }


    function setPhaseLabels(labels) {
        const ids = ["phase-input", "phase-analyze", "phase-cut", "phase-enrich", "phase-render"];
        ids.forEach((id, idx) => {
            const el = $(id);
            if (el && labels[idx]) {
                const span = el.querySelector("span:not(.phase-dot)");
                if (span) {
                    span.textContent = labels[idx];
                } else {
                    el.textContent = `${idx + 1}. ${labels[idx]}`;
                }
            }
        });
    }

    function switchMode(mode) {
        activeMode = mode;
        const tabStreamer = $("tabModeStreamer");
        const tabCopilot = $("tabModeCopilot");
        const tabStudio = $("tabModeStudio");
        const tabProjects = $("tabModeProjects");
        const dockStreamer = $("dockStreamer");
        const dockCopilot = $("dockCopilot");
        const dockStudio = $("dockStudio");
        const dockProjects = $("dockProjects");
        const heroTitle = $("heroTitle");
        const heroSubtitle = $("heroSubtitle");
        const bentoTitle = $("bentoCardTitle");
        const bentoSub = $("bentoCardSub");
        const previewBox = $("previewContainer");
        const dropWrap = $("copilotDropWrap");
        const streamerForm = $("streamerForm");
        const uploadForm = $("uploadForm");
        const studioSec = $("studioSection");
        const projectsCard = $("savedProjectsCard");

        // Limpiar clases activas
        [tabStreamer, tabCopilot, tabStudio, tabProjects].forEach(t => t && t.classList.remove("active"));
        [dockStreamer, dockCopilot, dockStudio, dockProjects].forEach(d => d && d.classList.remove("active"));
        if (studioSec) studioSec.hidden = true;
        if (projectsCard) projectsCard.hidden = true;

        const bentoPane = $("streamerTabPane");
        const trendingRow = $("trendingChipsRow");

        if (mode === "streamer") {
            if (tabStreamer) tabStreamer.classList.add("active");
            if (dockStreamer) dockStreamer.classList.add("active");
            if (heroTitle) heroTitle.textContent = "Transmisión Autónoma";
            if (heroSubtitle) heroSubtitle.textContent = "KAI investiga la web, redacta el guión y produce el video broadcast en vivo";
            if (bentoTitle) bentoTitle.textContent = "Mesa de Transmisión KAI";
            if (bentoSub) bentoSub.textContent = "Configuración de emisión y vista previa en tiempo real";
            if (trendingRow) trendingRow.hidden = false;
            if (bentoPane) bentoPane.hidden = false;
            if (previewBox) {
                previewBox.hidden = false;
                previewBox.style.display = "block";
            }
            if (dropWrap) {
                dropWrap.hidden = true;
                dropWrap.style.display = "none";
            }
            if (streamerForm) streamerForm.hidden = false;
            if (uploadForm) uploadForm.hidden = true;
            setPhaseLabels(["Investigar", "Guión IA", "Voz Neural", "B-Roll & Bento", "Broadcast"]);
        } else if (mode === "copilot") {
            if (tabCopilot) tabCopilot.classList.add("active");
            if (dockCopilot) dockCopilot.classList.add("active");
            if (heroTitle) heroTitle.textContent = "Editor de Video Co-Piloto";
            if (heroSubtitle) heroSubtitle.textContent = "Sube tu video y KAI cortará pausas, buscará B-Rolls y creará tarjetas Bento";
            if (bentoTitle) bentoTitle.textContent = "Edición de Video Inteligente";
            if (bentoSub) bentoSub.textContent = "Arrastra tu video para análisis neuronal y corte automático";
            if (trendingRow) trendingRow.hidden = true;
            if (bentoPane) bentoPane.hidden = false;
            const preview = $("projectPreview");
            const hasVideo = preview && preview.src && preview.src !== window.location.href && !preview.src.endsWith("#");
            if (hasVideo) {
                if (previewBox) { previewBox.hidden = false; previewBox.style.display = "block"; }
                if (dropWrap) { dropWrap.hidden = true; dropWrap.style.display = "none"; }
            } else {
                if (previewBox) { previewBox.hidden = true; previewBox.style.display = "none"; }
                if (dropWrap) { dropWrap.hidden = false; dropWrap.style.display = "block"; }
            }
            if (streamerForm) streamerForm.hidden = true;
            if (uploadForm) uploadForm.hidden = false;
            setPhaseLabels(["Preparar", "Analizar", "Detectar pausas", "Buscar recursos", "Renderizar"]);
        } else if (mode === "studio") {
            if (tabStudio) tabStudio.classList.add("active");
            if (dockStudio) dockStudio.classList.add("active");
            if (heroTitle) heroTitle.textContent = "Mesa de Edición & Timeline";
            if (heroSubtitle) heroSubtitle.textContent = "Ajusta la duración, tarjetas interactivas, B-rolls y exporta el corte final";
            if (trendingRow) trendingRow.hidden = true;
            if (bentoPane) bentoPane.hidden = true;
            if (studioSec) studioSec.hidden = false;
            renderStudio(editorState, $("projectPreview")?.src);
        } else if (mode === "projects") {
            if (tabProjects) tabProjects.classList.add("active");
            if (dockProjects) dockProjects.classList.add("active");
            if (heroTitle) heroTitle.textContent = "Biblioteca de Proyectos";
            if (heroSubtitle) heroSubtitle.textContent = "Historial completo de producciones transmitidas y videos editados";
            if (trendingRow) trendingRow.hidden = true;
            if (bentoPane) bentoPane.hidden = true;
            if (projectsCard) projectsCard.hidden = false;
            loadSavedProjects();
        }
    }

    // Navegación por tabs y por dock flotante
    $("tabModeStreamer")?.addEventListener("click", () => switchMode("streamer"));
    $("tabModeCopilot")?.addEventListener("click", () => switchMode("copilot"));
    $("tabModeStudio")?.addEventListener("click", () => switchMode("studio"));
    $("tabModeProjects")?.addEventListener("click", () => switchMode("projects"));

    $("dockStreamer")?.addEventListener("click", () => switchMode("streamer"));
    $("dockCopilot")?.addEventListener("click", () => switchMode("copilot"));
    $("dockStudio")?.addEventListener("click", () => switchMode("studio"));
    $("dockProjects")?.addEventListener("click", () => switchMode("projects"));

    // Pills de formato 16:9 vs 9:16
    document.querySelectorAll("#formatPillsWrap .subcard-pill-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("#formatPillsWrap .subcard-pill-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const fmt = btn.dataset.fmt;
            if ($("streamerFormat")) $("streamerFormat").value = fmt;
            if ($("readoutFormat")) $("readoutFormat").textContent = fmt === "9:16" ? "9:16 Short" : "16:9 FHD";
            if ($("heroResolutionVal")) $("heroResolutionVal").innerHTML = fmt === "9:16" ? "9:16<sup>Vertical</sup>" : "1080p<sup>FHD</sup>";
        });
    });

    // Pills de duración (1m, 3m, 5m, 10m)
    document.querySelectorAll("#durationPillsWrap .subcard-pill-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("#durationPillsWrap .subcard-pill-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const sec = btn.dataset.sec;
            if ($("streamerDuration")) $("streamerDuration").value = sec;
            const min = Math.round(parseInt(sec, 10) / 60);
            if ($("readoutDuration")) $("readoutDuration").textContent = `${min} min`;
            if ($("heroDurationVal")) $("heroDurationVal").innerHTML = `${min}<sup>min</sup>`;
        });
    });

    // Chips dinámicos de tendencias web reales
    async function loadTrendingTopics() {
        const row = $("trendingChipsRow");
        if (!row) return;
        try {
            const resp = await fetch("/api/trending-topics");
            if (!resp.ok) return;
            const data = await resp.json();
            const topics = data.topics || [];
            if (!topics.length) return;

            // Conservar etiqueta inicial y botón de refresh
            row.innerHTML = `<span style="font-size:11px; font-weight:700; color:var(--text-muted); display:inline-flex; align-items:center; gap:4px; margin-right:4px;">🔥 Tendencias Web:</span>`;
            
            const emojis = ["⚛️", "🚀", "🧠", "⚡", "🔭", "🔋", "🧬", "🌐"];
            topics.slice(0, 6).forEach((top, i) => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "filter-chip chip-trend-btn";
                btn.dataset.topic = top;
                const emoji = emojis[i % emojis.length];
                // Título abreviado para el chip
                const shortLabel = top.length > 25 ? (top.slice(0, 23) + "…") : top;
                btn.textContent = `${emoji} ${shortLabel}`;
                btn.title = top;
                btn.addEventListener("click", () => {
                    document.querySelectorAll("#trendingChipsRow .filter-chip").forEach(c => c.classList.remove("active"));
                    btn.classList.add("active");
                    const input = $("streamerTopic");
                    if (input) {
                        input.value = top;
                        input.focus();
                        if ($("readoutTopicShort")) $("readoutTopicShort").textContent = top.slice(0, 18) + "…";
                    }
                });
                row.appendChild(btn);
            });

            // Botón de recargar tendencias
            const refreshBtn = document.createElement("button");
            refreshBtn.type = "button";
            refreshBtn.className = "filter-chip filter-chip-add";
            refreshBtn.title = "Actualizar tendencias web";
            refreshBtn.textContent = "↻";
            refreshBtn.addEventListener("click", (e) => {
                e.preventDefault();
                loadTrendingTopics();
            });
            row.appendChild(refreshBtn);
        } catch (err) {
            console.log("[Trending] Error cargando tendencias:", err);
        }
    }

    // Inicializar tendencias al arrancar
    loadTrendingTopics();

    // Sincronizar topic input con readout en vivo
    $("streamerTopic")?.addEventListener("input", (e) => {
        const val = e.target.value.trim();
        if ($("readoutTopicShort")) {
            $("readoutTopicShort").textContent = val ? (val.slice(0, 16) + "…") : "Tema Libre";
        }
    });

    // Configuración interactiva de RTMP en Vivo (YouTube Live, Twitch, Kick, Personalizado)
    const livePlatform = $("streamerLivePlatform");
    const streamKey = $("streamerStreamKey");
    const customRtmp = $("streamerCustomRtmp");
    if (livePlatform && streamKey && customRtmp) {
        livePlatform.addEventListener("change", () => {
            const val = livePlatform.value;
            if (val === "none") {
                streamKey.style.display = "none";
                customRtmp.style.display = "none";
            } else if (val === "custom") {
                streamKey.style.display = "none";
                customRtmp.style.display = "block";
            } else {
                streamKey.style.display = "block";
                customRtmp.style.display = "none";
                if (val === "youtube") {
                    streamKey.placeholder = "Clave de emisión de YouTube Live (xxxx-xxxx-xxxx-xxxx)";
                } else if (val === "twitch") {
                    streamKey.placeholder = "Clave de emisión de Twitch (live_...)";
                } else if (val === "kick") {
                    streamKey.placeholder = "Clave de emisión de Kick (sk_...)";
                }
            }
        });
    }

    // Toggle para cajón de opciones avanzadas (organizado y expandible según solicitud)
    const toggleDrawerBtn = $("toggleAdvancedDrawer");
    const drawer = $("advancedDrawer");
    if (toggleDrawerBtn && drawer) {
        toggleDrawerBtn.addEventListener("click", () => {
            drawer.hidden = !drawer.hidden;
            toggleDrawerBtn.classList.toggle("expanded", !drawer.hidden);
        });
    }

    // Botón para pantalla completa en la esquina inferior derecha
    $("fullscreenExpandBtn")?.addEventListener("click", () => {
        const masterPlayer = $("masterVideoPlayer");
        const preview = $("projectPreview");
        const targetVideo = (masterPlayer && !$("resultsSection").hidden && masterPlayer.src) 
            ? masterPlayer 
            : (preview && preview.src ? preview : ($("mainStudioWindow") || document.documentElement));
            
        if (!document.fullscreenElement) {
            targetVideo.requestFullscreen?.().catch(() => {
                document.documentElement.requestFullscreen?.().catch(() => {});
            });
        } else {
            document.exitFullscreen?.().catch(() => {});
        }
    });

    // Envío del formulario de KAI Streamer
    const streamerForm = $("streamerForm");
    const startStreamerBtn = $("startStreamerBtn");
    const startStreamerBtnText = $("startStreamerBtnText");

    if (streamerForm) {
        streamerForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const topic = ($("streamerTopic")?.value || "").trim();
            if (!topic) {
                alert("Por favor escribe o selecciona un tema para la transmisión de KAI.");
                $("streamerTopic")?.focus();
                return;
            }

            startStreamerBtn.disabled = true;
            startStreamerBtnText.textContent = "Iniciando transmisión…";
            if (results) results.hidden = true;
            didShowResults = false;
            renderedEvents = "";
            if (feed && emptyFeed) {
                feed.replaceChildren(emptyFeed);
                emptyFeed.hidden = false;
            }
            if ($("totalElapsed")) $("totalElapsed").textContent = "00:00";
            if ($("stageElapsed")) $("stageElapsed").textContent = "00:00";
            if ($("signalAge")) $("signalAge").textContent = "—";
            if ($("waitNote")) $("waitNote").hidden = true;
            setConnection("active", "Iniciando KAI Streamer");
            if ($("statusTitle")) $("statusTitle").textContent = `Investigando «${topic}»`;
            if ($("pipelineStatusText")) $("pipelineStatusText").textContent = "KAI está buscando fuentes web reales para redactar el guión.";
            if ($("jobFileName")) $("jobFileName").textContent = `KAI Live: ${topic.slice(0, 35)}`;
            if ($("progressPctText")) $("progressPctText").textContent = "10%";
            if ($("progressBarFill")) $("progressBarFill").style.width = "10%";
            if ($("donutPctText")) $("donutPctText").textContent = "10%";
            if ($("donutProgressArc")) $("donutProgressArc").style.strokeDashoffset = 90;
            if ($("donutLabelText")) $("donutLabelText").textContent = "Investigando";

            // Obtener RTMP si está configurado para transmisión directa
            const platform = $("streamerLivePlatform")?.value || "none";
            let rtmpUrl = null;
            if (platform === "youtube") {
                const key = $("streamerStreamKey")?.value?.trim();
                if (key) rtmpUrl = `rtmp://a.rtmp.youtube.com/live2/${key}`;
            } else if (platform === "twitch") {
                const key = $("streamerStreamKey")?.value?.trim();
                if (key) rtmpUrl = `rtmp://live.twitch.tv/app/${key}`;
            } else if (platform === "kick") {
                const key = $("streamerStreamKey")?.value?.trim();
                if (key) rtmpUrl = `rtmps://fa723fc1b171.global-contribute.live-video.net:443/app/${key}`;
            } else if (platform === "custom") {
                const custom = $("streamerCustomRtmp")?.value?.trim();
                if (custom) rtmpUrl = custom;
            }

            const payload = {
                topic: topic,
                style: $("streamerStyle")?.value || "divulgacion",
                duration_sec: parseInt($("streamerDuration")?.value || "300", 10),
                aspect_ratio: $("streamerFormat")?.value || "16:9",
                card_theme: $("streamerCardTheme")?.value || "dark",
                voice: $("streamerVoice")?.value || "es-MX-JorgeNeural",
                rtmp_url: rtmpUrl,
            };

            try {
                const response = await fetch("/api/streamer/create", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || "No se pudo iniciar la transmisión.");
                observedTaskId = data.task_id;
                localStorage.setItem("currentTaskId", data.task_id);
                const curUrl = new URL(window.location.href);
                curUrl.searchParams.set("task", data.task_id);
                curUrl.searchParams.delete("project");
                window.history.replaceState({}, "", curUrl);
                listen(data.task_id);
            } catch (error) {
                console.error("Error al iniciar streamer:", error);
                startStreamerBtn.disabled = false;
                startStreamerBtnText.textContent = "🚀 Iniciar Transmisión de KAI";
                setConnection("error", "Error al iniciar");
                if ($("statusTitle")) $("statusTitle").textContent = "No se pudo iniciar la transmisión";
                if ($("pipelineStatusText")) $("pipelineStatusText").textContent = error.message;
            }
        });
    }


    // =========================================================================
    // CUSTOM STUDIO HUD VIDEO PLAYER CONTROLLER (UI/UX PROMAX)
    // =========================================================================
    function setupHudPlayer(videoEl, options) {
        if (!videoEl) return;
        const playBtn = $(options.playBtn);
        const muteBtn = $(options.muteBtn);
        const timecode = $(options.timecode);
        const scrubberWrap = $(options.scrubberWrap);
        const scrubberBar = $(options.scrubberBar);
        const speedBtn = $(options.speedBtn);
        const fullscreenBtn = $(options.fullscreenBtn);
        const downloadBtn = $(options.downloadBtn);
        const container = videoEl.closest(".stage-preview-box");

        function updatePlayState() {
            if (playBtn) playBtn.textContent = videoEl.paused ? "▶" : "⏸";
            if (container) {
                container.classList.toggle("is-paused", videoEl.paused);
            }
        }

        if (playBtn) {
            playBtn.addEventListener("click", () => {
                if (videoEl.paused) videoEl.play().catch(() => {});
                else videoEl.pause();
                updatePlayState();
            });
        }

        videoEl.addEventListener("play", updatePlayState);
        videoEl.addEventListener("pause", updatePlayState);
        videoEl.addEventListener("ended", updatePlayState);

        if (muteBtn) {
            muteBtn.addEventListener("click", () => {
                videoEl.muted = !videoEl.muted;
                muteBtn.textContent = videoEl.muted ? "🔇" : "🔊";
            });
        }

        // Actualizar timecode y barra scrubber
        function updateTimeline() {
            const cur = videoEl.currentTime || 0;
            const dur = videoEl.duration || 0;
            if (timecode) {
                timecode.textContent = `${fmtDuration(cur)} / ${fmtDuration(dur)}`;
            }
            if (scrubberBar && dur > 0) {
                const pct = (cur / dur) * 100;
                scrubberBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
            }
        }

        videoEl.addEventListener("timeupdate", updateTimeline);
        videoEl.addEventListener("loadedmetadata", updateTimeline);
        videoEl.addEventListener("durationchange", updateTimeline);

        // Control scrubber: clic directo y arrastre suave
        if (scrubberWrap) {
            let isScrubbing = false;

            function scrub(e) {
                const rect = scrubberWrap.getBoundingClientRect();
                if (rect.width <= 0) return;
                const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                if (videoEl.duration) {
                    videoEl.currentTime = pos * videoEl.duration;
                }
                if (scrubberBar) {
                    scrubberBar.style.width = `${pos * 100}%`;
                }
            }

            scrubberWrap.addEventListener("mousedown", (e) => {
                isScrubbing = true;
                scrub(e);
            });

            window.addEventListener("mousemove", (e) => {
                if (isScrubbing) scrub(e);
            });

            window.addEventListener("mouseup", () => {
                isScrubbing = false;
            });

            // Soporte táctil en pantalla móvil / tablet
            scrubberWrap.addEventListener("touchstart", (e) => {
                isScrubbing = true;
                if (e.touches[0]) scrub(e.touches[0]);
            }, { passive: true });

            window.addEventListener("touchmove", (e) => {
                if (isScrubbing && e.touches[0]) scrub(e.touches[0]);
            }, { passive: true });

            window.addEventListener("touchend", () => {
                isScrubbing = false;
            });
        }

        const speeds = [1, 1.25, 1.5, 2];
        let speedIdx = 0;
        if (speedBtn) {
            speedBtn.addEventListener("click", () => {
                speedIdx = (speedIdx + 1) % speeds.length;
                const spd = speeds[speedIdx];
                videoEl.playbackRate = spd;
                speedBtn.textContent = `${spd}x`;
            });
        }

        if (fullscreenBtn) {
            fullscreenBtn.addEventListener("click", () => {
                if (container?.requestFullscreen) {
                    if (document.fullscreenElement) document.exitFullscreen();
                    else container.requestFullscreen();
                } else if (videoEl.requestFullscreen) {
                    if (document.fullscreenElement) document.exitFullscreen();
                    else videoEl.requestFullscreen();
                }
            });
        }

        if (downloadBtn) {
            downloadBtn.addEventListener("click", (e) => {
                e.preventDefault();
                const taskId = observedTaskId || "";
                const titleSource = $("resVideoTitle")?.textContent || $("bentoCardTitle")?.textContent || "KAI_Broadcast";
                const cleanTitle = titleSource.replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "_") || "KAI_Broadcast";
                const mp4Filename = `${cleanTitle}.mp4`;
                const endpoint = taskId ? `/api/projects/${taskId}/download` : (videoEl.src || "#");

                if (taskId) {
                    fetch(`/api/projects/${taskId}/save-to-downloads`, { method: "POST" })
                        .then(r => r.json())
                        .then(d => {
                            if (d.status === "ok") {
                                console.log("Video guardado en Descargas de Windows:", d.path);
                            }
                        })
                        .catch(() => {});
                }

                const a = document.createElement("a");
                a.href = endpoint;
                a.setAttribute("download", mp4Filename);
                document.body.appendChild(a);
                a.click();
                setTimeout(() => a.remove(), 1000);
            });
        }
    }

    // Inicializar HUDs
    setupHudPlayer($("projectPreview"), {
        playBtn: "hudPlayBtn",
        muteBtn: "hudMuteBtn",
        timecode: "hudTimecode",
        scrubberWrap: "hudScrubberWrap",
        scrubberBar: "hudScrubberBar",
        speedBtn: "hudSpeedBtn",
        fullscreenBtn: "hudFullscreenBtn",
        downloadBtn: "hudDownloadBtn"
    });

    setupHudPlayer($("masterVideoPlayer"), {
        playBtn: "masterPlayBtn",
        muteBtn: "masterMuteBtn",
        timecode: "masterTimecode",
        scrubberWrap: "masterScrubberWrap",
        scrubberBar: "masterScrubberBar",
        speedBtn: "masterSpeedBtn",
        fullscreenBtn: "masterFullscreenBtn",
        downloadBtn: "masterDownloadHudBtn"
    });

    // Framer Motion Micro-Animations
    if (window.Motion) {
        try {
            const { animate } = window.Motion;
            document.querySelectorAll(".dock-btn, .subcard-pill-btn, .cta-broadcast-btn, .hud-btn").forEach(el => {
                el.addEventListener("mouseenter", () => animate(el, { scale: 1.05 }, { duration: 0.18 }));
                el.addEventListener("mouseleave", () => animate(el, { scale: 1 }, { duration: 0.18 }));
                el.addEventListener("mousedown", () => animate(el, { scale: 0.95 }, { duration: 0.1 }));
                el.addEventListener("mouseup", () => animate(el, { scale: 1.05 }, { duration: 0.1 }));
            });
        } catch (e) {
            console.log("Motion init info:", e);
        }
    }

    loadSavedProjects();

    // Auto-abrir proyecto o tarea si está presente en la URL o en localStorage
    const initialUrl = new URL(window.location.href);
    const urlProjectId = initialUrl.searchParams.get("project");
    const urlTaskId = initialUrl.searchParams.get("task");
    const savedTaskId = localStorage.getItem("currentTaskId");

    if (urlProjectId) {
        openProject(urlProjectId).catch((e) => console.log("No se pudo cargar proyecto inicial:", e));
    } else if (urlTaskId) {
        listen(urlTaskId);
    } else if (savedTaskId) {
        listen(savedTaskId);
    }
});

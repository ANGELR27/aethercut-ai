document.addEventListener("DOMContentLoaded", () => {
    const $ = (id) => document.getElementById(id);

    const dropzone = $("dropzone");
    const videoFileInput = $("videoFileInput");
    const browseTrigger = $("browseTrigger");
    const selectedFileBadge = $("selectedFileBadge");
    const selectedFileName = $("selectedFileName");
    const removeFileBtn = $("removeFileBtn");
    const startBtn = $("startBtn");
    const uploadForm = $("uploadForm");
    const silenceThreshold = $("silenceThreshold");
    const silenceVal = $("silenceVal");
    const dispSilence = $("dispSilence");

    const chatFeed = $("chatFeed");
    const progWrap = $("assistantProgressWrap");
    const progressBarFill = $("progressBarFill");
    const progressPctText = $("progressPctText");
    const pipelineStatusText = $("pipelineStatusText");
    const resultsSection = $("resultsSection");

    const masterVideoPlayer = $("masterVideoPlayer");
    const shortVideoPlayer = $("shortVideoPlayer");
    const downloadMasterBtn = $("downloadMasterBtn");
    const downloadShortBtn = $("downloadShortBtn");
    const shortContainer = $("shortContainer");

    const statCuts = $("statCuts");
    const statBRolls = $("statBRolls");
    const statTimeSaved = $("statTimeSaved");
    const kpiBroll = $("kpiBroll");
    const kpiSaved = $("kpiSaved");

    const stages = {
        gemini: $("stepGemini"),
        broll: $("stepAssets"),
        cards: $("stepCards"),
        render: $("stepRender"),
        subs: $("stepSubs"),
    };
    const statCards = $("statCards");
    const factsWrap = $("factsWrap");
    const factsList = $("factsList");
    const factsSummary = $("factsSummary");

    let selectedFile = null;
    let lastLogged = "";

    /* ---------- Decorative charts (dot matrix, bars, holders) ---------- */
    const TOTAL_DOTS = 24 * 5;
    const dotMatrix = $("dotMatrix");
    for (let i = 0; i < TOTAL_DOTS; i++) dotMatrix.appendChild(document.createElement("i"));
    const dots = [...dotMatrix.children];

    function paintDots(pct) {
        const lit = Math.round((pct / 100) * TOTAL_DOTS);
        dots.forEach((d, i) => {
            d.className = "";
            if (i < lit) {
                const q = i / TOTAL_DOTS;
                d.classList.add(q < 0.25 ? "on-a" : q < 0.5 ? "on-b" : q < 0.75 ? "on-c" : "on-d");
            }
        });
    }
    paintDots(0);

    /* ---------- Chat & Terminal helpers ---------- */
    const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const clock = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

    function addMsg(kind, text) {
        const m = document.createElement("div");
        m.className = `msg ${kind}`;
        m.innerHTML = `<p>${esc(text)}</p><time>${clock()}</time>`;
        chatFeed.appendChild(m);
        chatFeed.scrollTop = chatFeed.scrollHeight;
    }

    const terminalLog = $("terminalLog");
    function logToTerminal(msg, type = "info") {
        if (!terminalLog) return;
        const d = document.createElement("div");
        d.innerHTML = `<span class="sys-time">[${clock()}]</span> <span class="log-${type}">${esc(msg)}</span>`;
        terminalLog.appendChild(d);
        terminalLog.scrollTop = terminalLog.scrollHeight;
        localStorage.setItem("terminalHistory", terminalLog.innerHTML);
    }

    // Restore state on load
    if (terminalLog) {
        const hist = localStorage.getItem("terminalHistory");
        if (hist) {
            terminalLog.innerHTML = hist;
            terminalLog.scrollTop = terminalLog.scrollHeight;
        }
    }
    const activeTask = localStorage.getItem("currentTaskId");
    if (activeTask) {
        progWrap.style.display = "block";
        listen(activeTask);
    }

    /* ---------- Stage status ---------- */
    function setStage(el, state, label) {
        el.classList.remove("active", "completed");
        if (state) el.classList.add(state);
        el.querySelector(".st").textContent = label;
    }

    function resetStages() {
        Object.values(stages).forEach((el) => setStage(el, null, "Idle"));
    }

    function highlightStep(step) {
        const order = ["gemini", "broll", "cards", "render", "subs"];
        const map = { gemini: "gemini", broll: "broll", cards: "cards", render: "render", subtitles: "subs", finalizing: "subs", done: "done" };
        const cur = map[step];
        if (!cur) return;
        if (cur === "done") {
            order.forEach((k) => setStage(stages[k], "completed", "Done"));
            return;
        }
        const idx = order.indexOf(cur);
        order.forEach((k, i) => {
            if (i < idx) setStage(stages[k], "completed", "Done");
            else if (i === idx) setStage(stages[k], "active", "Running");
            else setStage(stages[k], null, "Idle");
        });
    }

    /* ---------- Controls ---------- */
    silenceThreshold.addEventListener("input", (e) => {
        const v = `${parseFloat(e.target.value).toFixed(1)}s`;
        silenceVal.textContent = v;
        dispSilence.textContent = v;
    });

    dropzone.addEventListener("click", () => videoFileInput.click());
    browseTrigger.addEventListener("click", () => videoFileInput.click());
    dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("drag-active"); });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-active"));
    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("drag-active");
        if (e.dataTransfer.files && e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });
    videoFileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length) handleFile(e.target.files[0]);
    });

    function handleFile(file) {
        selectedFile = file;
        const mb = (file.size / (1024 * 1024)).toFixed(1);
        selectedFileName.textContent = `${file.name} (${mb} MB)`;
        selectedFileBadge.style.display = "inline-flex";
        startBtn.disabled = false;
        addMsg("ai", `Loaded ${file.name} (${mb} MB). Ready to process.`);
    }

    removeFileBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        selectedFile = null;
        videoFileInput.value = "";
        selectedFileBadge.style.display = "none";
        startBtn.disabled = true;
    });

    /* ---------- Submit / pipeline ---------- */
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!selectedFile) return;

        startBtn.disabled = true;
        progWrap.style.display = "block";
        resultsSection.style.display = "none";
        resetStages();
        paintDots(0);
        lastLogged = "";
        localStorage.removeItem("terminalHistory");
        if (terminalLog) terminalLog.innerHTML = '<div><span class="sys-time">[' + clock() + ']</span> <span class="log-info">System initialized. Uploading video...</span></div>';

        const opts = [
            $("enableBRoll").checked && "B-Roll",
            $("enableCards").checked && "tarjetas verificadas",
            $("enableCaptions").checked && "subtítulos",
            $("enableShorts").checked && "Short 9:16",
        ].filter(Boolean).join(", ");
        addMsg("me", `Smart cut ${silenceThreshold.value}s${opts ? " + " + opts : ""}.`);
        updateProgress(5, "Uploading file to server...");

        const fd = new FormData();
        fd.append("video", selectedFile);
        fd.append("silence_threshold", silenceThreshold.value);
        fd.append("enable_broll", $("enableBRoll").checked);
        fd.append("enable_captions", $("enableCaptions").checked);
        fd.append("enable_shorts", $("enableShorts").checked);
        fd.append("enable_cards", $("enableCards").checked);

        try {
            const resp = await fetch("/api/process-video", { method: "POST", body: fd });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || "Error al procesar el video");
            }
            const data = await resp.json();
            logToTerminal("Upload complete. Task ID: " + data.task_id, "success");
            localStorage.setItem("currentTaskId", data.task_id);
            listen(data.task_id);
        } catch (err) {
            addMsg("ai", `Error: ${err.message}`);
            logToTerminal("Error: " + err.message, "error");
            startBtn.disabled = false;
        }
    });

    function listen(taskId) {
        const es = new EventSource(`/api/stream-progress/${taskId}`);
        es.onmessage = (ev) => {
            const u = JSON.parse(ev.data);
            const { step, progress, message, completed, error, result } = u;

            if (error) {
                es.close();
                addMsg("ai", `Error: ${error}`);
                logToTerminal("Error: " + error, "error");
                startBtn.disabled = false;
                return;
            }

            updateProgress(progress, message);
            highlightStep(step);

            if (message && message !== lastLogged) {
                lastLogged = message;
                // Only chat important status updates, log EVERYTHING to terminal
                if (message.includes("Gemini:") || message.includes("Master") || message.includes("Renderizando") || message.includes("Short")) {
                    addMsg("ai", message);
                }
                logToTerminal(message, "info");
            }

            if (completed && result) {
                es.close();
                addMsg("ai", "Done. Master video and vertical Short are ready to download.");
                logToTerminal("Process completed successfully.", "success");
                showResults(result);
            }
        };
        es.onerror = () => {
            es.close();
            logToTerminal("Connection closed.", "warn");
        };
    }

    function updateProgress(pct, msg) {
        const p = Math.min(100, Math.max(0, pct || 0));
        progressBarFill.style.width = `${p}%`;
        progressPctText.textContent = `${Math.round(p)}%`;
        pipelineStatusText.textContent = msg || "";
        paintDots(p);
    }

    function showResults(r) {
        startBtn.disabled = false;
        resultsSection.style.display = "block";
        resultsSection.scrollIntoView({ behavior: "smooth", block: "nearest" });

        if (r.master_video_url) {
            masterVideoPlayer.src = r.master_video_url;
            downloadMasterBtn.href = r.master_video_url;
        }
        if (r.short_video_url) {
            shortContainer.style.display = "block";
            shortVideoPlayer.src = r.short_video_url;
            downloadShortBtn.href = r.short_video_url;
        } else {
            shortContainer.style.display = "none";
        }

        const saved = `+${Number(r.time_saved_sec || 0).toFixed(1)}s`;
        statCuts.textContent = r.silences_cut_count || 0;
        statBRolls.textContent = r.brolls_count || 0;
        statTimeSaved.textContent = saved;
        kpiBroll.textContent = r.brolls_count || 0;
        kpiSaved.textContent = saved;
        statCards.textContent = r.cards_shown || 0;
        renderFacts(r.cards || []);
    }

    const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
    const VERDICT = {
        supported: ["ok", "confirmado"],
        contradicted: ["bad", "falso · descartado"],
        insufficient: ["na", "sin evidencia"],
    };

    function renderFacts(cards) {
        factsList.innerHTML = "";
        factsWrap.style.display = cards.length ? "block" : "none";
        const ok = cards.filter((c) => c.verdict === "supported").length;
        factsSummary.textContent = `${ok}/${cards.length} confirmados`;

        cards.forEach((c) => {
            const [cls, label] = VERDICT[c.verdict] || VERDICT.insufficient;
            const li = document.createElement("li");
            li.className = "fact";
            const srcs = (c.sources || [])
                .map((s) => `<a href="${esc(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">${esc(s.domain || "fuente")}</a>`)
                .join("");
            const detail = c.verdict === "supported"
                ? esc(c.body)
                : `No se muestra en el video. ${esc(c.note || "")}`;
            li.innerHTML = `
                <div class="fact-top"><b>${esc(c.headline)}</b><span class="badge ${cls}">${label}${c.shown ? " · en video" : ""}</span></div>
                <p class="claim">Dijo (${esc(c.at_sec)}s): ${esc(c.claim)}</p>
                <p>${detail}</p>
                ${srcs ? `<div class="srcs">${srcs}</div>` : ""}`;
            factsList.appendChild(li);
        });
    }
});

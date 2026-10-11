/**
 * AetherCut - Radar de Viralidad
 * Ranking 24-72h de videos virales por región (score + movimiento cada 3h)
 * y temas urgentes sin cobertura. Réplica en español con mejoras en 1 clic.
 */
import { $, esc } from "./utils.js";

let pollTimer = null;
let countdownTimer = null;
let currentTab = "videos";
let data = null;

/* --------------------------------------------------------------- helpers */

function toast(message, level = "info") {
    const colors = { success: "#10b981", error: "#ef4444", warning: "#f59e0b", info: "#38bdf8" };
    const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
    const color = colors[level] || colors.info;
    const el = document.createElement("div");
    el.style.cssText = `position: fixed; bottom: 88px; right: 24px; z-index: 99999;
        background: #1e293b; border: 1px solid ${color}55; border-left: 3px solid ${color};
        color: #e2e8f0; padding: 12px 18px; border-radius: 10px; font-size: 13px; font-weight: 500;
        max-width: 360px; box-shadow: 0 8px 32px rgba(0,0,0,.45); display: flex; gap: 10px; align-items: center;
        pointer-events: none; transition: opacity .4s ease, transform .4s ease;`;
    el.innerHTML = `<span>${icons[level] || icons.info}</span><span>${esc(message)}</span>`;
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; el.style.transform = "translateX(20px)"; setTimeout(() => el.remove(), 450); }, 4200);
}

function fmtViews(n) {
    n = Number(n || 0);
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
    return String(n);
}

function timeAgo(iso) {
    if (!iso) return "";
    const mins = Math.max(1, Math.floor((Date.now() - new Date(iso).getTime()) / 60000));
    if (mins < 60) return `hace ${mins} min`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `hace ${hours} h`;
    return `hace ${Math.floor(hours / 24)} d`;
}

/* ------------------------------------------------------------- renderizado */

function renderUpdatedBadge() {
    const badge = $("radarUpdatedBadge");
    if (!badge) return;
    if (!data?.updated_at) { badge.textContent = "Cargando radar…"; return; }
    let base = `Actualizado ${timeAgo(data.updated_at)}`;
    if (data.refreshing) base += " · 🔄 barriendo ahora";
    else if (data.next_update_at) {
        const mins = Math.max(0, Math.round((new Date(data.next_update_at).getTime() - Date.now()) / 60000));
        if (mins < 90) base += ` · próxima revisión en ${Math.max(1, mins)} min`;
        else base += ` · próxima revisión en ${Math.floor(mins / 60)} h ${mins % 60} min`;
    }
    badge.textContent = base;
}

function renderVideos() {
    const list = $("radarVideosList");
    if (!list) return;
    list.replaceChildren();
    const videos = data?.videos || [];
    const regions = $("radarRegionsLabel");
    if (regions) regions.textContent = data?.regions?.length ? `Regiones: ${data.regions.join(" · ")}` : "";

    if (!videos.length) {
        const empty = document.createElement("div");
        empty.className = "radar-empty";
        empty.innerHTML = `<span style="font-size:28px;">📡</span><strong>Radar calibrando…</strong>
            <span>El primer barrido (charts de YouTube + análisis IA) está en marcha. Vuelve en un minuto.</span>`;
        list.append(empty);
        return;
    }

    videos.forEach(v => {
        const row = document.createElement("article");
        row.className = "radar-video-row";

        // Rango + movimiento
        const rankBox = document.createElement("div");
        rankBox.className = "radar-rank-box";
        rankBox.innerHTML = `<span class="radar-rank-num">#${v.rank}</span>`;
        const move = document.createElement("span");
        if (v.is_new) { move.className = "radar-move new"; move.textContent = "🆕"; move.title = "Nuevo en el ranking"; }
        else if (v.movement > 0) { move.className = "radar-move up"; move.textContent = `↑${v.movement}`; move.title = `Subió ${v.movement} puestos`; }
        else if (v.movement < 0) { move.className = "radar-move down"; move.textContent = `↓${Math.abs(v.movement)}`; move.title = `Bajó ${Math.abs(v.movement)} puestos`; }
        else { move.className = "radar-move steady"; move.textContent = "•"; move.title = "Sin cambios"; }
        rankBox.append(move);

        // Miniatura
        const thumbWrap = document.createElement("a");
        thumbWrap.className = "radar-thumb";
        thumbWrap.href = v.url;
        thumbWrap.target = "_blank";
        thumbWrap.rel = "noopener";
        thumbWrap.title = "Ver el video original en YouTube";
        thumbWrap.innerHTML = v.thumb
            ? `<img src="${esc(v.thumb)}" alt="" loading="lazy">`
            : `<span class="radar-thumb-ph">🎬</span>`;

        // Textos
        const body = document.createElement("div");
        body.className = "radar-video-body";
        const title = document.createElement("a");
        title.className = "radar-video-title";
        title.href = v.url;
        title.target = "_blank";
        title.rel = "noopener";
        title.textContent = v.title;
        const meta = document.createElement("div");
        meta.className = "radar-video-meta";
        const velocity = v.measured_velocity ?? v.views_per_hour;
        const durTxt = v.duration_sec ? `${Math.floor(v.duration_sec / 60)}:${String(v.duration_sec % 60).padStart(2, "0")}` : "—";
        meta.innerHTML =
            `<span>${v.region_flag} ${esc(v.region)}</span>` +
            `<span title="Categoría de YouTube">${v.category_emoji || "🔥"} ${esc(v.category || "viral")}</span>` +
            `<span title="Duración del original">⏱ ${durTxt}${v.is_short ? " (Short)" : ""}</span>` +
            `<span>👁 ${fmtViews(v.views)} vistas</span>` +
            `<span class="radar-hot" title="Velocidad: vistas por hora">⚡ ${fmtViews(velocity)}/h</span>` +
            `<span>❤️ ${(v.like_ratio * 100).toFixed(1)}%</span>`;
        body.append(title, meta);

        // Score
        const scoreBox = document.createElement("div");
        scoreBox.className = "radar-score-box";
        scoreBox.innerHTML =
            `<span class="radar-score-num ${v.score >= 70 ? "hot" : v.score >= 45 ? "warm" : ""}">${v.score}</span>` +
            `<span class="radar-score-label">SCORE</span>`;
        scoreBox.append(scoreBar(v.score));

        // Botón replicar: primero la IA analiza y propone enfoques
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "radar-replicate-btn";
        btn.title = "La IA analiza el original, propone enfoques y tú eliges qué producir";
        btn.innerHTML = `<span>⚡ Replicar 🇪🇸</span>`;
        btn.addEventListener("click", () => openStrategyModal(v));

        row.append(rankBox, thumbWrap, body, scoreBox, btn);
        list.append(row);
    });
}

function scoreBar(score) {
    const wrap = document.createElement("div");
    wrap.className = "radar-score-bar";
    const fill = document.createElement("div");
    fill.className = "radar-score-fill";
    fill.style.width = `${Math.max(4, Math.min(100, score))}%`;
    wrap.append(fill);
    return wrap;
}

function renderTopics() {
    const grid = $("radarTopicsGrid");
    if (!grid) return;
    grid.replaceChildren();
    const topics = data?.topics || [];

    if (!topics.length) {
        const empty = document.createElement("div");
        empty.className = "radar-empty";
        empty.style.gridColumn = "1 / -1";
        empty.innerHTML = `<span style="font-size:28px;">🚨</span><strong>Sin temas urgentes aún</strong>
            <span>El barrido de noticias + análisis IA todavía no devuelve candidatos.</span>`;
        grid.append(empty);
        return;
    }

    topics.forEach((t, idx) => {
        const card = document.createElement("article");
        card.className = "radar-topic-card";

        const head = document.createElement("div");
        head.className = "radar-topic-head";
        head.innerHTML =
            `<span class="radar-topic-score ${t.score >= 80 ? "hot" : t.score >= 60 ? "warm" : ""}" title="Fuerza de viralidad estimada por la IA">${t.score}</span>
             <div class="radar-topic-chips">
                 <span class="radar-chip cat">${esc(t.category)}</span>
                 <span class="radar-chip ${t.urgency >= 8 ? "urg-high" : t.urgency >= 5 ? "urg-mid" : "urg-low"}" title="Urgencia de publicación">⚡ ${t.urgency}/10</span>
                 ${idx === 0 ? `<span class="radar-chip top1">#1 OPORTUNIDAD</span>` : ""}
             </div>`;
        head.append(scoreBar(t.score));

        const title = document.createElement("h4");
        title.className = "radar-topic-title";
        title.textContent = t.title;

        const why = document.createElement("p");
        why.className = "radar-topic-why";
        why.innerHTML = `<strong>Por qué explota:</strong> ${esc(t.why)}`;

        const angle = document.createElement("p");
        angle.className = "radar-topic-angle";
        angle.innerHTML = `<strong>Ángulo para KAI:</strong> ${esc(t.angle)}`;

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "radar-replicate-btn wide";
        btn.innerHTML = `<span>🎬 Producir con KAI ahora</span>`;
        btn.addEventListener("click", () => replicate(btn, "topic", t));

        card.append(head, title, why, angle, btn);
        grid.append(card);
    });
}

/* ------------------------------------------------------------- réplica KAI */

let strategyCtx = null; // { item, choice } del modal de estrategia

async function openStrategyModal(video) {
    const modal = $("radarStrategyModal");
    if (!modal) { replicate(null, "video", video); return; }
    strategyCtx = { item: video, choice: null, auto: null };
    modal.hidden = false;
    if ($("radarStrategyTitle")) $("radarStrategyTitle").textContent = video.title || "Video viral";
    if ($("radarStrategySub")) $("radarStrategySub").textContent = `${video.region_flag || ""} ${video.channel || ""} · ${video.category_emoji || ""} ${video.category || ""} · ${fmtViews(video.views)} vistas`;
    if ($("radarStrategyLoading")) $("radarStrategyLoading").hidden = false;
    if ($("radarStrategyAnalysis")) $("radarStrategyAnalysis").hidden = true;
    if ($("radarStrategyCustom")) $("radarStrategyCustom").hidden = true;
    if ($("radarStrategyInstructions")) $("radarStrategyInstructions").value = "";
    if ($("radarStrategyOptions")) $("radarStrategyOptions").replaceChildren();
    const produceBtn = $("radarStrategyProduceBtn");
    if (produceBtn) { produceBtn.disabled = true; produceBtn.innerHTML = `<span>🧠 Esperando análisis…</span>`; }

    try {
        const res = await fetch("/api/trend-radar/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ kind: "video", item: video }),
        });
        const analysis = await res.json();
        if (!res.ok) throw new Error(analysis.detail || "El análisis falló.");
        renderStrategy(analysis);
    } catch (err) {
        closeStrategyModal();
        toast(`Estrategia: ${err.message}`, "error");
    }
}

function renderStrategy(analysis) {
    if ($("radarStrategyLoading")) $("radarStrategyLoading").hidden = true;
    const why = $("radarStrategyWhy");
    const aud = $("radarStrategyAudience");
    if (why) why.innerHTML = `<strong style="color:#e2e8f0;">📊 Por qué funciona el original:</strong> ${esc(analysis.why_works || "")}`;
    if (aud) aud.innerHTML = `🎯 ${esc(analysis.audience || "")}`;
    if ($("radarStrategyAnalysis")) $("radarStrategyAnalysis").hidden = false;

    const wrap = $("radarStrategyOptions");
    if (!wrap) return;
    wrap.replaceChildren();

    const select = (card, choice) => {
        wrap.querySelectorAll(".radar-option-card").forEach(c => c.classList.remove("selected"));
        card.classList.add("selected");
        strategyCtx.choice = choice;
    };

    // Opción "la IA decide": usa el enfoque de mayor puntaje de viralidad.
    const autoCard = document.createElement("button");
    autoCard.type = "button";
    autoCard.className = "radar-option-card selected";
    const recommended = (analysis.options || []).find(o => o.recommended)
        || (analysis.options || []).slice().sort((a, b) => (b.viral_estimate || 0) - (a.viral_estimate || 0))[0];
    if (recommended) strategyCtx.auto = recommended;
    autoCard.innerHTML = `
        <div class="radar-option-head">
            <span class="radar-chip cat" style="background:rgba(168,85,247,.2); color:#c084fc;">✨ IA DECIDE (MAYOR PUNTAJE)</span>
            ${recommended ? `<span class="radar-chip urg-high">⭐ ${esc(recommended.format || "recomendado")} · ${recommended.viral_estimate}</span>` : ""}
        </div>
        <strong class="radar-option-title">Que la IA produzca el enfoque de mayor viralidad</strong>
        <span class="radar-option-pitch">${recommended ? `Irá con: «${esc(recommended.title)}» · ${recommended.duration_sec}s` : "Estrategia óptima calculada por el análisis"}</span>`;
    autoCard.addEventListener("click", () => select(autoCard, null));
    wrap.append(autoCard);

    (analysis.options || []).forEach(opt => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "radar-option-card";
        card.innerHTML = `
            <div class="radar-option-head">
                <span class="radar-chip cat">${esc(opt.format || "enfoque")}</span>
                <span class="radar-chip ${opt.viral_estimate >= 80 ? "urg-high" : opt.viral_estimate >= 60 ? "urg-mid" : "urg-low"}">🔥 ${opt.viral_estimate}</span>
                <span class="radar-chip top1" style="margin-left:auto;">⏱ ${opt.duration_sec}s</span>
            </div>
            <strong class="radar-option-title">${esc(opt.title)}</strong>
            <span class="radar-option-pitch">${esc(opt.pitch)}</span>
            <div class="radar-score-bar"><div class="radar-score-fill" style="width:${Math.max(6, Math.min(100, opt.viral_estimate))}%;"></div></div>`;
        card.addEventListener("click", () => select(card, opt));
        wrap.append(card);
    });

    if ($("radarStrategyCustom")) $("radarStrategyCustom").hidden = false;
    const produceBtn = $("radarStrategyProduceBtn");
    if (produceBtn) { produceBtn.disabled = false; produceBtn.innerHTML = `<span>🎬 Producir con KAI</span>`; }
}

function closeStrategyModal() {
    const modal = $("radarStrategyModal");
    if (modal) modal.hidden = true;
}

async function produceFromStrategy(btn) {
    if (!strategyCtx) return;
    const instructions = $("radarStrategyInstructions")?.value?.trim() || "";
    // "IA decide" (choice null) usa el enfoque de mayor puntaje detectado.
    const choice = strategyCtx.choice || strategyCtx.auto;
    closeStrategyModal();
    await replicate(btn, "video", strategyCtx.item, { choice, instructions });
}

async function replicate(btn, kind, item, extra = {}) {
    if (btn?.dataset?.busy) return;
    if (btn) { btn.dataset.busy = "1"; btn.style.opacity = ".55"; }
    const original = btn?.innerHTML;
    if (btn) btn.innerHTML = `<span>🧠 Diseñando réplica…</span>`;
    try {
        const res = await fetch("/api/trend-radar/replicate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ kind, item, ...extra }), // la IA elige formato y duración
        });
        const out = await res.json();
        if (!res.ok) throw new Error(out.detail || "No se pudo preparar la réplica.");
        toast(`🚀 KAI está produciendo: «${out.topic}»`, "success");
        if (typeof window.__startRadarTask === "function") {
            window.__startRadarTask(out.task_id, out.topic);
        }
        load(); // refrescar temas (el producido se descuenta)
    } catch (err) {
        toast(`Error al replicar: ${err.message}`, "error");
        if (btn) btn.innerHTML = original;
    } finally {
        if (btn) { btn.style.opacity = "1"; delete btn.dataset.busy; }
    }
}

/* --------------------------------------------------------------- datos/poll */

function renderUnavailable(message) {
    const list = $("radarVideosList");
    const grid = $("radarTopicsGrid");
    const badge = $("radarUpdatedBadge");
    const box = document.createElement("div");
    box.className = "radar-empty";
    box.innerHTML = `<span style="font-size:30px;">📡</span>
        <strong>Radar no disponible ahora</strong>
        <span>${esc(message)}</span>`;
    if (list) { list.replaceChildren(box.cloneNode(true)); }
    if (grid) { grid.replaceChildren(box.cloneNode(true)); }
    if (badge) badge.textContent = "Sin conexión con el radar";
}

async function load({ silent = true } = {}) {
    try {
        const res = await fetch("/api/trend-radar");
        if (!res.ok) {
            throw new Error(res.status === 404
                ? "El servidor está corriendo código anterior. Detén uvicorn (Ctrl+C), vuelve a arrancarlo con «uvicorn server:app --port 8000» y recarga esta página (Ctrl+F5)."
                : `El radar respondió HTTP ${res.status}. Revisa la consola del servidor.`);
        }
        data = await res.json();
        renderVideos();
        renderTopics();
        renderUpdatedBadge();
    } catch (err) {
        if (!silent) toast(`Radar: ${err.message}`, "error");
        renderUnavailable(err.message || "Error de conexión con el servidor.");
    }
}

export function initTrendRadar() {
    document.querySelectorAll("[data-radar-tab]").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("[data-radar-tab]").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentTab = btn.dataset.radarTab;
            const videos = $("radarVideosPane");
            const topics = $("radarTopicsPane");
            if (videos) videos.hidden = currentTab !== "videos";
            if (topics) topics.hidden = currentTab !== "topics";
        });
    });

    $("radarRefreshBtn")?.addEventListener("click", async () => {
        try {
            await fetch("/api/trend-radar/refresh", { method: "POST" });
            toast("📡 Barriendo charts y noticias… listo en ~1 min.", "info");
            if ($("radarUpdatedBadge")) $("radarUpdatedBadge").textContent = "🔄 Barriendo charts + IA ahora…";
        } catch {
            toast("No se pudo iniciar el refresco.", "error");
        }
    });

    // Revisión silenciosa cada 5 min mientras la pestaña exista.
    pollTimer = setInterval(() => {
        const section = $("trendRadarSection");
        if (section && !section.hidden) load();
    }, 5 * 60 * 1000);

    // Modal de estrategia: cerrar y producir
    $("radarStrategyCloseBtn")?.addEventListener("click", closeStrategyModal);
    $("radarStrategyModal")?.addEventListener("click", (e) => {
        if (e.target.id === "radarStrategyModal") closeStrategyModal();
    });
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !$("radarStrategyModal")?.hidden) closeStrategyModal();
    });
    $("radarStrategyProduceBtn")?.addEventListener("click", (e) => produceFromStrategy(e.currentTarget));

    // Countdown del badge cada 30 s.
    countdownTimer = setInterval(renderUpdatedBadge, 30_000);

    load();

    return { load };
}

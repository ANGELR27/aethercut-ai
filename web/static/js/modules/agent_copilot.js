/**
 * Módulo Agente Copilot Multi-Modelo (Clon ChatGPT con Control Total de la App)
 * Conecta los modelos GLM-5.3, GLM-5.3 Flash, Kimi-k3 y Gemini con las acciones en tiempo real de AetherCut.
 */

export class AgentCopilot {
    constructor() {
        this.activeModel = "gemini";
        this.isOpen = false;
        this.isExpanded = false;
        this.history = [];          // Historial multi-turn de conversación
        this.isThinking = false;
        this.currentAbortController = null;
        this.currentTypewriterInterval = null;
        this.currentThinkingId = null;

        // Estado del MODO REN (Modificador de la Plataforma)
        this.isRenMode = false;
        this.selectedElementSelector = null;
        this.isInspectorActive = false;
        this.renStylesMap = {};

        this.modelsMeta = {
            "gemini":      { name: "Gemini 2.5 Flash",  color: "#f59e0b", badge: "⚡ Recomendado" },
            "glm-5.3":     { name: "GLM-5.3 Senior",    color: "#38bdf8", badge: "Arquitecto" },
            "glm-5.3-flash": { name: "GLM-5.3 Flash",  color: "#a855f7", badge: "Ultra Rápido" },
            "kimi-k3":     { name: "Kimi-k3",           color: "#10b981", badge: "Auditor" },
        };

        this.initElements();
        this.attachEvents();
        this.loadPersistedRenStyles();
    }

    initElements() {
        this.deck = document.getElementById("agentChatDeck");
        this.launcher = document.getElementById("agentFabLauncher");
        this.dockBtn = document.getElementById("dockAgentLauncher");
        this.btnClose = document.getElementById("agentBtnClose");
        this.btnMin = document.getElementById("agentBtnMinimize");
        this.btnExpand = document.getElementById("agentBtnExpand");
        this.btnNewChat = document.getElementById("agentBtnNewChat");
        this.modelCards = document.querySelectorAll(".agent-model-card");
        this.headerPillName = document.getElementById("agentHeaderModelName");
        this.headerDot = document.getElementById("agentHeaderDot");
        this.inputModelTag = document.getElementById("agentInputModelTag");
        this.fabModelPill = document.getElementById("agentFabModelPill");
        this.messagesContainer = document.getElementById("agentMessagesContainer");
        this.promptForm = document.getElementById("agentPromptForm");
        this.promptInput = document.getElementById("agentPromptInput");
        this.btnSend = document.getElementById("agentBtnSend");
        this.quickBtns = document.querySelectorAll(".agent-quick-btn");
        this.suggChips = document.querySelectorAll(".agent-sugg-chip");

        // Elementos del MODO REN
        this.btnToggleRen = document.getElementById("agentBtnToggleRen");
        this.renToolbar = document.getElementById("agentRenToolbar");
        this.renToggleDot = document.getElementById("agentRenToggleDot");
        this.btnPickElement = document.getElementById("agentBtnPickElement");
        this.renTargetPill = document.getElementById("agentRenTargetPill");
        this.renTargetSelText = document.getElementById("agentRenTargetSelText");
        this.btnClearTarget = document.getElementById("agentBtnClearTarget");
        this.btnResetRen = document.getElementById("agentBtnResetRen");
        this.renChips = document.querySelectorAll(".agent-ren-chip");
        this.inspectorOverlay = document.getElementById("agentRenInspectorOverlay");
        this.inspectorBadge = document.getElementById("agentRenInspectorBadge");
        this.inspectorTag = document.getElementById("agentRenHoverTag");
        this.inspectorSel = document.getElementById("agentRenHoverSel");
    }

    attachEvents() {
        // Toggle abrir / cerrar
        if (this.launcher) {
            this.launcher.addEventListener("click", () => this.toggle());
        }
        if (this.dockBtn) {
            this.dockBtn.addEventListener("click", () => this.open());
        }
        if (this.btnClose) {
            this.btnClose.addEventListener("click", () => this.close());
        }
        if (this.btnMin) {
            this.btnMin.addEventListener("click", () => this.close());
        }
        if (this.btnExpand) {
            this.btnExpand.addEventListener("click", () => this.toggleExpand());
        }
        if (this.btnNewChat) {
            this.btnNewChat.addEventListener("click", () => this.resetChat());
        }

        // Modo REN Toggle y Botones
        if (this.btnToggleRen) {
            this.btnToggleRen.addEventListener("click", () => this.toggleRenMode());
        }
        if (this.btnPickElement) {
            this.btnPickElement.addEventListener("click", () => this.toggleElementPicker());
        }
        if (this.btnClearTarget) {
            this.btnClearTarget.addEventListener("click", () => this.clearRenTarget());
        }
        if (this.btnResetRen) {
            this.btnResetRen.addEventListener("click", () => this.resetRenModifications());
        }
        this.renChips.forEach(chip => {
            chip.addEventListener("click", () => {
                const act = chip.getAttribute("data-ren-action");
                if (act) this.handleRenActionClick(act);
            });
        });

        // Selección de modelos
        this.modelCards.forEach(card => {
            card.addEventListener("click", () => {
                const modelId = card.getAttribute("data-model");
                this.selectModel(modelId);
            });
        });

        // Acciones rápidas & sugerencias
        const handlePromptClick = (btn) => {
            const promptText = btn.getAttribute("data-prompt");
            if (promptText) {
                if (this.promptInput) {
                    this.promptInput.value = promptText;
                    this.autoGrowInput();
                }
                this.submitCurrentPrompt();
            }
        };

        this.quickBtns.forEach(btn => btn.addEventListener("click", () => handlePromptClick(btn)));
        this.suggChips.forEach(btn => btn.addEventListener("click", () => handlePromptClick(btn)));

        // Envío de formulario o botón de parada si está pensando
        if (this.promptForm) {
            this.promptForm.addEventListener("submit", (e) => {
                e.preventDefault();
                if (this.isThinking) {
                    this.stopCurrent();
                } else {
                    this.submitCurrentPrompt();
                }
            });
        }

        if (this.promptInput) {
            this.promptInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    this.submitCurrentPrompt();
                }
            });
            this.promptInput.addEventListener("input", () => this.autoGrowInput());
        }
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        if (!this.deck) return;
        this.isOpen = true;
        this.deck.classList.remove("agent-hidden");
        this.deck.setAttribute("aria-hidden", "false");
        setTimeout(() => {
            if (this.promptInput) this.promptInput.focus();
        }, 150);
    }

    close() {
        if (!this.deck) return;
        this.isOpen = false;
        this.deck.classList.add("agent-hidden");
        this.deck.setAttribute("aria-hidden", "true");
    }

    toggleExpand() {
        if (!this.deck) return;
        this.isExpanded = !this.isExpanded;
        this.deck.classList.toggle("agent-expanded", this.isExpanded);
    }

    selectModel(modelId) {
        if (!modelId || !this.modelsMeta[modelId]) return;
        this.activeModel = modelId;
        const meta = this.modelsMeta[modelId];

        this.modelCards.forEach(c => {
            c.classList.toggle("active", c.getAttribute("data-model") === modelId);
        });

        if (this.headerPillName) this.headerPillName.textContent = meta.name;
        if (this.headerDot) this.headerDot.style.background = meta.color;
        if (this.inputModelTag) {
            this.inputModelTag.textContent = meta.name;
            this.inputModelTag.style.color = meta.color;
        }
        if (this.fabModelPill) {
            this.fabModelPill.textContent = meta.name;
            this.fabModelPill.style.color = meta.color;
        }
    }

    autoGrowInput() {
        if (!this.promptInput) return;
        this.promptInput.style.height = "auto";
        this.promptInput.style.height = Math.min(this.promptInput.scrollHeight, 130) + "px";
    }

    resetChat() {
        if (!this.messagesContainer) return;
        this.history = [];
        this.messagesContainer.innerHTML = `
            <div class="agent-message agent-msg-bot">
                <div class="agent-msg-avatar">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                        <path d="M4 11a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v7a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-7z"/>
                        <circle cx="9" cy="15" r="1"/>
                        <circle cx="15" cy="15" r="1"/>
                    </svg>
                </div>
                <div class="agent-msg-body">
                    <div class="agent-msg-author">AetherCopilot <span>${this.modelsMeta[this.activeModel].name}</span></div>
                    <div class="agent-msg-content">
                        <p>Nuevo chat iniciado con <strong>${this.modelsMeta[this.activeModel].name}</strong>. ¿En qué te ayudo ahora?</p>
                    </div>
                </div>
            </div>
        `;
    }

    appendUserMessage(text) {
        if (!this.messagesContainer) return;
        const msgDiv = document.createElement("div");
        msgDiv.className = "agent-message agent-msg-user";
        msgDiv.innerHTML = `
            <div class="agent-msg-body">
                <div>${this.escapeHtml(text)}</div>
            </div>
        `;
        this.messagesContainer.appendChild(msgDiv);
        this.scrollToBottom();
    }

    appendBotThinking() {
        if (!this.messagesContainer) return;
        const id = "botThinking_" + Date.now();
        const msgDiv = document.createElement("div");
        msgDiv.className = "agent-message agent-msg-bot";
        msgDiv.id = id;
        msgDiv.innerHTML = `
            <div class="agent-msg-avatar">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                    <path d="M4 11a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v7a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-7z"/>
                </svg>
            </div>
            <div class="agent-msg-body">
                <div class="agent-msg-author">AetherCopilot <span>${this.modelsMeta[this.activeModel].name}</span></div>
                <div class="agent-msg-content">
                    <p style="color:#94a3b8; display:flex; align-items:center; gap:8px;">
                        <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#c084fc; animation:pulse 1s infinite;"></span>
                        Pensando y ejecutando acciones...
                    </p>
                </div>
            </div>
        `;
        this.messagesContainer.appendChild(msgDiv);
        this.scrollToBottom();
        return id;
    }

    appendBotResponse(reply, actions = [], extra = {}, modelName = "GLM-5.3 Flash", reasoning = "") {
        if (!this.messagesContainer) return;
        const msgDiv = document.createElement("div");
        msgDiv.className = "agent-message agent-msg-bot";

        const uniqueThinkId = "think_" + Math.random().toString(36).substring(2, 9);
        const badgeId = "badge_" + uniqueThinkId;
        const textId = "text_" + uniqueThinkId;
        const cursorId = "cursor_" + uniqueThinkId;

        // Bloque desplegable de razonamiento / pensamiento (Estilo Antigravity / DeepSeek con Typewriter)
        let reasoningHtml = "";
        if (reasoning && reasoning.trim().length > 0) {
            reasoningHtml = `
                <details class="agent-thinking-dropdown" open>
                    <summary>
                        <span class="agent-thinking-icon">🧠</span>
                        <span>Pensamiento del modelo (${modelName})</span>
                        <span class="agent-thinking-badge" id="${badgeId}">Escribiendo...</span>
                    </summary>
                    <div class="agent-thinking-body">
                        <span class="agent-typewriter-text" id="${textId}"></span><span class="agent-typewriter-cursor" id="${cursorId}">|</span>
                    </div>
                </details>
            `;
        }

        // Badges visuales de acciones y archivos de contexto estilo Antigravity
        let actionsHtml = "";
        let contextPillsHtml = "";

        if (extra && extra.context_files && Array.isArray(extra.context_files) && extra.context_files.length > 0) {
            contextPillsHtml = `
                <div style="margin-bottom:8px; display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
                    <span style="font-size:11px; color:#94a3b8; font-weight:700; display:flex; align-items:center; gap:4px;">
                        📁 Contexto de código activo:
                    </span>
                    ${extra.context_files.map(f => `
                        <span style="font-size:11px; background:rgba(56,189,248,0.12); color:#38bdf8; border:1px solid rgba(56,189,248,0.3); padding:2px 8px; border-radius:12px; font-family:'Geist Mono', monospace; font-weight:600;">
                            ${this.escapeHtml(f)}
                        </span>
                    `).join("")}
                </div>
            `;
        }

        if (actions && actions.length > 0) {
            actionsHtml = `<div style="margin-bottom:8px; display:flex; flex-wrap:wrap; gap:6px;">`;
            actions.forEach(a => {
                const type = a.type || "action";
                let icon = "⚡";
                let label = "Acción ejecutada";
                if (type === "navigate") { icon = "🚀"; label = `Navegando a: ${a.view || "Mesa"}`; }
                else if (type === "create_project") { icon = "🎬"; label = `Lanzando emisión: ${a.topic?.slice(0, 24)}...`; }
                else if (type === "create_thumbnail") { icon = "🖼️"; label = "Miniatura YouTube Creada"; }
                else if (type === "customize_ui") { icon = "🎨"; label = "Estilo de UI Actualizado"; }
                else if (type === "ren_mutate") { icon = "🛠️"; label = `Modo REN: ${a.selector || "UI"}`; }
                else if (type === "ren_reset") { icon = "🔄"; label = "Modo REN: UI Restablecida"; }
                else if (type === "modify_popups") { icon = "📐"; label = "Pop-ups Ajustados"; }
                else if (type === "edit_file") {
                    icon = "✏️";
                    const p = a.path || a.file_written || "archivo";
                    const fName = p.split("/").pop();
                    label = `edit_file: ${fName} [✓ Modificado en disco]`;
                }
                else if (type === "read_file") {
                    icon = "📖";
                    const fName = (a.path || "archivo").split("/").pop();
                    label = `read_file: ${fName} [✓ Leído]`;
                }
                else if (type === "list_files") {
                    icon = "📁";
                    label = `list_files: ${a.dir || "web"} [✓ Listado]`;
                }

                actionsHtml += `<span class="agent-action-badge success">${icon} ${label}</span>`;
            });
            actionsHtml += `</div>`;
        }

        // Miniatura YouTube incrustada si existe
        let thumbHtml = "";
        if (extra && extra.thumbnail && extra.thumbnail.url) {
            thumbHtml = `
                <div class="agent-thumb-preview-card">
                    <img src="${extra.thumbnail.url}" alt="Portada YouTube">
                    <div class="agent-thumb-preview-footer">
                        <span style="font-size:11px; font-weight:700; color:#cbd5e1;">Miniatura 1280x720 (Alta Retención)</span>
                        <a href="${extra.thumbnail.url}" download="${extra.thumbnail.filename}" style="font-size:11px; font-weight:700; background:#a855f7; color:#fff; padding:4px 10px; border-radius:6px; text-decoration:none;">Descargar HD</a>
                    </div>
                </div>
            `;
        }

        let cleanReply = reply || "";
        if (typeof cleanReply === "string") {
            cleanReply = cleanReply.trim();
            if (cleanReply.startsWith("{") && cleanReply.includes('"reply"')) {
                try {
                    const parsed = JSON.parse(cleanReply);
                    if (parsed.reply) cleanReply = parsed.reply;
                } catch (e) {
                    const m = cleanReply.match(/"reply"\s*:\s*"((?:\\.|[^"\\])*)"/s);
                    if (m) cleanReply = m[1];
                }
            }
            cleanReply = cleanReply.replace(/\\n/g, "\n").replace(/\\"/g, '"').replace(/\\\\/g, '\\');
        }

        const formattedReply = this.formatMarkdown(cleanReply);

        msgDiv.innerHTML = `
            <div class="agent-msg-avatar">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
                    <path d="M4 11a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v7a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-7z"/>
                    <circle cx="9" cy="15" r="1"/>
                    <circle cx="15" cy="15" r="1"/>
                </svg>
            </div>
            <div class="agent-msg-body">
                <div class="agent-msg-author">AetherCopilot <span>${modelName}</span></div>
                <div class="agent-msg-content">
                    ${reasoningHtml}
                    ${contextPillsHtml}
                    ${actionsHtml}
                    ${formattedReply}
                    ${thumbHtml}
                </div>
            </div>
        `;
        this.messagesContainer.appendChild(msgDiv);
        this.scrollToBottom();

        // Activar botones interactivos de código: Copiar y Aplicar en vivo
        msgDiv.querySelectorAll(".agent-code-copy-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const code = decodeURIComponent(btn.getAttribute("data-code") || "");
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(code).then(() => {
                        const original = btn.textContent;
                        btn.textContent = "✓ Copiado";
                        setTimeout(() => { btn.textContent = original; }, 2000);
                    });
                }
            });
        });

        msgDiv.querySelectorAll(".agent-code-apply-btn").forEach(btn => {
            btn.addEventListener("click", async () => {
                const code = decodeURIComponent(btn.getAttribute("data-code") || "");
                btn.textContent = "⏳ Aplicando...";
                btn.disabled = true;

                // 1. Inyectar en vivo en el DOM
                let styleEl = document.getElementById("agentLiveAppliedStyles");
                if (!styleEl) {
                    styleEl = document.createElement("style");
                    styleEl.id = "agentLiveAppliedStyles";
                    document.head.appendChild(styleEl);
                }
                styleEl.textContent += "\n" + code;

                // 2. Cache-bust stylesheets
                document.querySelectorAll('link[rel="stylesheet"]').forEach(l => {
                    const base = l.href.split('?')[0];
                    l.href = `${base}?v=${Date.now()}`;
                });

                // 3. Persistir en disco via API edit-files
                try {
                    const resp = await fetch("/api/agent/edit-files", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            ops: [{
                                op: "append",
                                path: "web/static/css/theme/matte-dark.css",
                                content: `\n/* AetherCopilot Live UI Apply */\n${code}\n`
                            }]
                        })
                    });
                    const d = await resp.json();
                    if (d.ok) {
                        btn.textContent = "✓ Aplicado en disco";
                        btn.style.background = "#059669";
                        this.showToast("⚡ Estilos aplicados en pantalla y guardados en matte-dark.css", "success");
                    } else {
                        btn.textContent = "✓ Aplicado en vivo";
                    }
                } catch (e) {
                    btn.textContent = "✓ Aplicado en vivo";
                }
            });
        });

        // Disparar animación de escritura typewriter para el pensamiento
        if (reasoning && reasoning.trim().length > 0) {
            const textEl = document.getElementById(textId);
            const cursorEl = document.getElementById(cursorId);
            const badgeEl = document.getElementById(badgeId);
            if (textEl) {
                this.streamTypewriter(textEl, cursorEl, badgeEl, reasoning.trim());
            }
        }
    }

    /**
     * Animación fluida de escritura palabra/carácter por carácter (Estilo Antigravity)
     */
    streamTypewriter(textEl, cursorEl, badgeEl, fullText, speed = 10) {
        if (!textEl) return;
        if (this.currentTypewriterInterval) {
            clearInterval(this.currentTypewriterInterval);
            this.currentTypewriterInterval = null;
        }

        let index = 0;
        const total = fullText.length;
        const chunk = total > 400 ? 5 : (total > 160 ? 3 : 1);

        this.currentTypewriterInterval = setInterval(() => {
            if (index < total) {
                index = Math.min(index + chunk, total);
                textEl.textContent = fullText.substring(0, index);
                this.scrollToBottom();
            } else {
                clearInterval(this.currentTypewriterInterval);
                this.currentTypewriterInterval = null;
                if (badgeEl) {
                    badgeEl.textContent = "Completado";
                    badgeEl.style.borderColor = "rgba(16, 185, 129, 0.4)";
                    badgeEl.style.color = "#34d399";
                }
                if (cursorEl) {
                    cursorEl.style.transition = "opacity 0.4s ease";
                    cursorEl.style.opacity = "0";
                    setTimeout(() => { if (cursorEl) cursorEl.remove(); }, 400);
                }
            }
        }, speed);
    }

    scrollToBottom() {
        if (!this.messagesContainer) return;
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    collectAppContext() {
        const urlParams = new URLSearchParams(window.location.search);
        const curProjId = urlParams.get("project") || urlParams.get("task") || window.currentProjectId || null;
        const curTitle = document.getElementById("topbarProjectTitle")?.textContent || "";
        const activeView = window.activeMode || "studio";
        const aspect = document.querySelector('input[name="kaiAspectRatio"]:checked')?.value || "16:9";

        const curSelItem = (typeof window.getSelectedItem === "function") ? window.getSelectedItem() : null;
        const selItemData = curSelItem ? {
            type: window.selectedEditorItem?.type,
            id: window.selectedEditorItem?.id,
            headline: curSelItem.headline || curSelItem.title || curSelItem.concept || curSelItem.name,
            stat_value: curSelItem.stat_value,
            body: curSelItem.body,
            scene_id: curSelItem.scene_id,
            start: curSelItem.start,
            duration: curSelItem.duration || (curSelItem.end ? curSelItem.end - curSelItem.start : 7)
        } : null;

        return {
            current_project_id: curProjId,
            current_project_name: curTitle,
            active_view: activeView,
            aspect_ratio: aspect,
            is_ren_mode: this.isRenMode,
            target_selector: this.selectedElementSelector,
            selected_timeline_item: selItemData,
        };
    }

    stopCurrent() {
        if (this.currentTypewriterInterval) {
            clearInterval(this.currentTypewriterInterval);
            this.currentTypewriterInterval = null;
        }
        if (this.currentAbortController) {
            this.currentAbortController.abort();
            this.currentAbortController = null;
        }
        this.isThinking = false;
        if (this.currentThinkingId) {
            const thinkEl = document.getElementById(this.currentThinkingId);
            if (thinkEl) thinkEl.remove();
            this.currentThinkingId = null;
        }
        this.resetSendButton();
        this.appendBotResponse("⏹️ **Generación detenida a petición del usuario.** ¿Deseas hacer otra consulta o pedir otra acción?", [], {}, "AetherCopilot");
    }

    resetSendButton() {
        if (!this.btnSend) return;
        this.btnSend.innerHTML = `
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
        `;
        this.btnSend.style.background = "";
        this.btnSend.title = "Enviar mensaje";
        this.btnSend.disabled = false;
    }

    setStopButton() {
        if (!this.btnSend) return;
        this.btnSend.innerHTML = `<span style="font-size:13px; font-weight:800; display:flex; align-items:center; justify-content:center;">■</span>`;
        this.btnSend.style.background = "#ef4444";
        this.btnSend.title = "Detener generación en curso";
        this.btnSend.disabled = false;
    }

    async submitCurrentPrompt() {
        if (!this.promptInput) return;
        const text = this.promptInput.value.trim();
        if (!text) return;

        // Si ya había una tarea pensando, se aborta limpiamente
        if (this.isThinking && this.currentAbortController) {
            this.currentAbortController.abort();
            this.currentAbortController = null;
            if (this.currentThinkingId) {
                const prevEl = document.getElementById(this.currentThinkingId);
                if (prevEl) prevEl.remove();
            }
        }

        this.promptInput.value = "";
        this.autoGrowInput();
        this.appendUserMessage(text);
        this.isThinking = true;
        this.setStopButton();

        this.currentThinkingId = this.appendBotThinking();
        const appContext = this.collectAppContext();
        this.currentAbortController = new AbortController();

        // Preparar historial (solo texto plano para ahorrar tokens)
        const historyToSend = this.history.slice(-10).map(h => ({
            role: h.role,
            content: typeof h.content === "string" ? h.content.slice(0, 300) : String(h.content).slice(0, 300)
        }));

        try {
            const resp = await fetch("/api/agent/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                signal: this.currentAbortController.signal,
                body: JSON.stringify({
                    message: text,
                    model_id: this.activeModel,
                    app_context: appContext,
                    history: historyToSend,
                }),
            });

            const data = await resp.json();
            const thinkEl = document.getElementById(this.currentThinkingId);
            if (thinkEl) thinkEl.remove();
            this.currentThinkingId = null;

            if (!resp.ok) {
                throw new Error(data.detail || "Error al procesar mensaje");
            }

            // ── CASO ESPECIAL: El modelo NIM tarda > 12s ──
            if (data.status === "nim_slow") {
                this.isThinking = false;
                this.resetSendButton();
                this.currentAbortController = null;
                this.appendNimSlowCard(data.job_id, data.model_name, text, historyToSend, appContext);
                return;
            }

            const modelLabel = this.modelsMeta[data.model_used]?.name || this.modelsMeta[this.activeModel]?.name || data.model_used;
            this.appendBotResponse(data.reply, data.actions, data.extra, modelLabel, data.reasoning);

            // Guardar en historial de conversación
            this.history.push({ role: "user", content: text });
            this.history.push({ role: "assistant", content: data.reply || "" });
            // Mantener máximo 20 turnos
            if (this.history.length > 20) this.history = this.history.slice(-20);

            // EJECUTAR ACCIONES EN LA APLICACIÓN
            if (data.actions && Array.isArray(data.actions)) {
                this.executeAppActions(data.actions, data.extra);
            }
        } catch (err) {
            if (err.name === "AbortError") {
                console.log("[AgentCopilot] Petición abortada.");
                return;
            }
            console.error("[AgentCopilot] Error:", err);
            const thinkEl = document.getElementById(this.currentThinkingId);
            if (thinkEl) thinkEl.remove();
            this.currentThinkingId = null;
            this.appendBotResponse(`⚠️ No se pudo completar la solicitud: ${err.message}`, [], {}, "Error");
        } finally {
            this.isThinking = false;
            this.currentAbortController = null;
            this.resetSendButton();
        }
    }

    /**
     * Ejecuta las acciones devueltas por el agente directamente sobre la UI y plataforma.
     */
    executeAppActions(actions, extra) {
        if (!Array.isArray(actions)) return;
        // ¿Alguna acción escribió archivos reales? → necesitamos recargar
        let needsReload = false;
        const filesEdited = [];

        actions.forEach(rawAction => {
            if (!rawAction) return;
            let action = Object.assign({}, rawAction);
            // Normalizar formato polimórfico
            if (!action.type) {
                const VALID = ["ren_mutate","ren_reset","navigate","create_project","create_thumbnail",
                    "open_project","show_notification","customize_ui","modify_popups",
                    "highlight_element","set_playback","switch_model","edit_file"];
                for (const key of Object.keys(action)) {
                    if (VALID.includes(key)) {
                        const val = action[key];
                        if (typeof val === "object" && val !== null) {
                            action = Object.assign({ type: key }, val);
                        } else if (typeof val === "string" && key === "navigate") {
                            action = { type: "navigate", view: val };
                        } else {
                            action = { type: key, value: val };
                        }
                        break;
                    }
                }
            }
            const type = action.type;

            // ── ACCIÓN REAL: Archivo modificado en disco ──
            if (type === "edit_file") {
                const targetPath = action.path || action.file_written || "";
                const isCss = targetPath.endsWith(".css");
                if (isCss) {
                    // Inyección y hot-reload visual instantáneo (sin recargar ni perder el chat)
                    let liveStyle = document.getElementById("agentLiveAppliedStyles");
                    if (!liveStyle) {
                        liveStyle = document.createElement("style");
                        liveStyle.id = "agentLiveAppliedStyles";
                        document.head.appendChild(liveStyle);
                    }
                    if (action.css_code || action.content) {
                        liveStyle.textContent += "\n" + (action.css_code || action.content);
                    }
                    // Refrescar links de stylesheet
                    document.querySelectorAll('link[rel="stylesheet"]').forEach(l => {
                        const base = l.href.split("?")[0];
                        l.href = `${base}?v=${Date.now()}`;
                    });
                    this.showToast(`🎨 Estilos en ${targetPath.split('/').pop()} aplicados en pantalla y guardados en disco.`, "success");
                } else if (action.reload) {
                    needsReload = true;
                    filesEdited.push(targetPath);
                }
            }

            // Modificación de tarjeta de línea de tiempo por IA
            if (type === "modify_timeline_card" || type === "modify_card") {
                if (typeof window.updateCardFromCopilot === "function") {
                    const ok = window.updateCardFromCopilot(action);
                    if (ok) {
                        this.showToast(`📊 Tarjeta "${action.headline || action.card_id}" actualizada con éxito en la línea de tiempo.`, "success");
                    }
                }
            }


            // 0. Cambio de modelo
            if (type === "switch_model" && action.model_id) {
                this.selectModel(action.model_id);
            }

            // 1. Navegación
            if (type === "navigate") {
                const targetView = (action.view || "studio").toLowerCase();
                if (typeof window.switchMode === "function") {
                    if (targetView === "mesa" || targetView === "studio") {
                        window.switchMode("studio");
                    } else if (targetView === "projects") {
                        window.switchMode("projects");
                    } else if (targetView === "streamer") {
                        window.switchMode("streamer");
                    } else if (targetView === "copilot") {
                        window.switchMode("copilot");
                    } else if (targetView === "multiagent" || targetView === "multi-agent" || targetView === "dev") {
                        window.switchMode("multiagent");
                    }
                }
                if (action.project_id && typeof window.openProject === "function") {
                    window.openProject(action.project_id);
                }
            }

            // 2. Abrir proyecto específico
            if (type === "open_project" && action.project_id) {
                if (typeof window.openProject === "function") {
                    window.openProject(action.project_id);
                    if (typeof window.switchMode === "function") window.switchMode("studio");
                }
            }

            // 3. Creación de proyecto
            if (type === "create_project") {
                // IDs reales verificados: streamerTopic, streamerDuration, streamerFormat, startStreamerBtn
                const topicInput = document.getElementById("streamerTopic") || document.getElementById("kaiTopicInput");
                const durSelect  = document.getElementById("streamerDuration") || document.getElementById("kaiDurationSelect");
                const fmtSelect  = document.getElementById("streamerFormat");
                const startBtn   = document.getElementById("startStreamerBtn");
                // Navegar al streamer primero para asegurar que los controles estén visibles
                if (typeof window.switchMode === "function") window.switchMode("streamer");
                if (topicInput && action.topic) topicInput.value = action.topic;
                if (durSelect && action.duration_sec) durSelect.value = String(action.duration_sec);
                if (fmtSelect && action.aspect_ratio) {
                    // streamerFormat usa valores como "16:9", "9:16", "1:1"
                    fmtSelect.value = action.aspect_ratio;
                }
                if (startBtn) {
                    // Pequeño delay para que el DOM procese los valores antes del submit
                    setTimeout(() => startBtn.click(), 150);
                }
            }

            // 4. Miniatura generada
            if (type === "create_thumbnail" || (extra && extra.thumbnail)) {
                const thumb = (extra && extra.thumbnail) || action;
                const thumbImg  = document.getElementById("resThumbnailImg");
                const thumbCard = document.getElementById("resThumbnailCard");
                const thumbBtn  = document.getElementById("btnDownloadThumbnail");
                if (thumbImg && thumb.url) {
                    thumbImg.src = thumb.url;
                    if (thumbCard) thumbCard.style.display = "flex";
                    if (thumbBtn) thumbBtn.href = thumb.url;
                }
            }

            // 5. Personalización de colores y acentos
            if (type === "customize_ui") {
                if (action.accent_color) {
                    document.documentElement.style.setProperty("--prism-accent", action.accent_color);
                    document.documentElement.style.setProperty("--neon-cyan", action.accent_color);
                    const styleTag = document.getElementById("agentCustomUiStyles") || document.createElement("style");
                    styleTag.id = "agentCustomUiStyles";
                    styleTag.textContent = `
                        .streamer-btn-primary, .prism-sb-tab.active, .agent-fab-launcher {
                            border-color: ${action.accent_color} !important;
                            box-shadow: 0 0 16px ${action.accent_color}44 !important;
                        }
                    `;
                    document.head.appendChild(styleTag);
                }
                if (action.bg_color) {
                    document.documentElement.style.setProperty("--surface-1", action.bg_color);
                }
            }

            // 6. MODO REN: Mutaciones en vivo
            if (type === "ren_mutate") {
                this.applyRenMutation(action);
            }

            // 7. MODO REN: Reseteo
            if (type === "ren_reset") {
                this.resetRenModifications();
            }

            // 8. Modificar popups
            if (type === "modify_popups") {
                const scale = action.scale || "medium";
                const style = action.style || "broadcast_amber";
                const styleTag = document.getElementById("agentPopupStyles") || document.createElement("style");
                styleTag.id = "agentPopupStyles";
                const scaleMap = { large: "1.15", medium: "1", small: "0.85" };
                const sc = scaleMap[scale] || "1";
                styleTag.textContent = `.popup-overlay { transform: scale(${sc}); } .popup-card { --popup-style: '${style}'; }`;
                document.head.appendChild(styleTag);
            }

            // 9. Resaltar elemento con pulso
            if (type === "highlight_element" && action.selector) {
                const target = document.querySelector(action.selector);
                if (target) {
                    target.scrollIntoView({ behavior: "smooth", block: "center" });
                    const color = action.color || "#38bdf8";
                    target.style.transition = "box-shadow 0.3s ease";
                    target.style.boxShadow = `0 0 28px ${color}, 0 0 8px ${color}88`;
                    setTimeout(() => { target.style.boxShadow = ""; }, 2800);
                }
            }

            // 10. Notificación toast
            if (type === "show_notification") {
                this.showToast(action.message || "Acción completada.", action.level || "info");
            }

            // 11. Control de reproducción
            if (type === "set_playback") {
                const video = document.getElementById("masterVideoPlayer") || document.getElementById("videoPlayer") || document.querySelector("video");
                if (video) {
                    if (action.action === "play") video.play();
                    else if (action.action === "pause") video.pause();
                    else if (action.action === "seek" && action.time != null) {
                        video.currentTime = Number(action.time);
                    }
                }
            }
        });

        // ── Si se editaron archivos que requieren recarga (HTML / JS estructurales) ──
        if (needsReload && filesEdited.length > 0) {
            const fileList = filesEdited.map(f => f.split("/").pop()).join(", ");
            this.showToast(`✏️ Archivos estructurales modificados: ${fileList} — Recargando...`, "info");
            setTimeout(() => {
                window.location.reload();
            }, 1800);
        }
    }

    /**
     * Muestra una notificación toast flotante en la app.
     */
    showToast(message, level = "info") {
        const colors = {
            success: { bg: "#10b981", icon: "✅" },
            error:   { bg: "#ef4444", icon: "❌" },
            warning: { bg: "#f59e0b", icon: "⚠️" },
            info:    { bg: "#38bdf8", icon: "ℹ️" },
        };
        const c = colors[level] || colors.info;
        const toast = document.createElement("div");
        toast.style.cssText = `
            position: fixed; bottom: 88px; right: 24px; z-index: 99999;
            background: #1e293b; border: 1px solid ${c.bg}55;
            border-left: 3px solid ${c.bg}; color: #e2e8f0;
            padding: 12px 18px; border-radius: 10px;
            font-size: 13px; font-weight: 500; max-width: 320px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            display: flex; align-items: center; gap: 10px;
            animation: slideInRight 0.3s ease;
            pointer-events: none;
        `;
        toast.innerHTML = `<span>${c.icon}</span><span>${this.escapeHtml(message)}</span>`;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            toast.style.opacity = "0";
            toast.style.transform = "translateX(20px)";
            setTimeout(() => toast.remove(), 400);
        }, 3500);
    }

    /* =========================================================================
       TARJETA INTERACTIVA: MODELO NIM LENTO (> 12s)
       ========================================================================= */

    /**
     * Muestra una tarjeta en el chat cuando un modelo NIM tarda más de 12s.
     * El usuario puede elegir: esperar al modelo original o cambiar a Gemini.
     */
    appendNimSlowCard(jobId, modelName, originalText, historyToSend, appContext) {
        if (!this.messagesContainer) return;
        const cardId = `nim-slow-${jobId}`;
        const card = document.createElement("div");
        card.id = cardId;
        card.className = "agent-message agent-msg-bot agent-nim-slow-card";
        card.innerHTML = `
            <div class="agent-msg-avatar" style="background: rgba(245,158,11,0.15); border-color: rgba(245,158,11,0.4);">
                <span style="font-size:16px;">⏳</span>
            </div>
            <div class="agent-msg-body" style="flex:1;">
                <div class="agent-msg-author" style="color:#f59e0b;">
                    AetherCopilot <span>Modelo Lento</span>
                </div>
                <div class="agent-msg-content">
                    <p><strong>${this.escapeHtml(modelName)}</strong> está procesando tu solicitud pero tardó más de 12 segundos.</p>
                    <p style="color:#94a3b8; font-size:12px; margin-top:4px;">El modelo NIM sigue trabajando en segundo plano. ¿Qué prefieres hacer?</p>
                    <div style="display:flex; gap:10px; margin-top:12px; flex-wrap:wrap;">
                        <button class="agent-nim-btn-gemini" data-job="${jobId}" style="
                            background: linear-gradient(135deg, rgba(245,158,11,0.2), rgba(245,158,11,0.1));
                            border: 1px solid rgba(245,158,11,0.5); color: #fbbf24;
                            padding: 8px 16px; border-radius: 8px; cursor: pointer;
                            font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 6px;
                            transition: all 0.2s ease;
                        ">
                            ⚡ Continuar con Gemini
                        </button>
                        <button class="agent-nim-btn-wait" data-job="${jobId}" data-model="${this.escapeHtml(modelName)}" style="
                            background: rgba(255,255,255,0.05);
                            border: 1px solid rgba(255,255,255,0.15); color: #94a3b8;
                            padding: 8px 16px; border-radius: 8px; cursor: pointer;
                            font-size: 12px; font-weight: 500; display: flex; align-items: center; gap: 6px;
                            transition: all 0.2s ease;
                        ">
                            ⏳ Esperar con <strong style="color:#e2e8f0; margin-left:3px;">${this.escapeHtml(modelName)}</strong>
                        </button>
                    </div>
                    <div class="agent-nim-timer" style="margin-top:8px; font-size:11px; color:#475569;">
                        Tiempo transcurrido: <span class="agent-nim-elapsed" id="nim-elapsed-${jobId}">12</span>s
                    </div>
                </div>
            </div>
        `;
        this.messagesContainer.appendChild(card);
        this.scrollToBottom();

        // Contador de tiempo en vivo
        let elapsed = 12;
        const timerInterval = setInterval(() => {
            elapsed++;
            const el = document.getElementById(`nim-elapsed-${jobId}`);
            if (el) el.textContent = elapsed;
            else clearInterval(timerInterval);
        }, 1000);

        // Botón: Cambiar a Gemini
        card.querySelector(".agent-nim-btn-gemini").addEventListener("click", async () => {
            clearInterval(timerInterval);
            card.remove();
            // Cancelar el job NIM en background
            fetch(`/api/agent/wait/${jobId}`, { method: "DELETE" }).catch(() => {});
            // Nueva llamada directa con Gemini
            this.isThinking = true;
            this.setStopButton();
            const thinkId = this.appendBotThinking();
            this.currentAbortController = new AbortController();
            try {
                const r = await fetch("/api/agent/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    signal: this.currentAbortController.signal,
                    body: JSON.stringify({ message: originalText, model_id: "gemini", app_context: appContext, history: historyToSend }),
                });
                const d = await r.json();
                document.getElementById(thinkId)?.remove();
                const label = this.modelsMeta["gemini"]?.name || "Gemini";
                this.appendBotResponse(d.reply, d.actions, d.extra, label, d.reasoning);
                this.history.push({ role: "user", content: originalText });
                this.history.push({ role: "assistant", content: d.reply || "" });
                if (d.actions?.length) this.executeAppActions(d.actions, d.extra);
            } catch (e) {
                document.getElementById(thinkId)?.remove();
                this.appendBotResponse("⚠️ Error al contactar Gemini.", [], {}, "Error");
            } finally {
                this.isThinking = false;
                this.resetSendButton();
                this.currentAbortController = null;
            }
        });

        // Botón: Esperar con el modelo original
        card.querySelector(".agent-nim-btn-wait").addEventListener("click", async () => {
            clearInterval(timerInterval);
            // Actualizar la tarjeta para mostrar que está esperando
            card.querySelector(".agent-msg-content").innerHTML = `
                <p>⏳ Esperando respuesta de <strong>${this.escapeHtml(modelName)}</strong>...</p>
                <p style="color:#475569; font-size:11px;">El modelo está procesando. Esto puede tardar hasta 90 segundos.</p>
            `;
            try {
                const r = await fetch(`/api/agent/wait/${jobId}`);
                const d = await r.json();
                card.remove();
                const label = this.modelsMeta[this.activeModel]?.name || modelName;
                if (d.status === "ok") {
                    this.appendBotResponse(d.reply, d.actions, d.extra, label, d.reasoning);
                    this.history.push({ role: "user", content: originalText });
                    this.history.push({ role: "assistant", content: d.reply || "" });
                    if (d.actions?.length) this.executeAppActions(d.actions, d.extra);
                } else {
                    this.appendBotResponse(d.reply || "⚠️ El modelo no respondió a tiempo.", [], {}, label);
                }
            } catch (e) {
                card.remove();
                this.appendBotResponse(`⚠️ Error al esperar al modelo: ${e.message}`, [], {}, modelName);
            }
        });
    }

    /* =========================================================================
       MÉTODOS DEL MODO REN (RENDER / EDIT NETWORK) & SELECTOR DE ELEMENTOS
       ========================================================================= */

    toggleRenMode(force) {
        this.isRenMode = force !== undefined ? force : !this.isRenMode;
        if (this.deck) {
            this.deck.classList.toggle("ren-mode-active", this.isRenMode);
        }
        if (this.btnToggleRen) {
            this.btnToggleRen.classList.toggle("active", this.isRenMode);
        }
        if (this.renToolbar) {
            this.renToolbar.style.display = this.isRenMode ? "flex" : "none";
        }
        if (this.promptInput) {
            if (this.isRenMode) {
                this.promptInput.placeholder = "Modo REN activo: selecciona elementos o escribe 'cambia el botón a cian', 'oculta la barra'...";
            } else {
                this.promptInput.placeholder = "Pídele al agente lo que quieras en la app... (Enter para enviar)";
                this.stopElementPicker();
            }
        }
    }

    toggleElementPicker() {
        if (this.isInspectorActive) {
            this.stopElementPicker();
        } else {
            this.startElementPicker();
        }
    }

    startElementPicker() {
        if (!this.isRenMode) {
            this.toggleRenMode(true);
        }
        this.isInspectorActive = true;
        document.body.classList.add("ren-inspector-active");

        if (this.btnPickElement) {
            this.btnPickElement.classList.add("picking");
            this.btnPickElement.innerHTML = `<span>✕ Cancelar Selección</span>`;
        }
        if (this.deck) {
            this.deck.style.opacity = "0.35";
            this.deck.style.pointerEvents = "none";
        }
        if (this.inspectorOverlay) {
            this.inspectorOverlay.style.display = "block";
        }

        this._onInspectorMove = (e) => {
            const el = document.elementFromPoint(e.clientX, e.clientY);
            if (!el || el.closest("#agentChatDeck") || el.closest("#agentRenInspectorOverlay")) {
                if (this.inspectorOverlay) this.inspectorOverlay.style.display = "none";
                return;
            }

            const rect = el.getBoundingClientRect();
            if (this.inspectorOverlay) {
                this.inspectorOverlay.style.display = "block";
                this.inspectorOverlay.style.top = `${rect.top}px`;
                this.inspectorOverlay.style.left = `${rect.left}px`;
                this.inspectorOverlay.style.width = `${rect.width}px`;
                this.inspectorOverlay.style.height = `${rect.height}px`;
            }

            const tagName = el.tagName.toLowerCase();
            const idPart = el.id ? `#${el.id}` : "";
            const classPart = !el.id && el.classList.length ? `.${el.classList[0]}` : "";
            if (this.inspectorTag) this.inspectorTag.textContent = tagName;
            if (this.inspectorSel) this.inspectorSel.textContent = idPart || classPart || "";
        };

        this._onInspectorClick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            const el = document.elementFromPoint(e.clientX, e.clientY);
            if (!el || el.closest("#agentChatDeck") || el.closest("#agentRenInspectorOverlay")) {
                return;
            }

            // Deducir mejor selector CSS
            let selector = "";
            if (el.id) {
                selector = `#${el.id}`;
            } else if (el.classList.length) {
                selector = `${el.tagName.toLowerCase()}.${Array.from(el.classList).slice(0, 2).join(".")}`;
            } else {
                selector = el.tagName.toLowerCase();
            }

            this.setRenTarget(selector);
            this.stopElementPicker();
        };

        this._onInspectorKey = (e) => {
            if (e.key === "Escape") {
                this.stopElementPicker();
            }
        };

        window.addEventListener("mousemove", this._onInspectorMove, { passive: true });
        window.addEventListener("click", this._onInspectorClick, { capture: true, once: true });
        window.addEventListener("keydown", this._onInspectorKey);
    }

    stopElementPicker() {
        this.isInspectorActive = false;
        document.body.classList.remove("ren-inspector-active");

        if (this.btnPickElement) {
            this.btnPickElement.classList.remove("picking");
            this.btnPickElement.innerHTML = `
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.4">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="22" y1="12" x2="18" y2="12"/>
                    <line x1="6" y1="12" x2="2" y2="12"/>
                    <line x1="12" y1="6" x2="12" y2="2"/>
                    <line x1="12" y1="22" x2="12" y2="18"/>
                </svg>
                <span>🎯 Seleccionar Elemento</span>
            `;
        }
        if (this.deck) {
            this.deck.style.opacity = "1";
            this.deck.style.pointerEvents = "auto";
        }
        if (this.inspectorOverlay) {
            this.inspectorOverlay.style.display = "none";
        }

        if (this._onInspectorMove) window.removeEventListener("mousemove", this._onInspectorMove);
        if (this._onInspectorClick) window.removeEventListener("click", this._onInspectorClick, { capture: true });
        if (this._onInspectorKey) window.removeEventListener("keydown", this._onInspectorKey);
    }

    setRenTarget(selector) {
        this.selectedElementSelector = selector;
        if (this.renTargetPill && this.renTargetSelText) {
            this.renTargetSelText.textContent = selector;
            this.renTargetPill.style.display = "inline-flex";
        }
        // Resaltar momentáneamente el elemento seleccionado
        const target = document.querySelector(selector);
        if (target) {
            target.style.transition = "box-shadow 0.3s ease";
            target.style.boxShadow = "0 0 25px #06b6d4";
            setTimeout(() => { target.style.boxShadow = ""; }, 1800);
        }
        if (this.promptInput) {
            this.promptInput.focus();
            if (!this.promptInput.value) {
                this.promptInput.value = `Modifica ${selector}: `;
                this.autoGrowInput();
            }
        }
    }

    clearRenTarget() {
        this.selectedElementSelector = null;
        if (this.renTargetPill) {
            this.renTargetPill.style.display = "none";
        }
    }

    handleRenActionClick(actionType) {
        const sel = this.selectedElementSelector || "button, .streamer-btn-primary";
        let styles = {};
        let op = "style";

        if (actionType === "color_cyan") {
            styles = { borderColor: "#06b6d4", boxShadow: "0 0 20px rgba(6, 182, 212, 0.4)", color: "#06b6d4" };
        } else if (actionType === "color_emerald") {
            styles = { borderColor: "#10b981", boxShadow: "0 0 20px rgba(16, 185, 129, 0.4)", color: "#10b981" };
        } else if (actionType === "color_purple") {
            styles = { borderColor: "#a855f7", boxShadow: "0 0 20px rgba(168, 85, 247, 0.4)", color: "#a855f7" };
        } else if (actionType === "color_amber") {
            styles = { borderColor: "#f59e0b", boxShadow: "0 0 20px rgba(245, 158, 11, 0.4)", color: "#f59e0b" };
        } else if (actionType === "glow") {
            styles = { boxShadow: "0 0 28px rgba(6, 182, 212, 0.6)", borderColor: "#38bdf8" };
        } else if (actionType === "scale_up") {
            styles = { transform: "scale(1.1)", transformOrigin: "center" };
        } else if (actionType === "hide") {
            op = "hide";
        } else if (actionType === "remove") {
            op = "remove";
        }

        this.applyRenMutation({
            selector: sel,
            operation: op,
            styles: styles,
        });

        this.appendBotResponse(`✨ **[Modo REN]** Acción ejecutada sobre \`${sel}\` (operación: \`${op}\`).`, [{
            type: "ren_mutate",
            selector: sel,
            operation: op
        }], {}, "Modo REN");
    }

    applyRenMutation(action) {
        const sel = action.selector || "body";
        const op = action.operation || "style";
        const styles = action.styles || {};

        if (op === "remove") {
            const targets = document.querySelectorAll(sel);
            targets.forEach(t => {
                t.style.setProperty("display", "none", "important");
                t.style.setProperty("height", "0", "important");
                t.style.setProperty("overflow", "hidden", "important");
                t.style.setProperty("pointer-events", "none", "important");
                t.setAttribute("data-ren-removed", "true");
            });
            this.renStylesMap[sel] = {
                display: "none",
                height: "0",
                overflow: "hidden",
                pointerEvents: "none"
            };
        } else if (op === "hide") {
            const targets = document.querySelectorAll(sel);
            targets.forEach(t => t.style.setProperty("display", "none", "important"));
            this.renStylesMap[sel] = Object.assign(this.renStylesMap[sel] || {}, { display: "none" });
        } else {
            this.renStylesMap[sel] = Object.assign(this.renStylesMap[sel] || {}, styles);
        }

        this.savePersistedRenStyles();
    }

    savePersistedRenStyles() {
        let styleTag = document.getElementById("aethercutRenCustomStyles");
        if (!styleTag) {
            styleTag = document.createElement("style");
            styleTag.id = "aethercutRenCustomStyles";
            document.head.appendChild(styleTag);
        }

        let cssContent = "";
        for (const [selector, rules] of Object.entries(this.renStylesMap)) {
            cssContent += `${selector} {\n`;
            for (const [prop, val] of Object.entries(rules)) {
                const kebabProp = prop.replace(/([A-Z])/g, "-$1").toLowerCase();
                cssContent += `  ${kebabProp}: ${val} !important;\n`;
            }
            cssContent += `}\n`;
        }

        styleTag.textContent = cssContent;
        try {
            localStorage.setItem("aethercut_ren_styles", JSON.stringify(this.renStylesMap));
        } catch (e) {
            console.warn("[Modo REN] No se pudo guardar en localStorage:", e);
        }
    }

    loadPersistedRenStyles() {
        try {
            const saved = localStorage.getItem("aethercut_ren_styles");
            if (saved) {
                this.renStylesMap = JSON.parse(saved);
                this.savePersistedRenStyles();
            }
        } catch (e) {
            console.warn("[Modo REN] Error al cargar estilos persistidos:", e);
        }
    }

    resetRenModifications() {
        this.renStylesMap = {};
        const styleTag = document.getElementById("aethercutRenCustomStyles");
        if (styleTag) styleTag.remove();
        try {
            localStorage.removeItem("aethercut_ren_styles");
        } catch (e) {}
        this.clearRenTarget();
        this.appendBotResponse("🔄 **[Modo REN]** Todos los estilos y elementos personalizados se han restablecido a la versión original de la app.", [], {}, "Modo REN");
    }

    escapeHtml(str) {
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    formatMarkdown(text) {
        if (!text) return "";

        // 1. Extraer y estructurar bloques de código estilo Antigravity ```lang ... ```
        const codeBlocks = [];
        let processed = text.replace(/```([a-zA-Z0-9_\-\.]*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            const blockId = "cb_" + Math.random().toString(36).substring(2, 9);
            codeBlocks.push({ id: blockId, lang: (lang || "code").toLowerCase(), code: code.trim() });
            return `__CODEBLOCK_PLACEHOLDER_${blockId}__`;
        });

        // 2. Formato Markdown estándar
        processed = processed
            // Negrita
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            // Cursiva
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            // Enlaces [texto](url)
            .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color:#38bdf8; text-decoration:underline;">$1</a>')
            // Código inline
            .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px; font-family:\'Geist Mono\', monospace; font-size:12px; color:#38bdf8;">$1</code>');

        // 3. Reemplazar placeholders de bloques de código por componentes interactivos
        codeBlocks.forEach(b => {
            const lowCode = b.code.toLowerCase();
            const hasBadPlanningWords = lowCode.includes("plan:") || lowCode.includes("edit_file") || lowCode.includes("replace 1:") || lowCode.includes("voy a hacer");
            const isCss = !hasBadPlanningWords && (b.lang === "css" || ((b.code.includes(";") || b.code.includes("background:") || b.code.includes("border:")) && b.code.includes("{")));
            const applyBtnHtml = isCss ? `
                <button type="button" class="agent-code-apply-btn" data-code="${encodeURIComponent(b.code)}" title="Inyectar en pantalla y guardar en matte-dark.css" style="background:linear-gradient(135deg, #10b981, #059669); color:#fff; border:none; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:4px; box-shadow:0 2px 8px rgba(16,185,129,0.3);">
                    <span>⚡ Aplicar en vivo</span>
                </button>
            ` : "";

            const blockHtml = `
                <div class="agent-code-block-wrap" style="margin:12px 0; border:1px solid rgba(255,255,255,0.12); border-radius:9px; background:#070a12; overflow:hidden; box-shadow:0 6px 20px rgba(0,0,0,0.6);">
                    <div class="agent-code-block-header" style="display:flex; justify-content:space-between; align-items:center; padding:6px 12px; background:rgba(255,255,255,0.04); border-bottom:1px solid rgba(255,255,255,0.08);">
                        <span style="font-size:10px; font-weight:700; text-transform:uppercase; color:#94a3b8; letter-spacing:0.06em; font-family:'Geist Mono', monospace;">${this.escapeHtml(b.lang || 'código')}</span>
                        <div style="display:flex; gap:6px;">
                            ${applyBtnHtml}
                            <button type="button" class="agent-code-copy-btn" data-code="${encodeURIComponent(b.code)}" title="Copiar código al portapapeles" style="background:rgba(255,255,255,0.08); color:#cbd5e1; border:1px solid rgba(255,255,255,0.12); padding:3px 8px; border-radius:6px; font-size:11px; font-weight:600; cursor:pointer;">
                                📋 Copiar
                            </button>
                        </div>
                    </div>
                    <pre style="margin:0; padding:12px; font-family:'Geist Mono', monospace; font-size:12px; line-height:1.55; color:#e2e8f0; overflow-x:auto; background:transparent;"><code>${this.escapeHtml(b.code)}</code></pre>
                </div>
            `;
            processed = processed.replace(`__CODEBLOCK_PLACEHOLDER_${b.id}__`, blockHtml);
        });

        // 4. Párrafos y listas
        const lines = processed.split("\n");
        let result = [];
        let inList = false;

        lines.forEach(line => {
            const trimmed = line.trim();
            if (trimmed.includes("agent-code-block-wrap")) {
                if (inList) { result.push("</ul>"); inList = false; }
                result.push(trimmed);
            } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
                if (!inList) {
                    result.push("<ul style=\"margin:6px 0; padding-left:18px;\">");
                    inList = true;
                }
                result.push(`<li>${trimmed.substring(2)}</li>`);
            } else {
                if (inList) {
                    result.push("</ul>");
                    inList = false;
                }
                if (trimmed) {
                    result.push(`<p style=\"margin:6px 0;\">${trimmed}</p>`);
                }
            }
        });
        if (inList) result.push("</ul>");

        return result.join("");
    }
}

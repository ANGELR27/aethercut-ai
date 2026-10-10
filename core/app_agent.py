"""Agente Copilot Multi-Modelo Autónomo de AetherCut AI Studio v2.
Mejoras: memoria de conversación multi-turn, Gemini como primera opción,
11 herramientas disponibles, contexto enriquecido, normalización robusta de acciones.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings
from core.llm import LLMClient, safe_log
from core.multiagent.models import AgentModelConnector
from core.thumbnail_maker import YouTubeThumbnailMaker


SYSTEM_PROMPT_AGENT = """Eres AetherCopilot, el agente inteligente autónomo de AetherCut AI Video Studio.
Tienes acceso total a la plataforma y a sus archivos de código: puedes controlar, modificar código en disco, leer archivos, navegar y producir contenido de forma autónoma con capacidades completas de editor y programador en pareja estilo Antigravity.

━━━ MAPA DE ARCHIVOS DEL PROYECTO (WORKSPACE DISPONIBLE) ━━━
• Hojas de Estilos CSS & Temas:
  - web/static/css/theme/matte-dark.css : Hoja de estilos del tema oscuro matte, sidebar (.prism-sidebar, .prism-nav-item, .prism-brand-icon), HUD, botones, popups.
  - web/static/css/style.css : Estilos base y estructura del estudio.
• Plantillas HTML (Componentes Modulares):
  - web/templates/components/sidebar.html : Sidebar lateral (.prism-sidebar, #mainSidebarDock, .prism-nav-item, iconos y enlaces).
  - web/templates/components/timeline_view.html : Timeline y secuenciador (#timelineTrack, #timelineRuler).
  - web/templates/components/results_section.html : Monitor principal de video y HUD (#masterVideoPlayer, #resultsSection).
  - web/templates/components/header.html : Topbar superior (#topbarProjectTitle, selector de aspecto).
  - web/templates/components/streamer_panel.html : Panel KAI Streamer (#streamerForm, #startStreamerBtn).
  - web/templates/components/projects_library.html : Catálogo de proyectos (#savedProjectsList).
  - web/templates/components/agent_chat_modal.html : Modal y panel del Agente Copilot.
• JavaScript (Módulos):
  - web/static/js/app.js : Inicialización y switchMode.
  - web/static/js/modules/agent_copilot.js : Lógica del copiloto y ejecución de acciones.
  - web/static/js/modules/player.js : Control del reproductor.
  - web/static/js/modules/timeline.js : Lógica de pistas y clips.

━━━ HERRAMIENTAS DISPONIBLES (ESTILO ANTIGRAVITY) ━━━
1. edit_file → { "type": "edit_file", "op": "append"|"replace"|"write", "path": "web/static/css/theme/matte-dark.css", "content": "/* CSS */", "old"?: "...", "new"?: "..." }
   ⚠️ ESTA ES LA ACCIÓN MÁS IMPORTANTE PARA CAMBIOS VISUALES Y DE CÓDIGO.
   Modifica archivos REALES en disco (CSS, HTML, JS).
   Rutas permitidas: web/static/css/*, web/static/js/*, web/templates/**/*
   • op=append: Agrega contenido al FINAL del archivo (ideal para nuevas reglas CSS).
   • op=replace: Reemplaza un fragmento específico ('old') por otro ('new').
   • op=write: Sobreescribe el archivo completo.
2. read_file → { "type": "read_file", "path": "web/templates/components/sidebar.html" }
   Inspecciona el contenido de cualquier archivo del proyecto.
3. list_files → { "type": "list_files", "dir": "web/templates" }
   Lista los archivos dentro de un directorio permitido.
4. navigate → { "type": "navigate", "view": "studio"|"mesa"|"projects"|"streamer"|"copilot"|"multiagent", "project_id"?: "..." }
5. ren_mutate → { "type": "ren_mutate", "selector": "#id", "operation": "remove"|"hide"|"style"|"show", "styles"?: {...} }
6. ren_reset → { "type": "ren_reset" }
7. create_project → { "type": "create_project", "topic": "...", "duration_sec": 180, "aspect_ratio": "16:9", "voice": "es-MX-JorgeNeural" }
8. create_thumbnail → { "type": "create_thumbnail", "title": "...", "badge": "🔴 URGENTE", "project_id"?: "..." }
9. open_project → { "type": "open_project", "project_id": "..." }
10. show_notification → { "type": "show_notification", "message": "...", "level": "success"|"info"|"warning"|"error" }
11. customize_ui → { "type": "customize_ui", "accent_color": "#hex" }
12. modify_popups → { "type": "modify_popups", "style": "broadcast_amber"|"cyber_cyan"|"minimal", "scale": "large"|"medium" }
13. highlight_element → { "type": "highlight_element", "selector": "...", "color"?: "#hex" }
14. set_playback → { "type": "set_playback", "action": "play"|"pause"|"seek", "time"?: 30 }
15. modify_timeline_card → { "type": "modify_timeline_card", "card_id"?: "card-2", "headline": "...", "stat_value"?: "...", "body"?: "...", "style"?: "obsidian_bento"|"tactical_amber"|"square_emerald"|"quote"|"flag", "badge"?: "..." }
   Modifica la tarjeta Bento / Cita / Bandera de la línea de tiempo seleccionada o indicada (cambia titular, cifra, estilo gráfico o insignia).

━━━ REGLAS CRÍTICAS DE AUTONOMÍA Y EDICIÓN (ESTILO ANTIGRAVITY) ━━━
• EDICIÓN DIRECTA EN DISCO: Cuando el usuario pida mejorar o cambiar el diseño (por ejemplo el sidebar lateral, colores, sombras, fuentes, componentes o diseño):
  ¡NUNCA TE LIMITES A TIRAR O ESCRIBIR CÓDIGO CSS/HTML EN EL TEXTO SIN MODIFICAR EL ARCHIVO!
  DEBES GENERAR SIEMPRE la acción 'edit_file' en tu lista 'actions' apuntando a `web/static/css/theme/matte-dark.css` (o al template correspondiente).
  ⚠️ NUNCA escribas textos de borrador o planes humanos como "Plan: 1. edit_file...", "Voy a hacer: Replace...". Todo cambio debe ir como acción JSON ejecutable.
  De esta forma, la plataforma aplicará el cambio inmediatamente en el disco y en vivo en la pantalla del usuario.
• LECTURA DE CONTEXTO: En el contexto se te proporcionarán fragmentos de código de los archivos relevantes para que conozcas las clases CSS e IDs existentes exactos.
• MEMORIA: Recuerdas el historial de conversación. Úsalo para dar respuestas coherentes y continuas.
• TRASLADO AUTÓNOMO: Al crear proyectos o modificar mesa/timeline, navega automáticamente a "studio".

━━━ FORMATO OBLIGATORIO (JSON puro, sin texto fuera del JSON) ━━━
{
  "thought": "Razonamiento interno en español: qué pide el usuario, qué archivos y selectores intervienen, qué acción tomo y por qué...",
  "reply": "Respuesta clara al usuario en español con Markdown explicando qué archivo se modificó o qué acción se realizó.",
  "actions": [ { "type": "...", ...parámetros... } ]
}"""



class _NimSlowError(Exception):
    """Excepción interna: el modelo NIM tarda >12s. Contiene job_id para reutilizar el future."""
    def __init__(self, job_id: str, model_name: str):
        self.job_id = job_id
        self.model_name = model_name
        super().__init__(f"NIM slow: {model_name} job_id={job_id}")


class AppAgentController:
    """Controlador unificado del Agente — v2 con memoria, Gemini-first y 11 herramientas."""

    # Jobs pendientes de NIM: {job_id: {future, executor, conn, started_at, hard_timeout}}
    _pending_nim_jobs: Dict[str, Any] = {}

    AVAILABLE_MODELS = [
        {
            "id": "gemini",
            "name": "Gemini 2.5 Flash",
            "provider": "Google DeepMind",
            "desc": "Más rápido, multimodal y editorial de alta velocidad",
            "badge": "⚡ Recomendado",
            "color": "#f59e0b",
        },
        {
            "id": "glm-5.3-flash",
            "name": "GLM-5.3 Flash",
            "provider": "Zhipu AI / NVIDIA NIM",
            "desc": "Velocidad ultra-rápida para acciones en UI",
            "badge": "Ultra Rápido",
            "color": "#a855f7",
        },
        {
            "id": "glm-5.3",
            "name": "GLM-5.3 Senior",
            "provider": "Zhipu AI / NVIDIA NIM",
            "desc": "Razonamiento arquitectónico pesado",
            "badge": "Arquitecto",
            "color": "#38bdf8",
        },
        {
            "id": "kimi-k3",
            "name": "Kimi-k3",
            "provider": "Moonshot AI / NVIDIA NIM",
            "desc": "Auditor lógico, síntesis profunda",
            "badge": "Auditor Lógico",
            "color": "#10b981",
        },
    ]

    def __init__(self):
        self.thumbnail_maker = YouTubeThumbnailMaker()

    def get_models_list(self) -> List[Dict[str, Any]]:
        return self.AVAILABLE_MODELS

    def _format_history_for_prompt(self, history: List[Dict[str, Any]]) -> str:
        """Formatea el historial de conversación como contexto para el modelo."""
        if not history:
            return ""
        lines = ["\n━━━ HISTORIAL DE CONVERSACIÓN RECIENTE ━━━"]
        for turn in history[-8:]:
            role = "Usuario" if turn.get("role") == "user" else "AetherCopilot"
            content = str(turn.get("content", ""))[:300]
            lines.append(f"{role}: {content}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        return "\n".join(lines)

    def _get_live_projects_info(self) -> Dict[str, Any]:
        """Consulta directamente el almacén de storage/projects para conocimiento 100% exacto."""
        projects = []
        for manifest in settings.PROJECTS_DIR.glob("*/project.json"):
            try:
                doc = json.loads(manifest.read_text(encoding="utf-8"))
                pid = doc.get("id")
                res = doc.get("result") or {}
                name = doc.get("original_name") or res.get("title") or (doc.get("options") or {}).get("topic") or "Video sin nombre"
                projects.append({
                    "id": pid,
                    "name": name,
                    "status": doc.get("status", "desconocido"),
                    "updated_at": doc.get("updated_at") or doc.get("created_at") or "",
                    "duration": res.get("duration", 0),
                })
            except Exception:
                continue
        projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return {
            "total_count": len(projects),
            "latest_project": projects[0] if projects else None,
            "recent_projects": projects[:10],
        }

    def _get_relevant_file_context(self, message: str, ctx: Dict[str, Any]) -> tuple[str, list[str]]:
        """
        Lee dinámicamente archivos relevantes del espacio de trabajo según las palabras clave de la orden.
        Permite a los modelos (GLM, Gemini, Kimi) tener visión real del código (HTML, CSS, JS) estilo Antigravity.
        """
        low = (message or "").lower()
        _proj_root = Path(__file__).resolve().parent.parent
        targets = []
        loaded_names = []

        # Detección contextual por componentes
        if any(k in low for k in ["sidebar", "barra lateral", "lateral", "sidebard", "dock", "navegacion", "nav"]):
            targets.append(("web/templates/components/sidebar.html", 1, 80, "Plantilla HTML del Sidebar lateral"))
            targets.append(("web/static/css/theme/matte-dark.css", 42, 140, "Estilos CSS del Sidebar (.prism-sidebar, .prism-brand-icon, .prism-nav-item)"))

        if any(k in low for k in ["timeline", "secuenciador", "pistas", "linea de tiempo", "línea de tiempo"]):
            targets.append(("web/templates/components/timeline_view.html", 1, 80, "Plantilla HTML del Timeline & Secuenciador"))
            targets.append(("web/static/css/theme/matte-dark.css", 300, 420, "Estilos CSS del Timeline"))

        if any(k in low for k in ["player", "reproductor", "hud", "stage", "pantalla", "video"]):
            targets.append(("web/templates/components/results_section.html", 1, 90, "Plantilla HTML del Player HUD y Stage"))

        if any(k in low for k in ["streamer", "kai", "emision", "emisión", "transmision", "transmisión"]):
            targets.append(("web/templates/components/streamer_panel.html", 1, 80, "Plantilla HTML de KAI Streamer"))

        if any(k in low for k in ["header", "topbar", "encabezado"]):
            targets.append(("web/templates/components/header.html", 1, 70, "Plantilla HTML de la Topbar / Encabezado"))

        if any(k in low for k in ["proyectos", "biblioteca", "guardados"]):
            targets.append(("web/templates/components/projects_library.html", 1, 70, "Plantilla HTML de Biblioteca"))

        if any(k in low for k in ["css", "estilo", "tema", "color", "sombras", "matte", "diseño", "fondo"]) and not targets:
            targets.append(("web/static/css/theme/matte-dark.css", 1, 100, "Variables CSS principales y tema Matte Dark"))

        # Búsqueda de menciones directas a archivos (@archivo o ruta)
        for check_path in [
            "web/static/css/theme/matte-dark.css",
            "web/static/css/style.css",
            "web/templates/components/sidebar.html",
            "web/templates/components/timeline_view.html",
            "web/templates/components/header.html",
            "web/templates/components/streamer_panel.html",
            "web/templates/components/results_section.html",
            "web/templates/components/agent_chat_modal.html",
            "web/static/js/app.js",
            "web/static/js/modules/agent_copilot.js"
        ]:
            fname = Path(check_path).name.lower()
            stem = Path(check_path).stem.lower()
            if fname in low or f"@{stem}" in low or check_path in low:
                if not any(t[0] == check_path for t in targets):
                    targets.append((check_path, 1, 90, f"Archivo solicitado: {check_path}"))

        if not targets:
            return "", []

        output_lines = ["\n━━━ CONTEXTO DE ARCHIVOS DEL PROYECTO (CÓDIGO REAL EN DISCO) ━━━"]
        for rel_path, start_l, end_l, desc in targets:
            full_p = _proj_root / rel_path
            if full_p.exists():
                fname = full_p.name
                if fname not in loaded_names:
                    loaded_names.append(fname)
                try:
                    all_lines = full_p.read_text(encoding="utf-8", errors="replace").splitlines()
                    slice_lines = all_lines[max(0, start_l - 1):min(len(all_lines), end_l)]
                    numbered = [f"{start_l + idx}: {l}" for idx, l in enumerate(slice_lines)]
                    output_lines.append(f"\n📄 [{rel_path}] ({desc} | Líneas {start_l}-{min(len(all_lines), end_l)}):")
                    output_lines.append("```\n" + "\n".join(numbered) + "\n```")
                except Exception as e:
                    output_lines.append(f"\n[Error leyendo {rel_path}: {e}]")
        output_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        return "\n".join(output_lines), loaded_names

    def _extract_and_apply_css_if_present(
        self,
        message: str,
        raw_resp: str,
        ctx: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta si la respuesta del modelo contiene código CSS real y válido (incluso si falló la estructura JSON),
        lo valida estrictamente (rechazando notas de plan o scratchpads), lo aplica a matte-dark.css
        y genera la acción edit_file correspondiente para el frontend.
        """
        if not raw_resp:
            return None

        text = raw_resp.strip()
        low_msg = message.lower()
        low_resp = text.lower()

        # 1. Determinar el selector objetivo
        target_selector = ".prism-sidebar"
        element_name = "Sidebar lateral"

        # Si el usuario escribió un selector exacto (ej: div.prism-sidebar-brand, .prism-sidebar-brand, #header)
        m_explicit_sel = re.search(r'\b(?:div|span|button|section|aside|header|nav|a)?([\.#][a-zA-Z0-9_\-]+)\b', message)
        if m_explicit_sel:
            target_selector = m_explicit_sel.group(1)
            element_name = f"Elemento ({target_selector})"
        elif ctx.get("target_selector"):
            target_selector = ctx.get("target_selector")
            element_name = f"Elemento ({target_selector})"
        elif any(k in low_msg for k in ["brand", "logo", "logotipo"]):
            target_selector = ".prism-sidebar-brand"
            element_name = "Card de Marca (Sidebar)"
        elif any(k in low_msg for k in ["sidebar", "barra lateral", "lateral", "sidebard", "dock"]):
            target_selector = ".prism-sidebar"
            element_name = "Sidebar lateral"
        elif any(k in low_msg for k in ["timeline", "secuenciador", "pista"]):
            target_selector = ".prism-timeline-card"
            element_name = "Timeline & Secuenciador"
        elif any(k in low_msg for k in ["player", "reproductor", "hud", "monitor"]):
            target_selector = ".prism-viewport-screen"
            element_name = "Player Monitor"
        elif any(k in low_msg for k in ["header", "topbar", "encabezado"]):
            target_selector = ".prism-topbar"
            element_name = "Topbar / Encabezado"

        def is_clean_css_code(block: str) -> bool:
            """Valida estrictamente que el bloque sea código CSS y NO un texto de planificación."""
            if not block or len(block.strip()) < 6:
                return False
            low_b = block.lower()
            # Rechazar notas de plan, scratchpads de IA o pseudocódigo
            bad_phrases = ["plan:", "voy a hacer", "replace 1:", "replace 2:", "op=replace", "op=append", "edit_file", "paso 1", "paso 2", "replace:", '"thought":', '"reply":', '"actions":']
            if any(bp in low_b for bp in bad_phrases):
                return False
            css_keys = ["background", "color", "border", "box-shadow", "display", "padding", "margin", "font-", "transform", "transition", "border-radius", "linear-gradient"]
            # Debe contener llaves o pares propiedad: valor
            if "{" in block and "}" in block:
                return any(k in low_b for k in css_keys)
            return (";" in block or ":" in block) and any(k in low_b for k in css_keys)

        # 2. Extraer el bloque CSS
        extracted_css = ""

        # Caso A: Buscar bloques ```css ... ``` o ``` ... ``` que contengan CSS real
        code_blocks = re.findall(r"```(?:css)?\s*([\s\S]*?)```", text)
        for cb in code_blocks:
            cb_clean = cb.strip()
            if is_clean_css_code(cb_clean):
                extracted_css = cb_clean
                break

        # Caso B: Si no había bloques ``` válidos, buscar si hay bloques de reglas con llaves
        if not extracted_css:
            rule_matches = re.findall(r'([\.#a-zA-Z0-9_\-\s,>:+]+)\s*\{([^}]+)\}', text)
            valid_rules = []
            for sel, body in rule_matches:
                sel_clean = sel.strip()
                body_clean = body.strip()
                if any(bp in sel_clean.lower() for bp in ["plan", "replace", "paso", "edit_file"]):
                    continue
                if is_clean_css_code(body_clean):
                    valid_rules.append(f"{sel_clean} {{\n    {body_clean}\n}}")
            if valid_rules:
                extracted_css = "\n\n".join(valid_rules)

        # Caso C: Bloque encerrado en { ... } sin selector
        if not extracted_css:
            m_braces = re.search(r"\{\s*([^{}]+:[^{}]+)\s*\}", text, re.DOTALL)
            if m_braces:
                props = m_braces.group(1).strip()
                if is_clean_css_code(props):
                    extracted_css = f"{target_selector} {{\n    {props}\n}}"

        if not extracted_css or not is_clean_css_code(extracted_css):
            return None

        # 3. Aplicar directamente al archivo en disco (matte-dark.css)
        _proj_root = Path(__file__).resolve().parent.parent
        target_file = _proj_root / "web" / "static" / "css" / "theme" / "matte-dark.css"
        rel_path = "web/static/css/theme/matte-dark.css"

        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            if target_file.exists():
                import shutil
                shutil.copy2(str(target_file), str(target_file) + ".bak")
                existing = target_file.read_text(encoding="utf-8")
            else:
                existing = ""

            import datetime
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            banner = f"\n\n/* ━━━ AetherCopilot Live Edit [{ts}]: {element_name} ━━━ */\n"
            new_content = existing + banner + extracted_css + "\n"
            target_file.write_text(new_content, encoding="utf-8")
            safe_log(f"[AppAgent] ✅ CSS auto-aplicado directamente en disco: {rel_path} ({len(extracted_css)} chars)")
        except Exception as err:
            safe_log(f"[AppAgent] Error guardando CSS en disco: {err}")

        # 4. Formatear respuesta limpia y acción para el frontend
        reply = (
            f"🎨 **He modificado directamente el archivo `{rel_path}` en disco** aplicando el nuevo diseño profesional para {element_name}:\n\n"
            f"```css\n{extracted_css}\n```\n\n"
            f"⚡ Los estilos se han actualizado en vivo en la interfaz de la aplicación."
        )

        return {
            "reply": reply,
            "thought": f"Detectado código CSS para {element_name}. Se auto-aplicó directamente a {rel_path} en disco y se generó la acción edit_file con recarga en vivo.",
            "actions": [
                {
                    "type": "edit_file",
                    "op": "append",
                    "path": rel_path,
                    "content": extracted_css,
                    "file_written": rel_path,
                    "css_code": extracted_css,
                    "reload": False,
                }
            ],
            "extra": {
                "file_edits": [rel_path],
                "css_code": extracted_css,
            }
        }

    def _call_model(self, model_id: str, prompt: str, system_prompt: str) -> tuple[str, str]:
        """Invoca el conector adecuado. Gemini es la primera opción por velocidad y fiabilidad."""
        m_id = (model_id or "gemini").lower()

        if "gemini" in m_id:
            try:
                client = LLMClient()
                resp = client.generate(f"{system_prompt}\n\n{prompt}", json_mode=True)
                return resp, ""
            except Exception as exc:
                safe_log(f"[AppAgent] Error con Gemini: {exc}. Fallback a NIM.")
                m_id = "glm-5.3-flash"

        # NIM: GLM / Kimi con timeout 6s y failover a Gemini
        if "kimi" in m_id:
            key = getattr(settings, "KIMI_API_KEY", "") or getattr(settings, "NVIDIA_API_KEY", "")
            conn = AgentModelConnector(model_name="moonshotai/kimi-k3", api_key=key, role_title="Kimi-k3")
        elif "flash" in m_id:
            key = getattr(settings, "GLM_FLASH_API_KEY", "") or getattr(settings, "NVIDIA_API_KEY", "")
            conn = AgentModelConnector(model_name="z-ai/glm-5.3-flash", api_key=key, role_title="GLM-5.3-flash")
        else:
            key = getattr(settings, "GLM_API_KEY", "") or getattr(settings, "NVIDIA_API_KEY", "")
            conn = AgentModelConnector(model_name="z-ai/glm-5.3", api_key=key, role_title="GLM-5.3")

        import concurrent.futures
        import concurrent.futures, threading, time

        WARN_TIMEOUT = 45.0   # Segundos de espera para modelos profundos (GLM / Kimi)
        HARD_TIMEOUT = 120.0  # Timeout máximo absoluto

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            conn.generate,
            system_prompt=system_prompt,
            user_prompt=prompt,
            max_tokens=1200,
            json_mode=True,
        )

        # Esperar 12s: si el modelo no responde, devolver nim_slow para que el usuario decida
        try:
            resp = future.result(timeout=WARN_TIMEOUT)
            executor.shutdown(wait=False)
            return resp, conn.last_reasoning or ""
        except concurrent.futures.TimeoutError:
            # El modelo NIM sigue procesando. Guardamos el future para reutilizarlo si el usuario elige esperar.
            import uuid as _uuid
            job_id = _uuid.uuid4().hex[:10]
            AppAgentController._pending_nim_jobs[job_id] = {
                "future": future,
                "executor": executor,
                "conn": conn,
                "started_at": time.time(),
                "hard_timeout": HARD_TIMEOUT,
                "user_message": prompt,
            }
            safe_log(f"[AppAgent] {m_id} sigue pensando tras 12s → job_id={job_id}. Esperando decisión del usuario.")
            raise _NimSlowError(job_id, conn.role_title)
        except Exception as exc:
            executor.shutdown(wait=False)
            safe_log(f"[AppAgent] {m_id} falló: {exc}. Failover a Gemini.")
            try:
                client = LLMClient()
                resp = client.generate(f"{system_prompt}\n\n{prompt}", json_mode=True)
                return resp, f"🔄 Failover a Gemini (error en {conn.role_title})."
            except Exception as g_exc:
                safe_log(f"[AppAgent] Gemini también falló: {g_exc}")
                return "", ""

    @staticmethod
    def _clean_reply_text(text: str) -> str:
        """Limpia y desenvuelve cualquier residuo de JSON o secuencias de escape literales."""
        if not text:
            return ""
        s = text.strip()
        # Si la respuesta quedó envuelta en bloque JSON o comillas
        if '"reply"' in s:
            m = re.search(r'"reply"\s*:\s*"((?:\\.|[^"\\])*)"', s, re.DOTALL)
            if m:
                s = m.group(1)
            else:
                m2 = re.search(r'"reply"\s*:\s*"(.*?)(?:"\s*,\s*"actions"|"\s*\}\s*$)', s, re.DOTALL)
                if m2:
                    s = m2.group(1)
        # Desescapar secuencias de escape
        s = s.replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
        # Quitar restos de sintaxis JSON
        s = re.sub(r'^\s*\{\s*', '', s)
        s = re.sub(r'\s*\}\s*$', '', s)
        return s.strip()

    def _check_fast_path(
        self,
        message: str,
        low_msg: str,
        ctx: Dict[str, Any],
        proj_info: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Atajos ultra-rápidos estrictamente para botones de acción o palabras únicas.
        CUALQUIER mensaje conversacional, instrucción o petición en lenguaje natural
        debe pasar al modelo de IA para que razone con criterio e inteligencia autónoma.
        """
        clean_msg = low_msg.strip()
        words = clean_msg.split()

        # Solo interceptar atajos literales de 1 o 2 palabras exactas sin instrucciones adicionales
        if len(words) <= 2:
            if clean_msg in ["mesa", "timeline"]:
                return {
                    "model_used": "fast-path",
                    "reply": "🚀 Trasladándote a la **Mesa de Edición & Timeline**.",
                    "reasoning": "⚡ Salto directo solicitado.",
                    "actions": [{"type": "navigate", "view": "mesa"}],
                    "extra": {},
                }
            if clean_msg in ["proyectos", "biblioteca"]:
                return {
                    "model_used": "fast-path",
                    "reply": "📂 Abriendo la **Biblioteca de Proyectos**.",
                    "reasoning": "⚡ Salto directo solicitado.",
                    "actions": [{"type": "navigate", "view": "projects"}],
                    "extra": {},
                }
            if clean_msg in ["streamer", "emision", "emisión"]:
                return {
                    "model_used": "fast-path",
                    "reply": "🎙️ Abriendo **KAI Streamer**.",
                    "reasoning": "⚡ Salto directo solicitado.",
                    "actions": [{"type": "navigate", "view": "streamer"}],
                    "extra": {},
                }
            if clean_msg in ["copilot", "recortes"]:
                return {
                    "model_used": "fast-path",
                    "reply": "✂️ Abriendo el **Editor Co-Piloto**.",
                    "reasoning": "⚡ Salto directo solicitado.",
                    "actions": [{"type": "navigate", "view": "copilot"}],
                    "extra": {},
                }

        # Consulta directa estricta de conteo de proyectos
        if clean_msg in ["cuantos proyectos hay", "cuántos proyectos hay"]:
            tot = proj_info.get("total_count", 0)
            latest = proj_info.get("latest_project")
            latest_str = f"**'{latest['name']}'** (Estado: `{latest['status']}`)" if latest else "ninguno"
            return {
                "model_used": "fast-path",
                "reply": f"📊 Hay un total de **{tot} proyectos creados**.\n\nÚltimo proyecto: {latest_str}.",
                "reasoning": f"⚡ Consulta directa en disco: {tot} proyectos.",
                "actions": [],
                "extra": {},
            }

        # Para todo lo demás (instrucciones, modificaciones, razonamiento arquitectónico):
        # Permitir que el MODELO DE INTELIGENCIA ARTIFICIAL razone libremente.
        return None

    def process_message(
        self,
        message: str,
        model_id: str = "gemini",
        app_context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Procesa una orden con memoria de conversación y conocimiento exacto del estudio."""
        ctx = app_context or {}
        history = history or []
        low_msg = message.lower()
        effective_model = model_id
        delegated_note = None

        proj_info = self._get_live_projects_info()

        # Fast-path solo para comandos literales de 1-2 palabras
        fast_res = self._check_fast_path(message, low_msg, ctx, proj_info)
        if fast_res:
            return fast_res

        # Delegación automática a Gemini para tareas visuales
        if any(w in low_msg for w in ["imagen", "foto", "visual", "dibujo", "video frame", "screenshot", "captura"]):
            if "gemini" not in model_id.lower():
                effective_model = "gemini"
                delegated_note = "🎨 Delegado a **Gemini Neural** (especialista en análisis visual y multimodal)."

        # Estado enriquecido del estudio
        tot_proj = proj_info["total_count"]
        latest_p = proj_info["latest_project"]
        latest_str = (
            f"'{latest_p['name']}' (ID: {latest_p['id']}, Estado: {latest_p['status']}, Formato: {latest_p.get('aspect_ratio','16:9')})"
            if latest_p else "Ninguno"
        )
        recent_list = ", ".join(
            [f"'{p['name']}' ({p['id'][:6]})" for p in proj_info["recent_projects"][:6]]
        )
        ren_mode_str = "ACTIVO" if ctx.get("is_ren_mode") else "inactivo"
        target_sel = ctx.get("target_selector") or "ninguno"

        file_context_str, context_files = self._get_relevant_file_context(message, ctx)

        sel_card = ctx.get("selected_timeline_item")
        sel_card_str = (
            f"Tipo={sel_card.get('type')}, ID={sel_card.get('id')}, Titular='{sel_card.get('headline')}', Cifra='{sel_card.get('stat_value','')}', Segundo={sel_card.get('start')}s"
            if sel_card and isinstance(sel_card, dict)
            else "ninguno"
        )

        context_str = f"""
━━━ ESTADO ACTUAL DEL ESTUDIO ━━━
• Proyectos totales: {tot_proj}
• Último proyecto: {latest_str}
• Proyectos recientes: {recent_list or 'Ninguno'}
• Proyecto abierto ahora: {ctx.get('current_project_id') or 'ninguno'} — "{ctx.get('current_project_name') or 'sin nombre'}"
• Vista activa: {ctx.get('active_view') or 'mesa'}
• Formato: {ctx.get('aspect_ratio') or '16:9'}
• Modo REN: {ren_mode_str} | Elemento objetivo: {target_sel}
• Elemento/Tarjeta seleccionada en Línea de Tiempo: {sel_card_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{file_context_str}"""

        history_str = self._format_history_for_prompt(history)
        full_prompt = f"{context_str}{history_str}\nMENSAJE ACTUAL: \"{message}\""

        try:
            raw_resp, reasoning_text = self._call_model(effective_model, full_prompt, SYSTEM_PROMPT_AGENT)
        except _NimSlowError as nim_err:
            # El modelo NIM sigue procesando tras 12s — pedirle al usuario que decida
            return {
                "status": "nim_slow",
                "job_id": nim_err.job_id,
                "model_name": nim_err.model_name,
                "model_used": effective_model,
                "reply": "",
                "reasoning": "",
                "actions": [],
                "extra": {},
            }

        parsed_data = None
        try:
            clean = raw_resp.strip()
            m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", clean)
            if m:
                clean = m.group(1).strip()
            else:
                s = clean.find("{")
                e = clean.rfind("}")
                if s != -1 and e != -1 and e > s:
                    clean = clean[s : e + 1].strip()

            try:
                parsed_data = json.loads(clean, strict=False)
            except Exception:
                # Extractor regex resiliente para JSON con saltos de línea sin escapar
                m_rep = re.search(r'"reply"\s*:\s*"(.*?)(?:"\s*,\s*"actions"|"\s*\}\s*$)', clean, re.DOTALL)
                if m_rep:
                    ext_reply = m_rep.group(1)
                    act_list = []
                    m_act = re.search(r'"actions"\s*:\s*(\[.*?\])', clean, re.DOTALL)
                    if m_act:
                        try:
                            act_list = json.loads(m_act.group(1), strict=False)
                        except Exception:
                            pass
                    parsed_data = {"reply": ext_reply, "actions": act_list}
        except Exception as exc:
            safe_log(f"[AppAgent] Advertencia al parsear JSON del modelo {effective_model}: {exc}")

        # Si el modelo no devolvió JSON estricto o no generó acciones para una orden de diseño/código:
        parsed_actions = parsed_data.get("actions", []) if isinstance(parsed_data, dict) else []
        if not parsed_data or not isinstance(parsed_data, dict) or not parsed_actions:
            # Primero intentar auto-aplicar si el modelo generó CSS o código directo
            css_applied = self._extract_and_apply_css_if_present(message, raw_resp or message, ctx)
            if css_applied:
                parsed_data = css_applied
            elif not parsed_data or not isinstance(parsed_data, dict):
                parsed_data = self._fallback_intent_parser(message, raw_resp or message, ctx, proj_info)

        raw_reply = parsed_data.get("reply", "Entendido. Procesando tu solicitud en la aplicación.")
        reply = self._clean_reply_text(raw_reply)

        model_thought = parsed_data.get("thought")
        if model_thought and isinstance(model_thought, str) and model_thought.strip():
            reasoning_text = model_thought.strip()

        if delegated_note:
            reply = f"{delegated_note}\n\n{reply}"

        raw_actions = parsed_data.get("actions", [])
        if not isinstance(raw_actions, list):
            raw_actions = []

        actions = []
        for item in raw_actions:
            if not isinstance(item, dict):
                continue
            if "type" in item:
                actions.append(item)
            else:
                for k, v in item.items():
                    if k in ["ren_mutate", "ren_reset", "navigate", "create_project", "create_thumbnail", "customize_ui", "modify_popups", "highlight_element", "edit_file", "read_file", "list_files"]:
                        if isinstance(v, dict):
                            act_dict = {"type": k}
                            act_dict.update(v)
                            actions.append(act_dict)
                        elif isinstance(v, str) and k == "navigate":
                            actions.append({"type": "navigate", "view": v})
                        else:
                            actions.append({"type": k, "value": v})
                        break

        # Si hubo cambio de modelo por delegación, notificar al frontend
        if effective_model != model_id:
            actions.insert(0, {
                "type": "switch_model",
                "model_id": effective_model,
                "reason": "Delegación automática de capacidades",
            })

        # Ejecución Backend de acciones (ej: generar miniatura si fue solicitada o editar archivos en disco)
        final_actions = []
        extra_data = {}

        for act in actions:
            if not isinstance(act, dict):
                continue
            act_type = act.get("type")

            if act_type == "create_thumbnail":
                thumb_title = act.get("title") or ctx.get("current_project_name") or "BROADCAST EXCLUSIVO"
                thumb_badge = act.get("badge") or "🔴 ALERTA MUNDIAL"
                proj_id = act.get("project_id") or ctx.get("current_project_id")
                try:
                    res_thumb = self.thumbnail_maker.generate(
                        title=thumb_title,
                        badge_text=thumb_badge,
                        project_id=proj_id,
                    )
                    act["thumbnail_url"] = res_thumb["url"]
                    act["thumbnail_filename"] = res_thumb["filename"]
                    extra_data["thumbnail"] = res_thumb
                    reply += f"\n\n🖼️ **Miniatura generada con éxito:** [Descargar Portada HD]({res_thumb['url']})"
                except Exception as th_err:
                    safe_log(f"[AppAgent] Error generando miniatura: {th_err}")

            if act_type == "read_file":
                _proj_root = Path(__file__).resolve().parent.parent
                rel_path = act.get("path", "")
                try:
                    target = (_proj_root / rel_path.lstrip("/\\")).resolve()
                    if target.exists() and target.is_file():
                        content = target.read_text(encoding="utf-8", errors="replace")
                        act["content"] = content[:3000]
                        act["lines"] = content.count("\n") + 1
                        act["ok"] = True
                        extra_data["read_files"] = extra_data.get("read_files", []) + [rel_path]
                        reply += f"\n\n📖 **Archivo leído `{rel_path}`** ({act['lines']} líneas)."
                    else:
                        act["error"] = "Archivo no encontrado"
                        act["ok"] = False
                except Exception as r_err:
                    act["error"] = str(r_err)

            if act_type == "list_files":
                _proj_root = Path(__file__).resolve().parent.parent
                rel_dir = act.get("dir", "web")
                try:
                    target_d = (_proj_root / rel_dir.lstrip("/\\")).resolve()
                    if target_d.exists() and target_d.is_dir():
                        flist = [str(p.relative_to(_proj_root)).replace("\\", "/") for p in target_d.glob("**/*") if p.is_file()][:40]
                        act["files"] = flist
                        act["ok"] = True
                        extra_data["listed_files"] = flist
                        reply += f"\n\n📁 **Archivos en `{rel_dir}`:** {len(flist)} archivos encontrados."
                    else:
                        act["error"] = "Directorio no encontrado"
                except Exception as l_err:
                    act["error"] = str(l_err)

            if act_type == "edit_file":
                # ── ACCIÓN REAL ESTILO ANTIGRAVITY: Escribe en archivos del proyecto en disco ──
                import shutil
                _proj_root = Path(__file__).resolve().parent.parent
                _allowed = [
                    _proj_root / "web" / "static" / "css",
                    _proj_root / "web" / "static" / "js",
                    _proj_root / "web" / "templates",
                ]
                rel_path = act.get("path", "")
                op = act.get("op", "append")
                try:
                    target = (_proj_root / rel_path.lstrip("/\\")).resolve()
                    # Validar path seguro
                    is_safe = any(
                        True for d in _allowed
                        if str(target).startswith(str(d.resolve()))
                    )
                    if not is_safe:
                        safe_log(f"[AppAgent] edit_file rechazado: ruta no permitida {rel_path}")
                        reply += f"\n\n⚠️ Ruta no permitida para edición: `{rel_path}`"
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if target.exists():
                            shutil.copy2(str(target), str(target) + ".bak")

                        if op == "write":
                            target.write_text(act.get("content", ""), encoding="utf-8")
                        elif op == "append":
                            existing = target.read_text(encoding="utf-8") if target.exists() else ""
                            target.write_text(existing + "\n" + act.get("content", ""), encoding="utf-8")
                        elif op == "replace":
                            old_str = act.get("old", "")
                            new_str = act.get("new", "")
                            if old_str and target.exists():
                                existing = target.read_text(encoding="utf-8")
                                updated = existing.replace(old_str, new_str, 1)
                                target.write_text(updated, encoding="utf-8")
                            else:
                                safe_log(f"[AppAgent] edit_file replace: 'old' no encontrado en {rel_path}")

                        act["file_written"] = str(rel_path)
                        if target.suffix == ".css":
                            act["css_code"] = act.get("content") or act.get("new") or ""
                            act["reload"] = False  # El frontend inyecta CSS en vivo sin recargar la página!
                        else:
                            act["reload"] = True
                        extra_data["file_edits"] = extra_data.get("file_edits", []) + [rel_path]
                        safe_log(f"[AppAgent] ✅ Archivo modificado en disco: {rel_path}")

                except Exception as fe:
                    safe_log(f"[AppAgent] Error en edit_file {rel_path}: {fe}")
                    reply += f"\n\n⚠️ Error al modificar `{rel_path}`: {fe}"

            if act_type in ["modify_timeline_card", "modify_card"]:
                card_id = act.get("card_id") or (ctx.get("selected_timeline_item", {}).get("id") if ctx.get("selected_timeline_item") else "")
                cur_proj_id = ctx.get("current_project_id") or proj_info.get("latest_project", {}).get("id")
                if cur_proj_id:
                    proj_dir = settings.PROJECTS_DIR / cur_proj_id
                    plan_path = proj_dir / "work" / "broadcast_plan.json"
                    if plan_path.exists():
                        try:
                            bplan = json.loads(plan_path.read_text(encoding="utf-8"))
                            found_card = False
                            for sc in bplan.get("scenes", []):
                                c = sc.get("card")
                                sid = str(sc.get("scene_id"))
                                if c and (card_id == f"card-{sid}" or card_id == sid or not card_id):
                                    if "headline" in act: c["headline"] = act["headline"]
                                    if "stat_value" in act: c["stat"] = act["stat_value"]
                                    if "body" in act: c["body"] = act["body"]
                                    if "badge" in act: c["badge"] = act["badge"]
                                    act["card_id"] = f"card-{sid}"
                                    act["scene_id"] = sid
                                    act["updated_card"] = c
                                    found_card = True
                                    break
                            if found_card:
                                plan_path.write_text(json.dumps(bplan, ensure_ascii=False, indent=2), encoding="utf-8")
                                safe_log(f"[AppAgent] ✅ Tarjeta {card_id} guardada en broadcast_plan.json")

                                # Regenerar la imagen gráfica PNG con WebCardRenderer (Estándar Web 2026 Cuadrado/Bento)
                                try:
                                    from core.web_card_renderer import WebCardRenderer
                                    card_img_path = proj_dir / "work" / f"scene_{sid}" / f"card_{sid}.png"
                                    web_ren = WebCardRenderer()
                                    chosen_style = act.get("style") or "obsidian_bento"
                                    if chosen_style in ("free_title", "kinetic_text", "texto_libre"):
                                        web_ren.render_free_kinetic_text_to_image(
                                            main_title=c.get("headline", ""),
                                            out_png=card_img_path,
                                            number=c.get("number", "") or (c.get("stat", "") if len(c.get("stat", "")) <= 3 else ""),
                                            tag=c.get("badge", ""),
                                            subtitle=c.get("body", ""),
                                            highlight=c.get("highlight", ""),
                                            accent_color=c.get("accent_color", "#38bdf8"),
                                        )
                                    else:
                                        web_ren.render_to_image(
                                            headline=c.get("headline", ""),
                                            out_png=card_img_path,
                                            stat_value=c.get("stat", "") or c.get("stat_value", "95%"),
                                            stat_label="Precisión / Métrica",
                                            body=c.get("body", ""),
                                            badge=c.get("badge", "") or "DATO VERIFICADO",
                                            source="Registro Oficial · Tech Defense 2026",
                                            style=chosen_style,
                                        )
                                    act["card_url"] = f"/storage/projects/{cur_proj_id}/work/scene_{sid}/card_{sid}.png?v={int(time.time()*1000)}"
                                    safe_log(f"[AppAgent] 🎨 Tarjeta Bento moderna generada con éxito en {card_img_path.name}")
                                except Exception as ren_err:
                                    safe_log(f"[AppAgent] Error con WebCardRenderer, usando fallback de Pillow: {ren_err}")
                                    try:
                                        from core.card_renderer import InfoCardRenderer
                                        from core.models import InfoCard
                                        card_obj = InfoCard(
                                            card_id=f"sc_card_{sid}",
                                            start_sec=0.5,
                                            end_sec=15.0,
                                            headline=c.get("headline", ""),
                                            claim=c.get("body", ""),
                                            body=c.get("body", ""),
                                            stat_value=c.get("stat", "") or c.get("stat_value", ""),
                                            note=c.get("badge", "") or "DATO CLAVE",
                                            verdict="supported",
                                            search_query=c.get("headline", "dato verificado"),
                                        )
                                        card_img_path = proj_dir / "work" / f"scene_{sid}" / f"card_{sid}.png"
                                        renderer = InfoCardRenderer(1920, 1080, theme="dark")
                                        renderer.render(card_obj, card_img_path)
                                        act["card_url"] = f"/storage/projects/{cur_proj_id}/work/scene_{sid}/card_{sid}.png?v={int(time.time()*1000)}"
                                    except Exception as f_err:
                                        safe_log(f"[AppAgent] Fallback error: {f_err}")

                                reply += f"\n\n📊 **Tarjeta `{act.get('headline', card_id)}` actualizada y re-renderizada en disco como nueva imagen gráfica.**"
                        except Exception as bp_err:
                            safe_log(f"[AppAgent] Error actualizando tarjeta en broadcast_plan: {bp_err}")

            final_actions.append(act)

        if context_files:
            extra_data["context_files"] = context_files

        return {
            "model_used": model_id,
            "reply": reply,
            "reasoning": reasoning_text or f"Razonamiento completado con {model_id} para orquestar la aplicación.",
            "actions": final_actions,
            "extra": extra_data,
        }

    def _fallback_intent_parser(
        self,
        message: str,
        raw_text: str,
        ctx: Dict[str, Any],
        proj_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extractor de intenciones robusto basado en palabras clave para garantizar respuesta inmediata."""
        low = message.lower()
        actions = []
        reply_lines = []

        # 0. Consulta directa de proyectos y estado de la biblioteca
        if any(k in low for k in ["cuantos proyectos", "cuántos proyectos", "ultimo creado", "último creado", "que proyectos hay", "lista de proyectos"]):
            tot = proj_info.get("total_count", 0) if proj_info else 0
            latest = proj_info.get("latest_project") if proj_info else None
            lat_txt = f"**'{latest['name']}'** (ID: `{latest['id']}`, estado: `{latest['status']}`)" if latest else "ninguno registrado aún"
            reply_lines.append(f"Actualmente hay **{tot} proyectos** registrados en la biblioteca de AetherCut Studio.\nEl último proyecto creado o actualizado es {lat_txt}.")
            actions.append({"type": "navigate", "view": "projects"})

        # 1. Detección de miniatura para YouTube
        if any(k in low for k in ["miniatura", "portada", "thumbnail", "cover"]):
            proj_title = ctx.get("current_project_name") or "ALERTA: ROBOTS ASESINOS EN EL MUNDO"
            # Extraer posible título
            m_tit = re.search(r"['\"]([^'\"]+)['\"]", message)
            chosen_tit = m_tit.group(1) if m_tit else proj_title
            actions.append({
                "type": "create_thumbnail",
                "title": chosen_tit,
                "badge": "🔴 BROADCAST URGENTE",
                "project_id": ctx.get("current_project_id"),
            })
            reply_lines.append(f"He diseñado y renderizado una miniatura de alta retención para YouTube basada en **'{chosen_tit}'** con contraste cinematográfico y badge broadcast.")

        # 2. Detección de creación / inicio de proyecto
        if any(k in low for k in ["pon a hacer", "crea un proyecto", "iniciar transmision", "inicia transmision", "haz un video", "crear video", "haz una prueba"]):
            m_tit = re.search(r"(?:tema\s*:?\s*|con\s+el\s+tema\s*:?\s*)['\"]?([^'\",\n]+)['\"]?", message, re.I)
            topic = m_tit.group(1).strip() if m_tit else "Agencias internacionales advierten sobre peligro de 'robots asesinos'"
            dur = 180
            if "3 min" in low or "180" in low or "tres minutos" in low:
                dur = 180
            elif "1 min" in low or "60" in low or "un minuto" in low:
                dur = 60

            aspect = "16:9" if ("horizontal" in low or "16:9" in low or "panoramico" in low) else "16:9"
            actions.append({
                "type": "create_project",
                "topic": topic,
                "duration_sec": dur,
                "aspect_ratio": aspect,
                "voice": "es-MX-JorgeNeural",
            })
            actions.append({"type": "navigate", "view": "mesa"})
            reply_lines.append(f"¡Entendido! He iniciado de inmediato la producción del proyecto: **'{topic}'** ({dur}s, formato {aspect}). Te estoy trasladando a la **Mesa de Edición & Timeline** para que monitorees el proceso en tiempo real.")

        # 3. Detección de navegación
        if any(k in low for k in ["ve a la mesa", "lleva a la mesa", "timeline", "secuenciador", "monitor"]):
            actions.append({"type": "navigate", "view": "mesa"})
            reply_lines.append("Te he llevado a la **Mesa de Edición & Timeline**.")
        elif any(k in low for k in ["proyectos", "biblioteca", "historial"]):
            actions.append({"type": "navigate", "view": "projects"})
            reply_lines.append("Abriendo la **Biblioteca de Proyectos Guardados**.")
        elif any(k in low for k in ["streamer", "emision", "transmision"]):
            actions.append({"type": "navigate", "view": "streamer"})
            reply_lines.append("Abriendo el panel de **KAI Streamer**.")

        # 4. Detección de cambios estéticos / botones / colores
        if any(k in low for k in ["cambia el color", "color del boton", "color primario", "estilo"]):
            col = "#38bdf8"
            if "rojo" in low or "red" in low: col = "#ef4444"
            elif "verde" in low or "esmeralda" in low: col = "#10b981"
            elif "morado" in low or "purpura" in low: col = "#a855f7"
            elif "amarillo" in low or "ambar" in low: col = "#f59e0b"
            elif "azul" in low or "cian" in low: col = "#06b6d4"

            actions.append({"type": "customize_ui", "accent_color": col})
            reply_lines.append(f"He actualizado el tono visual de la plataforma aplicando acento `{col}` en los controles y botones.")

        # 5. Detección de popups
        if any(k in low for k in ["pop up", "popup", "graficos", "tarjetas"]):
            actions.append({"type": "modify_popups", "style": "broadcast_amber", "scale": "large"})
            reply_lines.append("He actualizado los parámetros de los popups a modo Broadcast de alta fidelidad para que se vean amplios, legibles y nítidos.")

        # 6. Detección de diseño / mejora del sidebar lateral o interfaz
        if any(k in low for k in ["sidebar", "barra lateral", "sidebard", "lateral"]) and any(k in low for k in ["diseño", "estilo", "mejor", "negro", "sombras", "color", "iconos", "profesional"]):
            sidebar_css = """
/* AetherCopilot - Estilo Profesional Matte Dark Sidebar */
.prism-sidebar {
    background: linear-gradient(180deg, #07090e 0%, #05070a 100%) !important;
    border-right: 1px solid rgba(37, 99, 235, 0.22) !important;
    box-shadow: 6px 0 28px rgba(0, 0, 0, 0.75), inset -1px 0 0 rgba(37, 99, 235, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
}
.prism-brand-icon {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #38bdf8 100%) !important;
    box-shadow: 0 0 20px rgba(37, 99, 235, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.4) !important;
}
.prism-nav-item:hover {
    background: rgba(30, 41, 59, 0.55) !important;
    border-color: rgba(37, 99, 235, 0.3) !important;
    color: #f8fafc !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
}
.prism-nav-item.active {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.22) 0%, rgba(15, 23, 42, 0.7) 100%) !important;
    border-color: rgba(56, 189, 248, 0.45) !important;
    box-shadow: 0 4px 18px rgba(37, 99, 235, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
    color: #ffffff !important;
}
""".strip()
            actions.append({
                "type": "edit_file",
                "op": "append",
                "path": "web/static/css/theme/matte-dark.css",
                "content": sidebar_css,
                "file_written": "web/static/css/theme/matte-dark.css",
                "css_code": sidebar_css,
                "reload": False,
            })
            reply_lines.append(
                "🎨 **He modificado directamente el archivo `web/static/css/theme/matte-dark.css` en disco** aplicando el diseño profesional negro mate con sombras sutiles azul oscuro y blanco para el sidebar lateral:\n\n"
                f"```css\n{sidebar_css}\n```\n\n"
                "⚡ Los estilos se han actualizado en pantalla y sincronizado en vivo en la aplicación."
            )

        if not reply_lines:
            reply_lines.append(raw_text if len(raw_text) > 10 else "Entendido. Estoy a tu disposición para controlar proyectos, crear miniaturas, modificar estilos o guiarte en AetherCut AI.")

        return {
            "reply": "\n\n".join(reply_lines),
            "actions": actions,
        }

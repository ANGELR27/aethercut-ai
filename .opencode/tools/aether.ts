import { tool } from "@opencode-ai/plugin"

// Herramientas propias de AetherCut para el agente (OpenCode).
// Las acciones de interfaz se encolan en el servidor y se ejecutan en el navegador
// al terminar el turno; las de lectura devuelven datos reales de la app.

const BASE = process.env.AETHERCUT_URL ?? "http://127.0.0.1:8000"

async function enqueue(sessionID: string, action: Record<string, unknown>) {
  const r = await fetch(`${BASE}/api/oc/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionID, action }),
  })
  if (!r.ok) return `Error ${r.status}: ${await r.text()}`
  return "Acción encolada: se ejecutará en la interfaz de AetherCut al terminar tu respuesta."
}

export const create_video = tool({
  description:
    "Crea un video nuevo en AetherCut Studio a partir de un tema (investiga datos reales, guion, voz y B-Roll).",
  args: {
    topic: tool.schema.string().describe("Tema del video"),
    duration_sec: tool.schema.number().optional().describe("Duración en segundos (default 180)"),
    aspect_ratio: tool.schema.enum(["16:9", "9:16"]).optional(),
  },
  async execute(args, ctx) {
    return enqueue(ctx.sessionID, {
      type: "create_project",
      topic: args.topic,
      duration_sec: args.duration_sec ?? 180,
      aspect_ratio: args.aspect_ratio ?? "16:9",
    })
  },
})

export const create_thumbnail = tool({
  description: "Genera una miniatura de YouTube con título e insignia.",
  args: {
    title: tool.schema.string(),
    badge: tool.schema.string().optional().describe("Ej: 🔴 URGENTE"),
    project_id: tool.schema.string().optional(),
  },
  async execute(args, ctx) {
    return enqueue(ctx.sessionID, { type: "create_thumbnail", ...args })
  },
})

export const navigate_app = tool({
  description: "Cambia de vista en la app.",
  args: {
    view: tool.schema.enum(["studio", "mesa", "projects", "streamer", "copilot", "multiagent"]),
    project_id: tool.schema.string().optional(),
  },
  async execute(args, ctx) {
    return enqueue(ctx.sessionID, { type: "navigate", ...args })
  },
})

export const open_project = tool({
  description: "Abre un proyecto existente en el estudio.",
  args: { project_id: tool.schema.string() },
  async execute(args, ctx) {
    return enqueue(ctx.sessionID, { type: "open_project", project_id: args.project_id })
  },
})

export const notify_user = tool({
  description: "Muestra una notificación flotante al usuario en la app.",
  args: {
    message: tool.schema.string(),
    level: tool.schema.enum(["success", "info", "warning", "error"]).optional(),
  },
  async execute(args, ctx) {
    return enqueue(ctx.sessionID, { type: "show_notification", message: args.message, level: args.level ?? "info" })
  },
})

export const ui_action = tool({
  description:
    "Acción de interfaz genérica del frontend. type puede ser: customize_ui {accent_color}, " +
    "modify_popups {style, scale}, highlight_element {selector,color}, set_playback {action,time}, " +
    "modify_timeline_card {card_id,headline,stat_value,body,style}, ren_mutate {selector,operation,styles}, ren_reset.",
  args: {
    type: tool.schema.string(),
    params: tool.schema.record(tool.schema.string(), tool.schema.any()).optional(),
  },
  async execute(args, ctx) {
    return enqueue(ctx.sessionID, { type: args.type, ...(args.params ?? {}) })
  },
})

export const list_projects = tool({
  description: "Lista los proyectos de video existentes (id, nombre, estado).",
  args: {},
  async execute() {
    const r = await fetch(`${BASE}/api/projects`)
    if (!r.ok) return `Error ${r.status}`
    return JSON.stringify(await r.json()).slice(0, 8000)
  },
})

export const app_status = tool({
  description: "Estado del servidor: tareas en curso (renders, investigaciones, etc.).",
  args: {},
  async execute() {
    const r = await fetch(`${BASE}/api/oc/status`)
    if (!r.ok) return `Error ${r.status}`
    return JSON.stringify(await r.json()).slice(0, 8000)
  },
})

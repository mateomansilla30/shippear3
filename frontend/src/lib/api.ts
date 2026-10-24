// Contrato con el back (FastAPI en el VPS). Cada persona tiene su propia memoria.
//
//   GET  /personas                  → Persona[]
//   POST /personas      {nombre}    → Persona
//   GET  /memoria/{persona_id}      → Memoria
//   PUT  /memoria/{persona_id}      {persona, contactos, vocabulario, correcciones} → Memoria
//   POST /turno         form-data: audio, persona_id → Turno (el back lo guarda en el historial)
//   POST /validar       {persona_id, turno_id, texto_final} → Memoria
//        Si texto_final ≠ turno.texto, el back guarda la corrección {original: turno.texto → texto_final}.
//
// Sin NEXT_PUBLIC_API_URL todo funciona contra localStorage, para poder probar la interfaz.

export type Persona = { id: string; nombre: string; notas?: string }
export type Contacto = { nombre: string; relacion: string; telefono?: string }
export type Correccion = { original: string; texto: string; fecha: string }
export type Turno = {
  id: string
  texto: string // lo que el sistema entendió
  audio_url?: string // voz del asistente (Gemini TTS), si el back la devuelve
  fecha: string
  estado: "pendiente" | "validado" | "corregido"
  texto_final?: string
}
export type Memoria = {
  persona: Persona
  contactos: Contacto[]
  vocabulario: string[]
  correcciones: Correccion[]
  historial: Turno[]
}
export type Editable = Pick<Memoria, "persona" | "contactos" | "vocabulario" | "correcciones">

const API_URL = process.env.NEXT_PUBLIC_API_URL
export const HAY_BACK = !!API_URL

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_URL}${ruta}`, init)
  if (!r.ok) throw new Error(`El servidor respondió ${r.status}`)
  return r.json()
}
const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
})

export async function listarPersonas(): Promise<Persona[]> {
  if (!API_URL) return local.personas()
  return pedir("/personas")
}

export async function crearPersona(nombre: string): Promise<Persona> {
  if (!API_URL) return local.crearPersona(nombre)
  return pedir("/personas", json("POST", { nombre }))
}

export async function obtenerMemoria(personaId: string): Promise<Memoria> {
  if (!API_URL) return local.memoria(personaId)
  return pedir(`/memoria/${personaId}`)
}

export async function guardarMemoria(personaId: string, datos: Editable): Promise<Memoria> {
  if (!API_URL) return local.guardar(personaId, datos)
  return pedir(`/memoria/${personaId}`, json("PUT", datos))
}

export async function enviarAudio(personaId: string, audio: Blob, nombre = "audio.webm", pista?: Pista): Promise<Turno> {
  if (!API_URL) return local.turno(personaId, pista)
  const datos = new FormData()
  datos.append("audio", audio, nombre)
  datos.append("persona_id", personaId)
  return pedir("/turno", { method: "POST", body: datos })
}

export async function validar(personaId: string, turnoId: string, textoFinal: string): Promise<Memoria> {
  if (!API_URL) return local.validar(personaId, turnoId, textoFinal)
  return pedir("/validar", json("POST", { persona_id: personaId, turno_id: turnoId, texto_final: textoFinal }))
}

// Solo para el modo sin back: qué texto devolvería el sistema.
export type Pista = { texto: string }

// ponytail: back falso en localStorage. El aprendizaje acá es una coincidencia exacta con una
// corrección validada; el back real busca las correcciones parecidas y se las pasa al LLM.
const local = {
  leer<T>(clave: string, defecto: T): T {
    try {
      const v = localStorage.getItem(`vozclara:${clave}`)
      return v ? JSON.parse(v) : defecto
    } catch {
      return defecto
    }
  },
  escribir(clave: string, valor: unknown) {
    try {
      localStorage.setItem(`vozclara:${clave}`, JSON.stringify(valor))
    } catch {}
  },
  personas(): Persona[] {
    const p = local.leer<Persona[]>("personas", [])
    if (p.length) return p
    const demo = [{ id: "demo", nombre: "Marta", notas: "Tiene ELA. Habla despacio y hace pausas largas." }]
    local.escribir("personas", demo)
    local.escribir("memoria:demo", {
      persona: demo[0],
      contactos: [
        { nombre: "María", relacion: "hija" },
        { nombre: "Juan", relacion: "amigo" },
      ],
      vocabulario: ["Riluzol", "kinesiólogo", "Háblalo"],
      correcciones: [],
      historial: [],
    })
    return demo
  },
  crearPersona(nombre: string): Persona {
    const persona = { id: crypto.randomUUID(), nombre }
    local.escribir("personas", [...local.personas(), persona])
    return persona
  },
  memoria(id: string): Memoria {
    const persona = local.personas().find((p) => p.id === id) ?? { id, nombre: "Sin nombre" }
    return local.leer<Memoria>(`memoria:${id}`, {
      persona,
      contactos: [],
      vocabulario: [],
      correcciones: [],
      historial: [],
    })
  },
  guardar(id: string, datos: Editable): Memoria {
    const m = { ...local.memoria(id), ...datos }
    local.escribir(`memoria:${id}`, m)
    local.escribir(
      "personas",
      local.personas().map((p) => (p.id === id ? datos.persona : p)),
    )
    return m
  },
  async turno(id: string, pista: Pista = { texto: "Quiero hablar con maia." }): Promise<Turno> {
    await new Promise((r) => setTimeout(r, 1200))
    const m = local.memoria(id)
    const aprendida = m.correcciones.find((c) => c.original === pista.texto)
    const turno: Turno = {
      id: crypto.randomUUID(),
      texto: aprendida?.texto ?? pista.texto,
      fecha: new Date().toISOString(),
      estado: "pendiente",
    }
    local.escribir(`memoria:${id}`, { ...m, historial: [turno, ...m.historial].slice(0, 50) })
    return turno
  },
  validar(id: string, turnoId: string, textoFinal: string): Memoria {
    const m = local.memoria(id)
    const t = m.historial.find((h) => h.id === turnoId)
    if (!t) return m
    const corregido = textoFinal.trim() !== t.texto.trim()
    const historial = m.historial.map((h) =>
      h.id === turnoId ? { ...h, estado: corregido ? "corregido" : "validado", texto_final: textoFinal } as Turno : h,
    )
    const correcciones = corregido
      ? [{ original: t.texto, texto: textoFinal, fecha: new Date().toISOString() },
         ...m.correcciones.filter((c) => c.original !== t.texto)]
      : m.correcciones
    const nueva = { ...m, historial, correcciones }
    local.escribir(`memoria:${id}`, nueva)
    return nueva
  },
}

export type Turno = {
  crudo: string // lo que escuchó Whisper, sin corregir
  texto: string // lo que el sistema entendió
  audio_url?: string // voz del asistente (Gemini TTS), si el back la devuelve
}

const API_URL = process.env.NEXT_PUBLIC_API_URL

export async function enviarAudio(audio: Blob, nombre = "audio.webm"): Promise<Turno> {
  // ponytail: sin back configurado devuelve una respuesta fija, para poder diseñar la interfaz
  if (!API_URL) {
    await new Promise((r) => setTimeout(r, 1500))
    return { crudo: "kero ablar co maia", texto: "Quiero hablar con María." }
  }
  const datos = new FormData()
  datos.append("audio", audio, nombre)
  datos.append("persona_id", "demo")
  const r = await fetch(`${API_URL}/turno`, { method: "POST", body: datos })
  if (!r.ok) throw new Error(`El servidor respondió ${r.status}`)
  return r.json()
}

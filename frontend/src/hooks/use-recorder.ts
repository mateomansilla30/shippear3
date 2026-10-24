"use client"

import { useRef, useState } from "react"

// Por debajo de este pico (escala 0–1) la grabación se considera muda: llegó silencio del micrófono.
const PICO_MINIMO = 0.02

// Graba del micrófono y expone un AnalyserNode para que el orbe reaccione a la voz.
// También informa qué micrófono usa el navegador y si llegó sonido, para no mandar silencio al modelo.
export function useRecorder() {
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null)
  const [microfono, setMicrofono] = useState("")
  const recorder = useRef<MediaRecorder | null>(null)
  const partes = useRef<Blob[]>([])
  const ctx = useRef<AudioContext | null>(null)
  const pico = useRef(0)
  const medible = useRef(false)
  const medicion = useRef<number | null>(null)

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    setMicrofono(stream.getAudioTracks()[0]?.label ?? "")
    ctx.current = new AudioContext()
    // Si el contexto queda suspendido, el analizador lee ceros: en ese caso no se puede medir el nivel.
    await Promise.race([ctx.current.resume(), new Promise((r) => setTimeout(r, 300))]).catch(() => {})
    medible.current = ctx.current.state === "running"
    const node = ctx.current.createAnalyser()
    node.fftSize = 1024
    ctx.current.createMediaStreamSource(stream).connect(node)
    setAnalyser(node)

    pico.current = 0
    const muestras = new Float32Array(node.fftSize)
    const medir = () => {
      node.getFloatTimeDomainData(muestras)
      for (const v of muestras) pico.current = Math.max(pico.current, Math.abs(v))
      medicion.current = requestAnimationFrame(medir)
    }
    medir()

    partes.current = []
    recorder.current = new MediaRecorder(stream)
    recorder.current.ondataavailable = (e) => partes.current.push(e.data)
    recorder.current.start()
  }

  function stop(): Promise<Blob> {
    return new Promise((resolve) => {
      const rec = recorder.current
      if (!rec) return resolve(new Blob())
      recorder.current = null
      if (medicion.current !== null) cancelAnimationFrame(medicion.current)
      const terminar = () => {
        rec.stream.getTracks().forEach((t) => t.stop())
        ctx.current?.close().catch(() => {})
        setAnalyser(null)
        resolve(new Blob(partes.current, { type: rec.mimeType }))
      }
      // Si el micrófono se desconectó, el grabador ya se detuvo solo: se entrega lo que haya.
      if (rec.state === "inactive") return terminar()
      rec.onstop = terminar
      rec.stop()
    })
  }

  // false solo si se pudo medir y no llegó sonido (la grabación vino muda).
  function huboSonido() {
    return !medible.current || pico.current >= PICO_MINIMO
  }

  return { analyser, microfono, start, stop, huboSonido }
}

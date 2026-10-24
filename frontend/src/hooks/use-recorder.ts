"use client"

import { useRef, useState } from "react"

// Graba del micrófono y expone un AnalyserNode para que el orbe reaccione a la voz.
export function useRecorder() {
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const partes = useRef<Blob[]>([])
  const ctx = useRef<AudioContext | null>(null)

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    ctx.current = new AudioContext()
    const node = ctx.current.createAnalyser()
    node.fftSize = 1024
    ctx.current.createMediaStreamSource(stream).connect(node)
    setAnalyser(node)
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

  return { analyser, start, stop }
}

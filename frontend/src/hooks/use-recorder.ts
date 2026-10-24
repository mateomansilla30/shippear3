"use client"

import { useRef, useState } from "react"

// Graba del micrófono y expone un AnalyserNode para que el orbe reaccione a la voz.
export function useRecorder() {
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const ctx = useRef<AudioContext | null>(null)

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    ctx.current = new AudioContext()
    const node = ctx.current.createAnalyser()
    node.fftSize = 1024
    ctx.current.createMediaStreamSource(stream).connect(node)
    setAnalyser(node)
    recorder.current = new MediaRecorder(stream)
    recorder.current.start()
  }

  function stop(): Promise<Blob> {
    return new Promise((resolve) => {
      const rec = recorder.current
      if (!rec) return resolve(new Blob())
      const partes: Blob[] = []
      rec.ondataavailable = (e) => partes.push(e.data)
      rec.onstop = () => {
        rec.stream.getTracks().forEach((t) => t.stop())
        ctx.current?.close()
        setAnalyser(null)
        resolve(new Blob(partes, { type: rec.mimeType }))
      }
      rec.stop()
      recorder.current = null
    })
  }

  return { analyser, start, stop }
}

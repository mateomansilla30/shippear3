"use client"

import { useRef, useState } from "react"
import { useAnimationFrame, useMotionValue } from "motion/react"

import { VoiceOrb } from "@/components/voice-orb"
import { VoiceInput } from "@/components/voice-input"
import { TextShimmer } from "@/components/text-shimmer"
import { TextGenerateEffect } from "@/components/text-generate-effect"
import { FileDropzone } from "@/components/ui/file-dropzone"
import { useRecorder } from "@/hooks/use-recorder"
import { enviarAudio, type Turno } from "@/lib/api"
import { cn } from "@/lib/utils"

type Fase = "inicio" | "escuchando" | "pensando" | "hablando" | "listo" | "error"

const COLORES = ["#6d8cff", "#e8edff", "#24346f"] as const
const PALABRA_S = 0.1

export default function Home() {
  const [fase, setFase] = useState<Fase>("inicio")
  const [modo, setModo] = useState<"hablar" | "subir">("hablar")
  const [turno, setTurno] = useState<Turno | null>(null)
  const [error, setError] = useState("")
  const [vozAsistente, setVozAsistente] = useState<AnalyserNode | null>(null)
  const mic = useRecorder()

  // Mientras "habla" sin audio del back, el orbe simula sílabas y pausas.
  const actividad = useMotionValue(0)
  const hablaHasta = useRef(0)
  useAnimationFrame((ms) => {
    if (fase !== "hablando" || vozAsistente) return actividad.set(0)
    const t = ms / 1000
    const frase = Math.max(0, Math.sin(t * 0.85 + 1))
    const silaba = Math.max(0, Math.sin(t * 9.3 + Math.sin(t * 2.1)))
    actividad.set(frase * (0.12 + silaba ** 2 * 0.72))
    if (ms > hablaHasta.current) setFase("listo")
  })

  async function procesar(audio: Blob, nombre?: string) {
    setFase("pensando")
    setError("")
    try {
      const r = await enviarAudio(audio, nombre)
      setTurno(r)
      setFase("hablando")
      if (r.audio_url) reproducir(r.audio_url)
      else hablaHasta.current = performance.now() + (r.texto.split(" ").length * PALABRA_S + 0.8) * 1000
    } catch (e) {
      setError(e instanceof Error ? e.message : "No pude procesar el audio")
      setFase("error")
    }
  }

  function reproducir(url: string) {
    const audio = new Audio(url)
    audio.crossOrigin = "anonymous"
    const ctx = new AudioContext()
    const nodo = ctx.createAnalyser()
    ctx.createMediaElementSource(audio).connect(nodo)
    nodo.connect(ctx.destination)
    setVozAsistente(nodo)
    audio.onended = () => {
      setVozAsistente(null)
      ctx.close()
      setFase("listo")
    }
    audio.play().catch(() => audio.onended?.(new Event("ended")))
  }

  async function empezar() {
    try {
      await mic.start()
      setTurno(null)
      setFase("escuchando")
    } catch {
      setError("No pude usar el micrófono. Revisá los permisos del navegador.")
      setFase("error")
    }
  }

  async function terminar() {
    const audio = await mic.stop()
    if (audio.size === 0) return setFase("inicio")
    procesar(audio, `grabacion.${audio.type.includes("mp4") ? "mp4" : "webm"}`)
  }

  const ocupado = fase === "pensando" || fase === "hablando"

  return (
    <div className="flex min-h-dvh flex-col bg-background text-foreground">
      <header className="mx-auto flex w-full max-w-2xl items-center justify-between px-4 py-5 sm:px-6">
        <span className="text-base font-semibold tracking-tight">Voz Clara</span>
        <div role="tablist" aria-label="Cómo mandar el audio" className="flex rounded-full border p-1 text-sm">
          {(["hablar", "subir"] as const).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={modo === m}
              onClick={() => setModo(m)}
              disabled={fase === "escuchando"}
              className={cn(
                "rounded-full px-3 py-1 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/50",
                modo === m ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {m === "hablar" ? "Hablar" : "Subir audio"}
            </button>
          ))}
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center px-4 pb-10 sm:px-6">
        <VoiceOrb
          analyser={fase === "escuchando" ? mic.analyser : vozAsistente}
          activity={actividad}
          colors={COLORES}
          aria-label="Asistente"
          className="mt-4 w-52 sm:mt-8 sm:w-64"
        />

        <section aria-live="polite" className="mt-8 flex min-h-40 w-full flex-col items-center text-center">
          {fase === "inicio" && (
            <p className="text-lg text-muted-foreground">
              {modo === "hablar" ? "Mantené apretado el botón y hablá." : "Subí un audio y te digo qué entendí."}
            </p>
          )}
          {fase === "escuchando" && <TextShimmer text="Te escucho…" className="text-lg" />}
          {fase === "pensando" && <TextShimmer text="Entendiendo lo que dijiste…" className="text-lg" />}
          {fase === "error" && (
            <p role="alert" className="text-lg text-destructive">
              {error}
            </p>
          )}
          {turno && (fase === "hablando" || fase === "listo") && (
            <>
              <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Entendí</span>
              <TextGenerateEffect
                key={turno.texto}
                staggerDuration={PALABRA_S}
                className="mt-2 max-w-xl text-2xl leading-snug font-medium tracking-tight text-balance sm:text-3xl"
              >
                {turno.texto}
              </TextGenerateEffect>
              {turno.crudo && turno.crudo !== turno.texto && (
                <p className="mt-4 max-w-xl text-sm text-muted-foreground">
                  Whisper escuchó: <span className="italic">“{turno.crudo}”</span>
                </p>
              )}
            </>
          )}
        </section>

        <div className="mt-auto flex w-full flex-col items-center pt-8">
          {modo === "hablar" ? (
            <VoiceInput listening={fase === "escuchando"} disabled={ocupado} onStart={empezar} onStop={terminar} />
          ) : (
            <div className="w-full max-w-md">
              <FileDropzone accept="audio/*" maxSizeMB={25} onUpload={(f) => procesar(f, f.name)} />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

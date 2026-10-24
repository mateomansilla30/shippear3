"use client"

import { useEffect, useRef, useState } from "react"
import { motion, useAnimationFrame, useMotionValue, useReducedMotion } from "motion/react"
import { Check, PanelLeft, PenLine, Play, Upload, Volume2 } from "lucide-react"

import {
  AnimatedSidebarInset,
  AnimatedSidebarProvider,
  AnimatedSidebarTrigger,
} from "@/components/animated-sidebar"
import { BarraLateral, type Vista } from "@/components/barra-lateral"
import { Perfil } from "@/components/perfil"
import { PanelAudiosPrueba } from "@/components/panel-audios-prueba"
import { VoiceOrb } from "@/components/voice-orb"
import { VoiceInput } from "@/components/voice-input"
import { TextShimmer } from "@/components/text-shimmer"
import { TextGenerateEffect } from "@/components/text-generate-effect"
import { FileDropzone } from "@/components/ui/file-dropzone"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { useRecorder } from "@/hooks/use-recorder"
import {
  HAY_BACK,
  crearPersona,
  enviarAudio,
  guardarMemoria,
  listarPersonas,
  obtenerMemoria,
  urlAudioPrueba,
  validar,
  type Memoria,
  type Persona,
  type Pista,
  type Turno,
} from "@/lib/api"
import type { AudioPrueba } from "@/lib/audios-prueba"
import { cn } from "@/lib/utils"

type Fase = "inicio" | "escuchando" | "pensando" | "hablando" | "listo" | "error"

const COLORES = ["#0047fc", "#dce6ff", "#011b53"] as const // azul, claro y marino de la marca
const PALABRA_S = 0.1
const CLAVE_PERSONA = "vozclara:persona-actual"

export default function Home() {
  const [personas, setPersonas] = useState<Persona[]>([])
  const [personaId, setPersonaId] = useState("")
  const [memoria, setMemoria] = useState<Memoria | null>(null)
  const [vista, setVista] = useState<Vista>("asistente")

  const [fase, setFase] = useState<Fase>("inicio")
  const [modo, setModo] = useState<"hablar" | "subir">("hablar")
  const [turno, setTurno] = useState<Turno | null>(null)
  const [referencia, setReferencia] = useState<string | null>(null)
  const [original, setOriginal] = useState<string | null>(null) // audio que se mandó, para volver a escucharlo
  const [sonando, setSonando] = useState(false)
  const [error, setError] = useState("")
  const [voz, setVoz] = useState<AnalyserNode | null>(null)
  const [corrigiendo, setCorrigiendo] = useState(false)
  const [borrador, setBorrador] = useState("")
  const mic = useRecorder()
  const reducirMovimiento = useReducedMotion()

  useEffect(() => {
    listarPersonas().then((ps) => {
      setPersonas(ps)
      let guardada = ""
      try {
        guardada = localStorage.getItem(CLAVE_PERSONA) ?? ""
      } catch {}
      setPersonaId(ps.some((p) => p.id === guardada) ? guardada : (ps[0]?.id ?? ""))
    })
  }, [])

  useEffect(() => {
    if (!personaId) return
    try {
      localStorage.setItem(CLAVE_PERSONA, personaId)
    } catch {}
    setTurno(null)
    setFase("inicio")
    obtenerMemoria(personaId).then(setMemoria)
  }, [personaId])

  // Mientras "habla" sin audio del back, el orbe simula sílabas y pausas.
  const actividad = useMotionValue(0)
  const hablaHasta = useRef(0)
  useAnimationFrame((ms) => {
    if (fase !== "hablando" || voz) return actividad.set(0)
    const t = ms / 1000
    const frase = Math.max(0, Math.sin(t * 0.85 + 1))
    const silaba = Math.max(0, Math.sin(t * 9.3 + Math.sin(t * 2.1)))
    actividad.set(frase * (0.12 + silaba ** 2 * 0.72))
    if (ms > hablaHasta.current) setFase("listo")
  })

  // Libera el audio anterior cuando se reemplaza.
  useEffect(() => () => {
    if (original) URL.revokeObjectURL(original)
  }, [original])

  // Reproduce un audio conectado al orbe. Resuelve cuando termina (o si no se pudo reproducir).
  function reproducir(src: string) {
    return new Promise<void>((resolve) => {
      const audio = new Audio(src)
      audio.crossOrigin = "anonymous"
      const ctx = new AudioContext()
      let terminado = false
      const fin = () => {
        if (terminado) return
        terminado = true
        setVoz(null)
        ctx.close().catch(() => {})
        resolve()
      }
      audio.onended = fin
      audio.onerror = fin
      // Si el navegador crea el contexto suspendido, el audio pasaría por él en silencio.
      // Lo activamos y, si no se puede, reproducimos directo (sin orbe, pero se escucha).
      // resume() puede quedar pendiente para siempre si el navegador no lo permite: le damos 300 ms.
      Promise.race([ctx.resume(), new Promise((r) => setTimeout(r, 300))])
        .catch(() => {})
        .finally(() => {
          if (ctx.state === "running") {
            const nodo = ctx.createAnalyser()
            ctx.createMediaElementSource(audio).connect(nodo)
            nodo.connect(ctx.destination)
            setVoz(nodo)
          }
          audio.play().catch(fin)
        })
    })
  }

  // Para los botones de volver a escuchar: no pisa otra reproducción.
  async function escuchar(src: string) {
    if (sonando) return
    setSonando(true)
    await reproducir(src)
    setSonando(false)
  }

  async function procesar(audio: Blob, nombre?: string, pista?: Pista) {
    setOriginal(audio.size ? URL.createObjectURL(audio) : null)
    setFase("pensando")
    setError("")
    setCorrigiendo(false)
    try {
      const t = await enviarAudio(personaId, audio, nombre, pista)
      setTurno(t)
      obtenerMemoria(personaId).then(setMemoria)
      setFase("hablando")
      if (t.audio_url) reproducir(t.audio_url).then(() => setFase("listo"))
      else hablaHasta.current = performance.now() + (t.texto.split(" ").length * PALABRA_S + 0.8) * 1000
    } catch (e) {
      setError(e instanceof Error ? e.message : "No pude procesar el audio")
      setFase("error")
    }
  }

  async function empezar() {
    try {
      await mic.start()
      setTurno(null)
      setReferencia(null)
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

  async function probar(a: AudioPrueba) {
    setVista("asistente")
    setTurno(null)
    setReferencia(a.referencia)
    const ruta = urlAudioPrueba(a.id)
    const wav = await fetch(ruta).then((r) => (r.ok ? r.blob() : null)).catch(() => null)
    if (!wav && HAY_BACK) {
      setError(`El servidor no tiene el audio ${a.id}.wav. Copialo a voz/audios_prueba/ en el servidor.`)
      return setFase("error")
    }
    if (wav) {
      setFase("escuchando")
      const url = URL.createObjectURL(wav)
      await reproducir(url)
      URL.revokeObjectURL(url)
    }
    procesar(wav ?? new Blob(), `${a.id}.wav`, { texto: a.texto })
  }

  async function confirmar(textoFinal: string) {
    if (!turno) return
    const m = await validar(personaId, turno.id, textoFinal)
    setMemoria(m)
    setTurno(m.historial.find((h) => h.id === turno.id) ?? turno)
    setCorrigiendo(false)
  }

  function verTurno(t: Turno) {
    setVista("asistente")
    setTurno(t)
    setReferencia(null)
    setOriginal(null)
    setCorrigiendo(false)
    setFase("listo")
  }

  const ocupado = fase === "escuchando" || fase === "pensando" || fase === "hablando"
  const textoTurno = turno ? (turno.texto_final ?? turno.texto) : ""

  return (
    <AnimatedSidebarProvider className="bg-background text-foreground">
      <BarraLateral
        vista={vista}
        memoria={memoria}
        turnoActivo={turno?.id}
        ocupado={ocupado}
        onVista={setVista}
        onTurno={verTurno}
        onProbar={probar}
      />

      <AnimatedSidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-3 px-4 sm:px-6">
          <AnimatedSidebarTrigger
            aria-label="Mostrar u ocultar menú"
            className="-ml-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <PanelLeft aria-hidden="true" className="size-4" />
          </AnimatedSidebarTrigger>
          <span className="text-sm text-muted-foreground">
            {vista === "perfil" ? "Perfil y memoria" : memoria ? `Hablando con ${memoria.persona.nombre}` : ""}
          </span>
          {vista === "asistente" && (
            <div role="tablist" aria-label="Cómo mandar el audio" className="ml-auto flex rounded-full border p-1 text-sm">
              {(["hablar", "subir"] as const).map((m) => (
                <button
                  key={m}
                  role="tab"
                  aria-selected={modo === m}
                  onClick={() => setModo(m)}
                  disabled={ocupado}
                  className={cn(
                    "rounded-full px-3 py-1 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/50",
                    modo === m ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {m === "hablar" ? "Hablar" : "Subir audio"}
                </button>
              ))}
            </div>
          )}
        </header>

        {vista === "perfil" && memoria ? (
          <Perfil
            key={memoria.persona.id}
            memoria={memoria}
            personas={personas}
            onCambiarPersona={setPersonaId}
            onCrearPersona={async (nombre) => {
              const p = await crearPersona(nombre)
              setPersonas((ps) => [...ps, p])
              setPersonaId(p.id)
            }}
            onGuardar={async (datos) => {
              const m = await guardarMemoria(personaId, datos)
              setMemoria(m)
              setPersonas((ps) => ps.map((p) => (p.id === personaId ? m.persona : p)))
            }}
          />
        ) : (
          <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center px-4 sm:px-6">
            {/* Grande mientras espera o escucha; cuando hay respuesta sube y se achica para dejarle lugar. */}
            <motion.div
              initial={false}
              animate={turno ? { width: 128, marginTop: 8 } : { width: 176, marginTop: 16 }}
              transition={reducirMovimiento ? { duration: 0 } : { type: "spring", stiffness: 160, damping: 24 }}
              className="shrink-0"
            >
              <VoiceOrb
                analyser={fase === "escuchando" ? (mic.analyser ?? voz) : voz}
                activity={actividad}
                colors={COLORES}
                aria-label="Asistente"
                className="w-full"
              />
            </motion.div>

            <section aria-live="polite" className="mt-6 flex min-h-40 w-full flex-col items-center text-center">
              {(fase === "inicio" || fase === "error") && !turno && (
                <div className="order-last mt-6 w-full flex justify-center">
                  <PanelAudiosPrueba onProbar={probar} />
                </div>
              )}
              {fase === "inicio" && (
                <p className="text-lg text-muted-foreground">
                  {modo === "hablar" ? "Tocá el botón y hablá tranquilo. Cuando termines, tocalo de nuevo." : "Subí un audio y te digo qué entendí."}
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
                    key={textoTurno}
                    staggerDuration={fase === "hablando" ? PALABRA_S : 0}
                    className={cn(
                      "mt-2 max-w-xl leading-snug font-medium tracking-tight text-balance",
                      textoTurno.length > 120 ? "text-lg sm:text-xl" : "text-2xl sm:text-3xl",
                    )}
                  >
                    {textoTurno}
                  </TextGenerateEffect>

                  <dl className="mt-5 max-w-xl space-y-1 text-sm text-muted-foreground">
                    {referencia && (
                      <div className="line-clamp-2" title={referencia}>
                        <dt className="inline">Lo que dijo: </dt>
                        <dd className="inline italic">“{referencia}”</dd>
                      </div>
                    )}
                  </dl>

                  {(original || turno.audio_url) && (
                    <div className="mt-4 flex flex-wrap justify-center gap-2">
                      {original && (
                        <Button
                          variant="outline"
                          size="lg"
                          className="h-10 rounded-full px-4 text-sm"
                          disabled={sonando || fase === "hablando"}
                          onClick={() => escuchar(original)}
                        >
                          <Play /> Escuchar audio original
                        </Button>
                      )}
                      {turno.audio_url && (
                        <Button
                          variant="outline"
                          size="lg"
                          className="h-10 rounded-full px-4 text-sm"
                          disabled={sonando || fase === "hablando"}
                          onClick={() => escuchar(turno.audio_url!)}
                        >
                          <Volume2 /> Repetir respuesta
                        </Button>
                      )}
                    </div>
                  )}

                  {fase === "listo" && (
                    <div className="mt-6 w-full max-w-xl">
                      {turno.estado !== "pendiente" ? (
                        <p className="inline-flex items-center gap-2 rounded-full bg-muted px-3 py-1.5 text-sm">
                          {turno.estado === "validado" ? (
                            <>
                              <Check className="size-4 text-emerald-600" /> Validado
                            </>
                          ) : (
                            <>
                              <PenLine className="size-4 text-amber-600" /> Corregido: lo voy a recordar
                            </>
                          )}
                        </p>
                      ) : corrigiendo ? (
                        <form
                          className="space-y-3 text-left"
                          onSubmit={(e) => {
                            e.preventDefault()
                            if (borrador.trim()) confirmar(borrador.trim())
                          }}
                        >
                          <label className="block space-y-1.5">
                            <span className="text-sm font-medium">¿Qué quisiste decir?</span>
                            <Textarea value={borrador} onChange={(e) => setBorrador(e.target.value)} rows={3} autoFocus />
                          </label>
                          <div className="flex justify-end gap-2">
                            <Button type="button" variant="ghost" size="lg" onClick={() => setCorrigiendo(false)}>
                              Cancelar
                            </Button>
                            <Button type="submit" size="lg">
                              Guardar corrección
                            </Button>
                          </div>
                        </form>
                      ) : (
                        <div className="flex flex-col items-center gap-3 rounded-2xl border bg-muted/40 px-4 py-4">
                          <span className="text-base font-medium">¿Es esto lo que quisiste decir?</span>
                          <div className="flex w-full max-w-sm gap-3">
                            <Button size="lg" className="h-12 flex-1 text-base" onClick={() => confirmar(turno.texto)}>
                              <Check /> Sí, validar
                            </Button>
                            <Button
                              size="lg"
                              variant="outline"
                              className="h-12 flex-1 text-base"
                              onClick={() => {
                                setBorrador(turno.texto)
                                setCorrigiendo(true)
                              }}
                            >
                              <PenLine /> No, corregir
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </section>

            <div className="sticky bottom-0 mt-auto flex w-full flex-col items-center bg-background/90 pt-4 pb-6 backdrop-blur">
              {modo === "hablar" ? (
                <VoiceInput
                  listening={fase === "escuchando" && !!mic.analyser}
                  disabled={!personaId || fase === "pensando" || fase === "hablando" || (fase === "escuchando" && !mic.analyser)}
                  onStart={empezar}
                  onStop={terminar}
                />
              ) : turno || ocupado ? (
                // Con un resultado en pantalla, el dropzone se achica para no tapar la validación.
                <Button
                  variant="outline"
                  size="lg"
                  className="h-12 rounded-full px-5 text-base"
                  disabled={ocupado}
                  onClick={() => {
                    setTurno(null)
                    setReferencia(null)
                    setOriginal(null)
                    setFase("inicio")
                  }}
                >
                  <Upload /> Subir otro audio
                </Button>
              ) : (
                <div className="w-full max-w-md">
                  <FileDropzone accept="audio/*" maxSizeMB={25} onUpload={(f) => procesar(f, f.name)} />
                </div>
              )}
            </div>
          </div>
        )}
      </AnimatedSidebarInset>
    </AnimatedSidebarProvider>
  )
}

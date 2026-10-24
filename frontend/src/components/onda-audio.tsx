"use client"

// Adaptado de 21st.dev/thegridcn/waveform: las barras salen del audio real (AnalyserNode) en vez de una
// animación simulada, y con el estilo limpio de la app.

import * as React from "react"
import { useReducedMotion } from "motion/react"

import { cn } from "@/lib/utils"

const ALTO = 56

export function OndaAudio({ analyser, barras = 32, className }: { analyser: AnalyserNode | null; barras?: number; className?: string }) {
  const [alturas, setAlturas] = React.useState<number[]>(() => Array(barras).fill(3))
  const reducir = useReducedMotion()

  React.useEffect(() => {
    // Con movimiento reducido la onda igual se muestra: no es decoración, es la forma de ver que el micrófono
    // escucha. Solo se actualiza menos seguido y sin transición.
    if (!analyser) return setAlturas(Array(barras).fill(3))
    const datos = new Uint8Array(analyser.frequencyBinCount)
    let ultimo = 0
    // La voz vive entre ~80 Hz y ~4 kHz: el primer 16 % del espectro. Se dibuja en espejo desde el centro.
    const util = Math.max(8, Math.floor(datos.length * 0.16))
    const mitad = Math.ceil(barras / 2)
    let raf = 0
    const dibujar = (ms: number) => {
      raf = requestAnimationFrame(dibujar)
      if (reducir && ms - ultimo < 125) return
      ultimo = ms
      analyser.getByteFrequencyData(datos)
      const lado = Array.from({ length: mitad }, (_, i) => {
        const desde = Math.floor((i * util) / mitad)
        const hasta = Math.max(desde + 1, Math.floor(((i + 1) * util) / mitad))
        let suma = 0
        for (let j = desde; j < hasta; j++) suma += datos[j]
        return Math.max(3, (suma / (hasta - desde) / 255) * ALTO)
      })
      setAlturas([...lado].reverse().concat(lado).slice(0, barras))
    }
    raf = requestAnimationFrame(dibujar)
    return () => cancelAnimationFrame(raf)
  }, [analyser, barras, reducir])

  return (
    <div aria-hidden className={cn("flex items-center justify-center gap-[3px]", className)} style={{ height: ALTO }}>
      {alturas.map((h, i) => (
        <div
          key={i}
          className={cn("w-1.5 rounded-full bg-[#0047fc]", !reducir && "transition-[height] duration-75")}
          style={{ height: h, opacity: 0.35 + (h / ALTO) * 0.65 }}
        />
      ))}
    </div>
  )
}

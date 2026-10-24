"use client"

// Adaptado de 21st.dev/molecule-lab-rushil/voice-input, controlado desde afuera.
// Tocar para empezar y tocar para terminar: la grabación nunca se corta sola. Mantener apretado no
// sirve para personas con poca precisión motora (soltar sin querer o salirse del botón cortaba).

import React from "react"
import { Mic } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { cn } from "@/lib/utils"

interface VoiceInputProps {
  listening: boolean
  disabled?: boolean
  onStart: () => void
  onStop: () => void
  className?: string
}

export function VoiceInput({ listening, disabled, onStart, onStop, className }: VoiceInputProps) {
  const [time, setTime] = React.useState(0)

  React.useEffect(() => {
    if (!listening) return setTime(0)
    const id = setInterval(() => setTime((t) => t + 1), 1000)
    return () => clearInterval(id)
  }, [listening])

  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`

  return (
    <motion.button
      type="button"
      disabled={disabled}
      aria-pressed={listening}
      onClick={() => (listening ? onStop() : onStart())}
      layout
      transition={{ layout: { duration: 0.4 } }}
      className={cn(
        "flex h-16 items-center justify-center gap-3 rounded-full border bg-background px-6 text-base font-medium shadow-sm select-none",
        "outline-none focus-visible:ring-4 focus-visible:ring-ring/40 disabled:opacity-50",
        listening && "border-foreground/20 shadow-md",
        className,
      )}
    >
      <span className="flex size-7 items-center justify-center">
        {listening ? (
          <motion.span
            className="size-5 rounded-sm bg-primary"
            animate={{ rotate: [0, 180, 360] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        ) : (
          <Mic className="size-7" />
        )}
      </span>
      <AnimatePresence mode="wait">
        {listening && (
          <motion.span
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            exit={{ opacity: 0, width: 0 }}
            transition={{ duration: 0.4 }}
            className="flex items-center gap-3 overflow-hidden"
          >
            <span className="flex items-center gap-0.5">
              {[...Array(12)].map((_, i) => (
                <motion.span
                  key={i}
                  className="w-0.5 rounded-full bg-primary"
                  initial={{ height: 2 }}
                  animate={{ height: [2, 3 + Math.random() * 14, 3 + Math.random() * 7, 2] }}
                  transition={{ duration: 1, repeat: Infinity, delay: i * 0.05, ease: "easeInOut" }}
                />
              ))}
            </span>
            <span className="w-12 text-center text-sm text-muted-foreground tabular-nums">{formatTime(time)}</span>
          </motion.span>
        )}
      </AnimatePresence>
      <span>{listening ? "Terminar" : "Tocá para hablar"}</span>
    </motion.button>
  )
}

"use client"

// Adaptado de 21st.dev/molecule-lab-rushil/voice-input: controlado desde afuera y con
// "mantener apretado para hablar". Un toque corto también sirve (toca para empezar, toca para
// terminar) para quien no puede sostener el botón.

import React from "react"
import { Mic } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { cn } from "@/lib/utils"

const TOQUE_MS = 300

interface VoiceInputProps {
  listening: boolean
  disabled?: boolean
  onStart: () => void
  onStop: () => void
  className?: string
}

export function VoiceInput({ listening, disabled, onStart, onStop, className }: VoiceInputProps) {
  const [time, setTime] = React.useState(0)
  const pressedAt = React.useRef(0)
  const toggled = React.useRef(false)

  React.useEffect(() => {
    if (!listening) return setTime(0)
    const id = setInterval(() => setTime((t) => t + 1), 1000)
    return () => clearInterval(id)
  }, [listening])

  const down = () => {
    if (disabled) return
    if (listening && toggled.current) {
      toggled.current = false
      return onStop()
    }
    pressedAt.current = Date.now()
    onStart()
  }
  const up = () => {
    if (!listening || toggled.current) return
    if (Date.now() - pressedAt.current < TOQUE_MS) toggled.current = true
    else onStop()
  }

  const formatTime = (s: number) =>
    `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`

  return (
    <motion.button
      type="button"
      disabled={disabled}
      aria-pressed={listening}
      aria-label={listening ? "Dejar de grabar" : "Mantené apretado para hablar"}
      onPointerDown={down}
      onPointerUp={up}
      onPointerLeave={up}
      onKeyDown={(e) => {
        if ((e.key === " " || e.key === "Enter") && !e.repeat) {
          e.preventDefault()
          down()
        }
      }}
      onKeyUp={(e) => {
        if (e.key === " " || e.key === "Enter") up()
      }}
      onContextMenu={(e) => e.preventDefault()}
      layout
      transition={{ layout: { duration: 0.4 } }}
      className={cn(
        "flex h-16 touch-none items-center justify-center rounded-full border bg-background px-5 shadow-sm select-none",
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
            initial={{ opacity: 0, width: 0, marginLeft: 0 }}
            animate={{ opacity: 1, width: "auto", marginLeft: 12 }}
            exit={{ opacity: 0, width: 0, marginLeft: 0 }}
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
    </motion.button>
  )
}

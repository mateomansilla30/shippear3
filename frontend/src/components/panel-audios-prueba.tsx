"use client"

import { useState } from "react"
import { ChevronDown, Play } from "lucide-react"

import { AUDIOS_PRUEBA, type AudioPrueba } from "@/lib/audios-prueba"
import { cn } from "@/lib/utils"

// Lo primero que se ve en el asistente: audios reales para probar sin tener que hablar.
export function PanelAudiosPrueba({ onProbar, disabled }: { onProbar: (a: AudioPrueba) => void; disabled?: boolean }) {
  const [todos, setTodos] = useState(false)

  return (
    <section aria-labelledby="titulo-audios" className="w-full max-w-xl text-left">
      <h2 id="titulo-audios" className="text-base font-semibold tracking-tight">
        Probalo con audios reales
      </h2>
      <p className="text-sm text-muted-foreground">
        Personas con ELA, Parkinson y ACV que el sistema nunca escuchó. Tocá uno.
      </p>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {AUDIOS_PRUEBA.slice(0, 4).map((a) => (
          <button
            key={a.id}
            type="button"
            disabled={disabled}
            onClick={() => onProbar(a)}
            className="group flex items-start gap-3 rounded-2xl border bg-muted/30 p-3 text-left outline-none transition-colors hover:border-[#0047fc]/40 hover:bg-[#dce6ff]/40 focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-50"
          >
            <span className="grid size-9 shrink-0 place-items-center rounded-full bg-[#0047fc] text-white">
              <Play className="size-4 fill-current" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-medium">{a.titulo}</span>
              <span className="block text-xs text-muted-foreground">{a.detalle}</span>
            </span>
          </button>
        ))}
      </div>

      <button
        type="button"
        aria-expanded={todos}
        onClick={() => setTodos((t) => !t)}
        className="mt-2 inline-flex items-center gap-1 rounded-md px-1 text-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50"
      >
        {todos ? "Ver menos" : `Ver los ${AUDIOS_PRUEBA.length} audios`}
        <ChevronDown className={cn("size-4 transition-transform", todos && "rotate-180")} />
      </button>

      {todos && (
        <ul className="mt-2 max-h-56 divide-y overflow-y-auto rounded-2xl border">
          {AUDIOS_PRUEBA.slice(4).map((a) => (
            <li key={a.id}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onProbar(a)}
                className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm outline-none hover:bg-muted focus-visible:bg-muted disabled:opacity-50"
              >
                <Play className="size-3.5 shrink-0 fill-current text-[#0047fc]" />
                <span className="min-w-0 flex-1 truncate">{a.titulo}</span>
                <span className="shrink-0 text-xs text-muted-foreground">{a.detalle.split(" · ")[0]}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

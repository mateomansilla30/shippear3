"use client"

import { useState } from "react"
import { Plus, Trash2, UserPlus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { TagInput } from "@/components/tag-input"
import type { Editable, Memoria, Persona } from "@/lib/api"
import { cn } from "@/lib/utils"

type Props = {
  memoria: Memoria
  personas: Persona[]
  onGuardar: (datos: Editable) => Promise<void>
  onCambiarPersona: (id: string) => void
  onCrearPersona: (nombre: string) => void
}

export function Perfil({ memoria, personas, onGuardar, onCambiarPersona, onCrearPersona }: Props) {
  const [datos, setDatos] = useState<Editable>(() => ({
    persona: memoria.persona,
    contactos: memoria.contactos,
    vocabulario: memoria.vocabulario,
    correcciones: memoria.correcciones,
  }))
  const [estado, setEstado] = useState<"" | "guardando" | "guardado">("")
  const [nueva, setNueva] = useState("")

  const cambiar = (parcial: Partial<Editable>) => {
    setDatos((d) => ({ ...d, ...parcial }))
    setEstado("")
  }
  const contacto = (i: number, campo: "nombre" | "relacion" | "telefono", valor: string) =>
    cambiar({ contactos: datos.contactos.map((c, j) => (j === i ? { ...c, [campo]: valor } : c)) })

  async function guardar() {
    setEstado("guardando")
    await onGuardar({ ...datos, contactos: datos.contactos.filter((c) => c.nombre.trim()) })
    setEstado("guardado")
  }

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8 sm:px-6">
      <section aria-labelledby="personas" className="mb-10">
        <h2 id="personas" className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Personas
        </h2>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {personas.map((p) => (
            <button
              key={p.id}
              type="button"
              aria-pressed={p.id === memoria.persona.id}
              onClick={() => onCambiarPersona(p.id)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/50",
                p.id === memoria.persona.id ? "bg-foreground text-background" : "hover:bg-muted",
              )}
            >
              {p.nombre}
            </button>
          ))}
          <form
            className="flex items-center gap-1"
            onSubmit={(e) => {
              e.preventDefault()
              if (nueva.trim()) onCrearPersona(nueva.trim())
              setNueva("")
            }}
          >
            <Input
              value={nueva}
              onChange={(e) => setNueva(e.target.value)}
              placeholder="Nueva persona"
              aria-label="Nombre de la nueva persona"
              className="h-8 w-36 rounded-full"
            />
            <Button type="submit" variant="ghost" size="icon" aria-label="Agregar persona">
              <UserPlus />
            </Button>
          </form>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Cada persona tiene su propia memoria: lo que se valida con una no afecta a las demás.
        </p>
      </section>

      <section aria-labelledby="quien" className="space-y-4">
        <h2 id="quien" className="text-xl font-semibold tracking-tight">
          Quién es
        </h2>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Nombre</span>
          <Input
            value={datos.persona.nombre}
            onChange={(e) => cambiar({ persona: { ...datos.persona, nombre: e.target.value } })}
          />
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Sobre la persona</span>
          <Textarea
            value={datos.persona.notas ?? ""}
            onChange={(e) => cambiar({ persona: { ...datos.persona, notas: e.target.value } })}
            placeholder="Ej.: tiene ELA, habla despacio, le gusta el fútbol."
            rows={3}
          />
        </label>
      </section>

      <section aria-labelledby="contactos" className="mt-10 space-y-3">
        <div>
          <h2 id="contactos" className="text-xl font-semibold tracking-tight">
            Contactos
          </h2>
          <p className="text-sm text-muted-foreground">Ayudan a reconocer nombres: &quot;mandale a María&quot;.</p>
        </div>
        {datos.contactos.map((c, i) => (
          <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-2 sm:grid-cols-[1fr_1fr_1fr_auto]">
            <Input aria-label="Nombre" placeholder="Nombre" value={c.nombre} onChange={(e) => contacto(i, "nombre", e.target.value)} />
            <Input aria-label="Relación" placeholder="Relación" value={c.relacion} onChange={(e) => contacto(i, "relacion", e.target.value)} />
            <Input
              aria-label="Teléfono"
              placeholder="Teléfono"
              type="tel"
              value={c.telefono ?? ""}
              onChange={(e) => contacto(i, "telefono", e.target.value)}
              className="col-span-2 sm:col-span-1"
            />
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Quitar a ${c.nombre || "este contacto"}`}
              onClick={() => cambiar({ contactos: datos.contactos.filter((_, j) => j !== i) })}
              className="row-start-1 col-start-3 sm:col-start-4"
            >
              <Trash2 />
            </Button>
          </div>
        ))}
        <Button variant="outline" onClick={() => cambiar({ contactos: [...datos.contactos, { nombre: "", relacion: "" }] })}>
          <Plus /> Agregar contacto
        </Button>
      </section>

      <section aria-labelledby="palabras" className="mt-10 space-y-3">
        <div>
          <h2 id="palabras" className="text-xl font-semibold tracking-tight">
            Palabras frecuentes
          </h2>
          <p className="text-sm text-muted-foreground">Medicamentos, lugares, nombres o frases que repite.</p>
        </div>
        <TagInput value={datos.vocabulario} onChange={(vocabulario) => cambiar({ vocabulario })} max={60} />
      </section>

      <section aria-labelledby="aprendi" className="mt-10 space-y-3">
        <div>
          <h2 id="aprendi" className="text-xl font-semibold tracking-tight">
            Lo que aprendí
          </h2>
          <p className="text-sm text-muted-foreground">
            Cada corrección que validás se usa como ejemplo la próxima vez que escuche algo parecido.
          </p>
        </div>
        {datos.correcciones.length === 0 ? (
          <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
            Todavía no aprendí nada. Corregí una transcripción desde el asistente.
          </p>
        ) : (
          <ul className="divide-y rounded-xl border">
            {datos.correcciones.map((c, i) => (
              <li key={i} className="flex items-start gap-3 p-3">
                <div className="min-w-0 flex-1 text-sm">
                  <p className="truncate text-muted-foreground line-through decoration-muted-foreground/40">{c.crudo}</p>
                  <p className="mt-0.5 font-medium">{c.texto}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Olvidar esta corrección"
                  onClick={() => cambiar({ correcciones: datos.correcciones.filter((_, j) => j !== i) })}
                >
                  <Trash2 />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="sticky bottom-0 mt-10 flex items-center justify-end gap-3 border-t bg-background/90 py-4 backdrop-blur">
        <span role="status" className="text-sm text-muted-foreground">
          {estado === "guardado" && "Guardado"}
        </span>
        <Button onClick={guardar} disabled={estado === "guardando"}>
          {estado === "guardando" ? "Guardando…" : "Guardar perfil"}
        </Button>
      </div>
    </div>
  )
}

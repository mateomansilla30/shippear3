"use client"

import Image from "next/image"
import { Check, Circle, Mic, PenLine, UserRound, X } from "lucide-react"

import {
  AnimatedSidebar,
  AnimatedSidebarClose,
  AnimatedSidebarContent,
  AnimatedSidebarFooter,
  AnimatedSidebarGroup,
  AnimatedSidebarGroupContent,
  AnimatedSidebarGroupLabel,
  AnimatedSidebarHeader,
  AnimatedSidebarMenu,
  AnimatedSidebarMenuButton,
  AnimatedSidebarMenuItem,
  AnimatedSidebarRail,
} from "@/components/animated-sidebar"
import type { Memoria, Turno } from "@/lib/api"

export type Vista = "asistente" | "perfil"

const ICONO_ESTADO = {
  pendiente: <Circle className="size-3.5" />,
  validado: <Check className="size-4 text-emerald-600" />,
  corregido: <PenLine className="size-4 text-amber-600" />,
}

type Props = {
  vista: Vista
  memoria: Memoria | null
  turnoActivo?: string
  onVista: (v: Vista) => void
  onTurno: (t: Turno) => void
}

export function BarraLateral({ vista, memoria, turnoActivo, onVista, onTurno }: Props) {
  const recientes = memoria?.historial.slice(0, 8) ?? []
  const nombre = memoria?.persona.nombre ?? "…"

  return (
    <AnimatedSidebar ariaLabel="Voz Clara" collapsible="icon" panelClassName="bg-muted/30">
      <AnimatedSidebarHeader className="p-3 pb-2">
        <div className="flex min-h-11 items-center gap-3 overflow-hidden px-2">
          <Image
            src="/logo-voz-clara.png"
            alt="Voz Clara"
            width={1068}
            height={160}
            priority
            className="h-6 w-auto group-data-[state=collapsed]/sidebar:hidden"
          />
          <Image
            src="/emblema-voz-clara.png"
            alt="Voz Clara"
            width={397}
            height={256}
            className="hidden h-5 w-auto shrink-0 group-data-[state=collapsed]/sidebar:block"
          />
          <AnimatedSidebarClose aria-label="Cerrar menú" className="ml-auto text-muted-foreground hover:bg-muted md:hidden">
            <X aria-hidden="true" className="size-4" />
          </AnimatedSidebarClose>
        </div>
      </AnimatedSidebarHeader>

      <AnimatedSidebarContent className="px-2 pt-1">
        <AnimatedSidebarGroup>
          <AnimatedSidebarGroupContent>
            <AnimatedSidebarMenu>
              <AnimatedSidebarMenuItem>
                <AnimatedSidebarMenuButton
                  icon={<Mic className="size-4" />}
                  isActive={vista === "asistente"}
                  onSelect={() => onVista("asistente")}
                >
                  Asistente
                </AnimatedSidebarMenuButton>
              </AnimatedSidebarMenuItem>
              <AnimatedSidebarMenuItem>
                <AnimatedSidebarMenuButton
                  icon={<UserRound className="size-4" />}
                  isActive={vista === "perfil"}
                  badge={memoria?.correcciones.length || undefined}
                  onSelect={() => onVista("perfil")}
                >
                  Perfil y memoria
                </AnimatedSidebarMenuButton>
              </AnimatedSidebarMenuItem>
            </AnimatedSidebarMenu>
          </AnimatedSidebarGroupContent>
        </AnimatedSidebarGroup>

        <AnimatedSidebarGroup>
          <AnimatedSidebarGroupLabel>Recientes</AnimatedSidebarGroupLabel>
          <AnimatedSidebarGroupContent>
            {recientes.length === 0 ? (
              <p className="px-3 text-xs text-muted-foreground group-data-[state=collapsed]/sidebar:hidden">
                Todavía no hay transcripciones.
              </p>
            ) : (
              <AnimatedSidebarMenu>
                {recientes.map((t) => (
                  <AnimatedSidebarMenuItem key={t.id}>
                    <AnimatedSidebarMenuButton
                      icon={ICONO_ESTADO[t.estado]}
                      isActive={vista === "asistente" && turnoActivo === t.id}
                      onSelect={() => onTurno(t)}
                    >
                      {t.texto_final ?? t.texto}
                    </AnimatedSidebarMenuButton>
                  </AnimatedSidebarMenuItem>
                ))}
              </AnimatedSidebarMenu>
            )}
          </AnimatedSidebarGroupContent>
        </AnimatedSidebarGroup>

      </AnimatedSidebarContent>

      <AnimatedSidebarFooter className="border-none p-3">
        <button
          type="button"
          onClick={() => onVista("perfil")}
          className="flex min-h-11 w-full items-center gap-3 overflow-hidden rounded-xl p-1 text-left outline-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="grid size-9 shrink-0 place-items-center rounded-full bg-[#dce6ff] text-xs font-semibold text-[#011b53]">
            {nombre.slice(0, 2).toUpperCase()}
          </span>
          <span className="min-w-0 flex-1 group-data-[state=collapsed]/sidebar:hidden">
            <span className="block truncate text-sm font-medium">{nombre}</span>
            <span className="block truncate text-xs text-muted-foreground">
              {memoria?.correcciones.length === 1 ? "1 corrección aprendida" : `${memoria?.correcciones.length ?? 0} correcciones aprendidas`}
            </span>
          </span>
        </button>
      </AnimatedSidebarFooter>

      <AnimatedSidebarRail aria-label="Mostrar u ocultar menú" />
    </AnimatedSidebar>
  )
}

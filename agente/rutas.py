"""Rutas de memoria para el front. Se montan en el FastAPI del back:

    from agente.rutas import router as rutas_agente
    app.include_router(rutas_agente)

POST /turno lo implementa el pipeline de voz y llama a agente.procesar_turno (ver AGENTE.md).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import agente

router = APIRouter()


class NuevaPersona(BaseModel):
    nombre: str


class Edicion(BaseModel):
    persona: dict
    contactos: list[dict]
    vocabulario: list[str]
    correcciones: list[dict]


class Validacion(BaseModel):
    persona_id: str
    turno_id: str
    texto_final: str


class Sugerencia(BaseModel):
    persona_id: str
    valor: str
    tipo: str  # contacto | palabra | descartar
    relacion: str = ""


def _memoria(persona_id, cambio=None):
    try:
        return agente.para_front(cambio() if cambio else agente.cargar(persona_id))
    except KeyError:
        raise HTTPException(404, "No existe esa persona o ese turno")


@router.get("/personas")
def personas():
    return agente.listar_personas()


@router.post("/personas")
def crear(p: NuevaPersona):
    return agente.crear_persona(p.nombre.strip())


@router.get("/memoria/{persona_id}")
def memoria(persona_id: str):
    return _memoria(persona_id)


@router.put("/memoria/{persona_id}")
def editar(persona_id: str, e: Edicion):
    return _memoria(persona_id, lambda: agente.editar(persona_id, e.persona, e.contactos, e.vocabulario,
                                                      e.correcciones))


@router.post("/validar")
def validar(v: Validacion):
    return _memoria(v.persona_id, lambda: agente.validar(v.persona_id, v.turno_id, v.texto_final))


@router.post("/sugerencia")
def sugerencia(s: Sugerencia):
    if s.tipo not in ("contacto", "palabra", "descartar"):
        raise HTTPException(422, "tipo tiene que ser contacto, palabra o descartar")
    return _memoria(s.persona_id, lambda: agente.responder_sugerencia(s.persona_id, s.valor, s.tipo,
                                                                      s.relacion))

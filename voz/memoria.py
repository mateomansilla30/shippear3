"""Memoria por persona, guardada en archivos JSON (voz/datos/). Versión simple para el hackatón.

Sigue el contrato de frontend/src/lib/api.ts: Persona, Memoria {persona, contactos, vocabulario, correcciones,
historial} y Turno {id, texto, audio_url, fecha, estado, texto_final}.

Aprendizaje simple: si una transcripción nueva se parece a una que la persona ya corrigió (WER ≤ 0,25), se usa la
corrección. El agente con LLM puede reemplazar `aplicar_correcciones` por algo mejor sin tocar el front.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import jiwer

import config
from reglas import normalizar

DATOS = config.CARPETA / "datos"
_candado = threading.Lock()
SIMILITUD_MAX_WER = 0.25
MAX_HISTORIAL = 50

PERSONA_DEMO = {"id": "demo", "nombre": "Marta", "notas": "Tiene ELA. Habla despacio y hace pausas largas."}
MEMORIA_DEMO = {
    "persona": PERSONA_DEMO,
    "contactos": [{"nombre": "María", "relacion": "hija"}, {"nombre": "Juan", "relacion": "amigo"}],
    "vocabulario": ["Riluzol", "kinesiólogo", "Háblalo"],
    "correcciones": [],
    "historial": [],
}


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ruta(nombre: str) -> Path:
    DATOS.mkdir(parents=True, exist_ok=True)
    return DATOS / nombre


def _leer(nombre: str, defecto):
    p = _ruta(nombre)
    if not p.exists():
        return defecto
    return json.loads(p.read_text(encoding="utf-8"))


def _escribir(nombre: str, valor) -> None:
    p = _ruta(nombre)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(valor, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)  # escritura atómica: no queda un JSON a medias si se corta


# --- Personas ---------------------------------------------------------------

def listar_personas() -> list[dict]:
    with _candado:
        personas = _leer("personas.json", [])
        if not personas:
            personas = [PERSONA_DEMO]
            _escribir("personas.json", personas)
            _escribir("memoria_demo.json", MEMORIA_DEMO)
        return personas


def crear_persona(nombre: str) -> dict:
    persona = {"id": uuid.uuid4().hex[:12], "nombre": nombre.strip() or "Sin nombre"}
    listar_personas()
    with _candado:
        _escribir("personas.json", _leer("personas.json", []) + [persona])
        _escribir(f"memoria_{persona['id']}.json", {"persona": persona, "contactos": [], "vocabulario": [],
                                                    "correcciones": [], "historial": []})
    return persona


# --- Memoria ----------------------------------------------------------------

def obtener_memoria(persona_id: str) -> dict:
    listar_personas()
    with _candado:
        m = _leer(f"memoria_{persona_id}.json", None)
    if m is None:
        raise KeyError(persona_id)
    return m


def guardar_memoria(persona_id: str, datos: dict) -> dict:
    """Actualiza lo editable desde el front: persona, contactos, vocabulario, correcciones."""
    m = obtener_memoria(persona_id)
    for clave in ("persona", "contactos", "vocabulario", "correcciones"):
        if clave in datos:
            m[clave] = datos[clave]
    m["persona"]["id"] = persona_id
    with _candado:
        _escribir(f"memoria_{persona_id}.json", m)
        personas = [m["persona"] if p["id"] == persona_id else p for p in _leer("personas.json", [])]
        _escribir("personas.json", personas)
    return m


def vocabulario_para_asr(m: dict) -> list[str]:
    """Nombres de contactos + vocabulario propio: se le pasan a Whisper para que los escriba bien."""
    nombres = [c["nombre"] for c in m.get("contactos", []) if c.get("nombre")]
    return list(dict.fromkeys(nombres + list(m.get("vocabulario", []))))[:30]


def aplicar_correcciones(m: dict, texto: str) -> tuple[str, dict | None]:
    """Si el texto se parece a una corrección validada, devuelve el texto corregido y la corrección usada."""
    nuevo = normalizar(texto)
    if len(nuevo.split()) < 2:
        return texto, None
    mejor, mejor_wer = None, SIMILITUD_MAX_WER
    for c in m.get("correcciones", []):
        original = normalizar(c["original"])
        if not original:
            continue
        w = 0.0 if original == nuevo else jiwer.wer(original, nuevo)
        if w <= mejor_wer:
            mejor, mejor_wer = c, w
    return (mejor["texto"], mejor) if mejor else (texto, None)


def agregar_turno(persona_id: str, turno: dict) -> dict:
    m = obtener_memoria(persona_id)
    m["historial"] = [turno] + m.get("historial", [])[:MAX_HISTORIAL - 1]
    with _candado:
        _escribir(f"memoria_{persona_id}.json", m)
    return turno


def validar(persona_id: str, turno_id: str, texto_final: str) -> dict:
    """La persona confirma o corrige. Si corrige, se guarda la corrección {original → texto_final}."""
    m = obtener_memoria(persona_id)
    turno = next((t for t in m["historial"] if t["id"] == turno_id), None)
    if turno is None:
        raise KeyError(turno_id)
    texto_final = " ".join(texto_final.split())
    corregido = texto_final != " ".join(turno["texto"].split())
    turno["estado"] = "corregido" if corregido else "validado"
    turno["texto_final"] = texto_final
    if corregido:
        # Se aprende de lo que dijo Whisper (texto_asr), no de un texto ya corregido por la memoria
        original = turno.get("texto_asr") or turno["texto"]
        m["correcciones"] = [{"original": original, "texto": texto_final, "fecha": _ahora()}] + [
            c for c in m.get("correcciones", []) if normalizar(c["original"]) != normalizar(original)]
    with _candado:
        _escribir(f"memoria_{persona_id}.json", m)
    return m


def nuevo_turno_id() -> str:
    return uuid.uuid4().hex[:12]


def ahora() -> str:
    return _ahora()

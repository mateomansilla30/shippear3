"""API HTTP de Voz Clara (FastAPI): pipeline de voz + memoria por persona.

Sigue el contrato de frontend/src/lib/api.ts. Correr (desde la carpeta voz/):
    .venv/Scripts/python -m uvicorn servidor:app --reload --port 8000     (Windows)
    .venv/bin/python -m uvicorn servidor:app --reload --port 8000         (Mac/Linux)
En el front: NEXT_PUBLIC_API_URL=http://localhost:8000 en frontend/.env.local
Probar sin front: http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

import config
import memoria
from asr import transcribir
from nota_voz import a_nota_de_voz
from pipeline import hablar, turno as correr_turno

app = FastAPI(title="Voz Clara")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
AUDIOS = memoria.DATOS / "audios"


def _memoria_o_404(persona_id: str) -> dict:
    try:
        return memoria.obtener_memoria(persona_id)
    except KeyError:
        raise HTTPException(404, f"No existe la persona {persona_id}")


@app.get("/salud")
def salud():
    return {"ok": True, "asr": config.ASR_MODELO,
            "tts": {"principal": config.TTS_PROVEEDOR, "respaldo": config.TTS_RESPALDO,
                    "voz_openai": config.TTS_OPENAI_VOZ, "voz_gemini": config.TTS_GEMINI_VOZ},
            "claves": {"groq": bool(config.GROQ_API_KEY), "openai": bool(config.OPENAI_API_KEY),
                       "gemini": bool(config.GEMINI_API_KEY)}}


# --- Personas y memoria (contrato del front) ----------------------------------

class PedidoPersona(BaseModel):
    nombre: str


@app.get("/personas")
def api_personas():
    return memoria.listar_personas()


@app.post("/personas")
def api_crear_persona(p: PedidoPersona):
    return memoria.crear_persona(p.nombre)


@app.get("/memoria/{persona_id}")
def api_memoria(persona_id: str):
    return _memoria_o_404(persona_id)


@app.put("/memoria/{persona_id}")
def api_guardar_memoria(persona_id: str, datos: dict):
    _memoria_o_404(persona_id)
    return memoria.guardar_memoria(persona_id, datos)


@app.post("/turno")
async def api_turno(request: Request, audio: UploadFile = File(...), persona_id: str = Form("demo"),
                    alternativa: bool = Form(True)):
    """Audio de la persona → lo que el sistema entendió + su voz. Se guarda en el historial.

    Devuelve un Turno {id, texto, audio_url, fecha, estado} más datos para depurar: texto_asr (Whisper tal cual,
    con reglas), confianza, nivel, hipotesis, correccion_usada y tiempos_ms.
    """
    m = _memoria_o_404(persona_id)
    datos = await audio.read()
    if not datos:
        raise HTTPException(400, "Audio vacío")

    usada = {}

    def interpretar(tr):
        texto, correccion = memoria.aplicar_correcciones(m, tr.texto)
        usada["c"] = correccion
        return texto or "No te entendí. ¿Podés repetirlo?"

    t = correr_turno(datos, audio.filename or "audio.webm", interpretar=interpretar,
                     vocabulario=memoria.vocabulario_para_asr(m), alternativa=alternativa)
    turno_id = memoria.nuevo_turno_id()
    audio_url = None
    if t.wav:
        AUDIOS.mkdir(parents=True, exist_ok=True)
        (AUDIOS / f"{turno_id}.wav").write_bytes(t.wav)
        audio_url = f"{str(request.base_url).rstrip('/')}/audio/{turno_id}.wav"
    nuevo = {
        "id": turno_id, "texto": t.texto_a_decir, "audio_url": audio_url, "fecha": memoria.ahora(),
        "estado": "pendiente",
        "texto_asr": t.transcripcion.texto, "confianza": t.transcripcion.confianza,
        "nivel": t.transcripcion.nivel, "hipotesis": t.transcripcion.hipotesis,
        "correccion_usada": usada.get("c"), "tiempos_ms": t.tiempos_ms,
    }
    return memoria.agregar_turno(persona_id, nuevo)


class PedidoValidar(BaseModel):
    persona_id: str
    turno_id: str
    texto_final: str


@app.post("/validar")
def api_validar(p: PedidoValidar):
    _memoria_o_404(p.persona_id)
    try:
        return memoria.validar(p.persona_id, p.turno_id, p.texto_final)
    except KeyError:
        raise HTTPException(404, f"No existe el turno {p.turno_id}")


@app.get("/audio/{nombre}")
def api_audio(nombre: str):
    ruta = (AUDIOS / nombre).resolve()
    if ruta.parent != AUDIOS.resolve() or ruta.suffix != ".wav" or not ruta.exists():
        raise HTTPException(404, "No existe ese audio")
    return FileResponse(ruta, media_type="audio/wav")


# --- Voz suelta (para el agente y WhatsApp) ------------------------------------

@app.post("/transcribir")
async def api_transcribir(audio: UploadFile = File(...), vocabulario: str | None = Form(None),
                          alternativa: bool = Form(True)):
    """Audio → transcripción limpia, hipótesis, confianza y nivel (alta/media/baja)."""
    datos = await audio.read()
    if not datos:
        raise HTTPException(400, "Audio vacío")
    palabras = [p.strip() for p in (vocabulario or "").split(",") if p.strip()] or None
    return transcribir(datos, audio.filename or "audio.webm", palabras, alternativa).a_dict()


class PedidoHablar(BaseModel):
    texto: str
    voz: str | None = None
    estilo: str | None = None
    formato: str = "wav"  # "wav" para reproducir en la web, "ogg" para nota de voz de WhatsApp


@app.post("/hablar")
def api_hablar(p: PedidoHablar):
    """Texto → audio. Devuelve el archivo directamente (audio/wav o audio/ogg)."""
    wav, ogg, tiempos = hablar(p.texto, voz=p.voz, estilo=p.estilo, nota_de_voz=p.formato == "ogg")
    cabeceras = {"X-Tiempos-ms": str(tiempos)}
    if p.formato == "ogg":
        return Response(ogg, media_type="audio/ogg", headers=cabeceras)
    return Response(wav, media_type="audio/wav", headers=cabeceras)


@app.post("/nota-de-voz")
async def api_nota_de_voz(audio: UploadFile = File(...)):
    """Cualquier audio → .ogg OPUS (formato de nota de voz de WhatsApp)."""
    return Response(a_nota_de_voz(await audio.read()), media_type="audio/ogg")

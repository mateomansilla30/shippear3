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
import interprete
import kapso
import memoria
import tts
from asr import Transcripcion, transcribir
from nota_voz import a_nota_de_voz, ruta_ffmpeg
from pipeline import Turno, hablar, turno as correr_turno

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
                    "voz_elevenlabs": config.TTS_ELEVEN_VOZ, "modelo_elevenlabs": config.TTS_ELEVEN_MODELO,
                    "voz_openai": config.TTS_OPENAI_VOZ},
            "claves": {"groq": bool(config.GROQ_API_KEY), "elevenlabs": bool(config.ELEVENLABS_API_KEY),
                       "openai": bool(config.OPENAI_API_KEY), "gemini": bool(config.GEMINI_API_KEY),
                       "kapso": bool(config.KAPSO_API_KEY)},
            "whatsapp": {"destino_configurado": bool(config.KAPSO_DESTINO), "ffmpeg": _hay_ffmpeg()}}


def _hay_ffmpeg() -> bool:
    try:
        ruta_ffmpeg()
        return True
    except RuntimeError:
        return False


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
                    alternativa: bool = Form(True), texto_demo: str | None = Form(None)):
    """Audio de la persona → lo que el sistema entendió + su voz. Se guarda en el historial.

    Devuelve un Turno {id, texto, audio_url, fecha, estado} más datos para depurar: texto_asr (Whisper tal cual,
    con reglas), confianza, nivel, hipotesis, correccion_usada y tiempos_ms.

    `texto_demo` (solo para audios de prueba de la demo): se usa ese texto en lugar de transcribir. Se le aplica la
    memoria igual y el turno queda marcado con interpretacion.fuente = "demo", para que nunca se confunda con una
    transcripción real.
    """
    m = _memoria_o_404(persona_id)
    datos = await audio.read()
    if not datos:
        raise HTTPException(400, "Audio vacío")

    usada = {}

    def interpretar(tr):
        texto, info = interprete.interpretar(tr, m)
        usada["c"] = info.get("correccion")
        usada["info"] = info
        return texto

    if texto_demo and texto_demo.strip():
        t = _turno_demo(texto_demo.strip(), m, usada)
    else:
        vocabulario = memoria.vocabulario_para_asr(m) if config.ASR_USAR_VOCABULARIO else None
        t = correr_turno(datos, audio.filename or "audio.webm", interpretar=interpretar,
                         vocabulario=vocabulario, alternativa=alternativa)
    turno_id = memoria.nuevo_turno_id()
    audio_url = None
    if t.wav:
        AUDIOS.mkdir(parents=True, exist_ok=True)
        (AUDIOS / f"{turno_id}.wav").write_bytes(t.wav)
        base = config.URL_PUBLICA or str(request.base_url).rstrip("/")
        audio_url = f"{base}/audio/{turno_id}.wav"
    nuevo = {
        "id": turno_id, "texto": t.texto_a_decir, "audio_url": audio_url, "fecha": memoria.ahora(),
        "estado": "pendiente",
        "texto_asr": t.transcripcion.texto, "confianza": t.transcripcion.confianza,
        "nivel": t.transcripcion.nivel, "hipotesis": t.transcripcion.hipotesis,
        "correccion_usada": usada.get("c"), "tiempos_ms": t.tiempos_ms,
        # De dónde salió el texto: memoria, llm o transcripción; y si el intérprete está seguro
        "interpretacion": {k: v for k, v in (usada.get("info") or {}).items() if k != "correccion"},
        # Qué proveedor de voz se usó y, si el principal falló, por qué (para depurar desde el navegador)
        "voz": {"proveedor": tts.ultimo_proveedor.get("nombre"), "errores": tts.ultimo_proveedor.get("errores")}
        if t.wav else None,
    }
    return memoria.agregar_turno(persona_id, nuevo)


def _turno_demo(texto_demo: str, m: dict, usada: dict) -> Turno:
    """Turno simulado para la demo: no transcribe; usa el texto dado, le aplica la memoria y lo dice con la voz."""
    texto, correccion = memoria.aplicar_correcciones(m, texto_demo)
    usada["c"] = correccion
    usada["info"] = {"fuente": "demo", "seguro": True, "memoria": bool(correccion)}
    tr = Transcripcion(texto=texto_demo, texto_crudo=texto_demo, hipotesis=[texto_demo], confianza=1.0,
                       nivel="alta", senales={"demo": True})
    wav, _, tiempos = hablar(texto)
    return Turno(transcripcion=tr, texto_a_decir=texto, wav=wav, tiempos_ms=tiempos)


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


class PedidoEnviar(BaseModel):
    persona_id: str
    turno_id: str
    destino: str | None = None  # si falta, KAPSO_DESTINO del .env


@app.post("/enviar")
def api_enviar(p: PedidoEnviar):
    """Manda por WhatsApp (Kapso) el texto de un turno como nota de voz, con la voz de la app."""
    m = _memoria_o_404(p.persona_id)
    turno = next((t for t in m.get("historial", []) if t["id"] == p.turno_id), None)
    if turno is None:
        raise HTTPException(404, f"No existe el turno {p.turno_id}")
    texto = turno.get("texto_final") or turno["texto"]
    # Si el texto no cambió, se reutiliza la voz ya generada en el turno (más rápido, sin gastar otra síntesis)
    wav_previo = AUDIOS / f"{p.turno_id}.wav"
    try:
        wav = wav_previo.read_bytes() if wav_previo.exists() and texto == turno["texto"] else tts.sintetizar(texto)
        mensaje_id = kapso.enviar_nota_de_voz(p.destino or config.KAPSO_DESTINO, a_nota_de_voz(wav))
    except RuntimeError as e:  # Kapso, ffmpeg o las voces (ErrorKapso también es RuntimeError)
        # 424 y no 502: los proxies (Easypanel/Traefik) reemplazan los 502 por su propia página de error y el front
        # pierde el motivo. Con 424 el mensaje llega al navegador.
        raise HTTPException(424, str(e))
    memoria.marcar_enviado(p.persona_id, p.turno_id, mensaje_id)
    return {"ok": True, "mensaje_id": mensaje_id, "texto": texto}


def _wav_de(carpeta, nombre: str) -> FileResponse:
    ruta = (carpeta / nombre).resolve()
    if ruta.parent != carpeta.resolve() or ruta.suffix != ".wav" or not ruta.exists():
        raise HTTPException(404, "No existe ese audio")
    return FileResponse(ruta, media_type="audio/wav")


@app.get("/audio/{nombre}")
def api_audio(nombre: str):
    """La voz de un turno (a lo que apunta audio_url)."""
    return _wav_de(AUDIOS, nombre)


@app.get("/audios-prueba/{nombre}")
def api_audio_prueba(nombre: str):
    """Audios de prueba de S-DiverSe para la demo. Se copian a mano a voz/audios_prueba/ (no están en el repo)."""
    return _wav_de(config.AUDIOS_PRUEBA, nombre)


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

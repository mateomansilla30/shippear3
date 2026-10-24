"""Texto a voz. Proveedor principal + respaldo, cada uno con un tope de tiempo que se cumple siempre.

Por defecto: OpenAI (gpt-4o-mini-tts), rápido; si falla o tarda más que TTS_TIMEOUT_S, Gemini TTS.
Se cambia en voz/.env con TTS_PROVEEDOR y TTS_RESPALDO ("openai" | "gemini" | "ninguno").

Uso:
    from tts import sintetizar
    wav = sintetizar("Hola, quiero hablar con María")   # bytes WAV
"""
from __future__ import annotations

import base64
import io
import time
import wave
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturoTimeout

import config

_clientes: dict = {}
_hilos = ThreadPoolExecutor(max_workers=4)
ultimo_proveedor: dict = {"nombre": None, "ms": None, "errores": []}


def _a_wav(datos: bytes, frecuencia: int = 24000) -> bytes:
    """Si llega PCM crudo (16 bit, mono), le agrega el encabezado WAV."""
    if datos[:4] == b"RIFF":
        return datos
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(frecuencia)
        w.writeframes(datos)
    return buf.getvalue()


def _openai(texto: str, voz: str | None, estilo: str | None) -> bytes:
    from openai import OpenAI
    if "openai" not in _clientes:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("Falta OPENAI_API_KEY en voz/.env")
        _clientes["openai"] = OpenAI(api_key=config.OPENAI_API_KEY, max_retries=1, timeout=config.TTS_TIMEOUT_S)
    r = _clientes["openai"].audio.speech.create(
        model=config.TTS_OPENAI_MODELO, voice=voz or config.TTS_OPENAI_VOZ, input=texto,
        instructions=estilo or config.TTS_ESTILO, response_format="pcm")
    # PCM crudo (24 kHz, 16 bit, mono): armamos el WAV nosotros porque el WAV de OpenAI trae el largo sin completar
    return _a_wav(r.read())


def _gemini(texto: str, voz: str | None, estilo: str | None) -> bytes:
    from google import genai
    from google.genai import types
    if "gemini" not in _clientes:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("Falta GEMINI_API_KEY en voz/.env")
        _clientes["gemini"] = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=int(config.TTS_TIMEOUT_S * 1000),
                                           retry_options=types.HttpRetryOptions(attempts=1)))
    interaccion = _clientes["gemini"].interactions.create(
        model=config.TTS_GEMINI_MODELO,
        input=[{"type": "user_input", "content": [{
            "type": "text", "text": texto,
            "annotations": [{"type": "speech_metadata", "style": estilo or config.TTS_ESTILO}]}]}],
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": voz or config.TTS_GEMINI_VOZ}]},
    )
    datos = interaccion.output_audio.data
    return _a_wav(base64.b64decode(datos) if isinstance(datos, str) else datos)


_ELEVEN_CON_IDIOMA = {"eleven_flash_v2_5", "eleven_turbo_v2_5"}  # modelos que aceptan language_code


_ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech"
_eleven_http = None


def _eleven_cliente():
    """Una sola conexión reutilizada con ElevenLabs: evita abrir una conexión segura nueva en cada frase."""
    global _eleven_http
    if _eleven_http is None:
        import httpx
        if not config.ELEVENLABS_API_KEY:
            raise RuntimeError("Falta ELEVENLABS_API_KEY en voz/.env")
        _eleven_http = httpx.Client(headers={"xi-api-key": config.ELEVENLABS_API_KEY}, timeout=config.TTS_TIMEOUT_S)
    return _eleven_http


def _eleven_cuerpo(texto: str) -> dict:
    cuerpo = {
        "text": texto,
        "model_id": config.TTS_ELEVEN_MODELO,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": config.TTS_ELEVEN_VELOCIDAD},
    }
    if config.TTS_ELEVEN_MODELO in _ELEVEN_CON_IDIOMA:
        cuerpo["language_code"] = "es"
    return cuerpo


def _elevenlabs(texto: str, voz: str | None, estilo: str | None) -> bytes:
    """ElevenLabs. `voz` es un voice_id (de la cuenta o de la biblioteca pública). `estilo` no aplica."""
    r = _eleven_cliente().post(f"{_ELEVEN_URL}/{voz or config.TTS_ELEVEN_VOZ}",
                               params={"output_format": "pcm_24000"}, json=_eleven_cuerpo(texto))
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs respondió {r.status_code}: {r.text[:300]}")
    return _a_wav(r.content)  # PCM 24 kHz 16 bit mono → WAV


def abrir_stream_elevenlabs(texto: str, voz: str | None = None):
    """Abre el streaming de ElevenLabs y devuelve (iterador de fragmentos MP3, cerrar).

    Si ElevenLabs responde con error, lanza RuntimeError ANTES de entregar nada, así quien llama puede usar el
    respaldo. La voz empieza a sonar en el navegador con los primeros fragmentos, sin esperar el audio entero.
    """
    texto = " ".join(str(texto).split())
    if not texto:
        raise ValueError("No hay texto para decir")
    cliente = _eleven_cliente()
    pedido = cliente.build_request("POST", f"{_ELEVEN_URL}/{voz or config.TTS_ELEVEN_VOZ}/stream",
                                   params={"output_format": "mp3_44100_64"}, json=_eleven_cuerpo(texto))
    r = cliente.send(pedido, stream=True)
    if r.status_code != 200:
        detalle = r.read()[:300]
        r.close()
        raise RuntimeError(f"ElevenLabs respondió {r.status_code}: {detalle!r}")
    ultimo_proveedor.update(nombre="elevenlabs", errores=[])
    return r.iter_bytes(), r.close


def calentar() -> None:
    """La primera frase con una voz tarda varios segundos más (ElevenLabs la carga): se la pide al arrancar."""
    if config.TTS_PROVEEDOR == "elevenlabs" and config.ELEVENLABS_API_KEY:
        try:
            _elevenlabs("Hola.", None, None)
        except Exception:
            pass


_PROVEEDORES = {"elevenlabs": _elevenlabs, "openai": _openai, "gemini": _gemini}


def _con_tope(proveedor: str, texto: str, voz: str | None, estilo: str | None) -> bytes:
    """Corre el proveedor en un hilo y deja de esperarlo al pasar el tope, aunque la API no corte."""
    futuro = _hilos.submit(_PROVEEDORES[proveedor], texto, voz, estilo)
    return futuro.result(timeout=config.TTS_TIMEOUT_S + 2)


def sintetizar(texto: str, voz: str | None = None, estilo: str | None = None) -> bytes:
    """Devuelve el audio en WAV. `voz` es del proveedor principal; el respaldo usa su voz por defecto.

    `estilo` describe cómo decirlo (no se lee en voz alta).
    """
    texto = " ".join(str(texto).split())
    if not texto:
        raise ValueError("No hay texto para decir")
    orden = [config.TTS_PROVEEDOR] + ([config.TTS_RESPALDO] if config.TTS_RESPALDO in _PROVEEDORES else [])
    errores = []
    for i, proveedor in enumerate(orden):
        t0 = time.perf_counter()
        try:
            wav = _con_tope(proveedor, texto, voz if i == 0 else None, estilo)
            ultimo_proveedor.update(nombre=proveedor, ms=round((time.perf_counter() - t0) * 1000), errores=errores)
            return wav
        except FuturoTimeout:
            errores.append(f"{proveedor}: no respondió en {config.TTS_TIMEOUT_S:.0f} s")
        except Exception as e:
            errores.append(f"{proveedor}: {type(e).__name__}: {str(e)[:200]}")
    raise RuntimeError("Ningún proveedor de voz respondió. " + " | ".join(errores))


def duracion_wav(wav: bytes) -> float:
    with wave.open(io.BytesIO(wav)) as w:
        return w.getnframes() / w.getframerate()

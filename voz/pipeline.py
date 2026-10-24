"""Recorrido completo de un turno: audio de la persona → texto → (interpretación) → voz clara.

La interpretación (LLM corrector + agente con memoria) la arma otra parte del equipo: se enchufa con el
parámetro `interpretar`, una función que recibe la Transcripcion y devuelve el texto a decir.
Mientras no exista, se dice la transcripción limpia.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from asr import Transcripcion, transcribir
from nota_voz import a_nota_de_voz
from tts import duracion_wav, sintetizar


@dataclass
class Turno:
    transcripcion: Transcripcion
    texto_a_decir: str
    wav: bytes | None = None
    ogg: bytes | None = None
    tiempos_ms: dict = field(default_factory=dict)

    def resumen(self) -> dict:
        return {
            "transcripcion": self.transcripcion.a_dict(),
            "texto_a_decir": self.texto_a_decir,
            "duracion_respuesta_s": round(duracion_wav(self.wav), 2) if self.wav else None,
            "tiempos_ms": self.tiempos_ms,
        }


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)


def hablar(texto: str, voz: str | None = None, estilo: str | None = None,
           nota_de_voz: bool = False) -> tuple[bytes, bytes | None, dict]:
    """Texto → WAV (y .ogg si se pide). Devuelve (wav, ogg, tiempos_ms)."""
    tiempos = {}
    t0 = time.perf_counter()
    wav = sintetizar(texto, voz=voz, estilo=estilo)
    tiempos["tts"] = _ms(t0)
    ogg = None
    if nota_de_voz:
        t1 = time.perf_counter()
        ogg = a_nota_de_voz(wav)
        tiempos["ogg"] = _ms(t1)
    return wav, ogg, tiempos


def turno(audio: bytes, nombre: str = "audio.wav", *,
          interpretar: Callable[[Transcripcion], str] | None = None,
          vocabulario: list[str] | None = None, alternativa: bool = True,
          voz: str | None = None, nota_de_voz: bool = False, sintetizar_voz: bool = True) -> Turno:
    """Un turno completo, midiendo cuánto tarda cada etapa."""
    t0 = time.perf_counter()
    tr = transcribir(audio, nombre, vocabulario=vocabulario, alternativa=alternativa)
    tiempos = dict(tr.tiempos_ms)

    t1 = time.perf_counter()
    texto = interpretar(tr) if interpretar else tr.texto
    tiempos["interpretar"] = _ms(t1)

    wav = ogg = None
    if sintetizar_voz and texto.strip():
        wav, ogg, t_voz = hablar(texto, voz=voz, nota_de_voz=nota_de_voz)
        tiempos.update(t_voz)
    tiempos["total"] = _ms(t0)
    return Turno(transcripcion=tr, texto_a_decir=texto, wav=wav, ogg=ogg, tiempos_ms=tiempos)

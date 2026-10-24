"""Transcripción con Groq (Whisper) + reglas anti-alucinación + confianza.

Uso:
    from asr import transcribir
    t = transcribir(open("audio.wav", "rb").read(), "audio.wav")
    t.texto, t.confianza, t.nivel, t.hipotesis
"""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturoTimeout
from dataclasses import asdict, dataclass, field

import jiwer
from openai import OpenAI

import config
from reglas import normalizar, postprocesar_reglas

_cliente: OpenAI | None = None
_hilos = ThreadPoolExecutor(max_workers=4)


def _groq() -> OpenAI:
    global _cliente
    if _cliente is None:
        if not config.GROQ_API_KEY:
            raise RuntimeError("Falta GROQ_API_KEY en voz/.env")
        _cliente = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_URL, max_retries=1, timeout=20)
    return _cliente


@dataclass
class Segmento:
    inicio: float
    fin: float
    texto: str
    avg_logprob: float
    no_speech_prob: float
    compression_ratio: float


@dataclass
class Transcripcion:
    texto: str                      # transcripción limpia (con reglas): la que se usa
    texto_crudo: str                # Whisper tal cual
    hipotesis: list[str]            # hipótesis limpias, la principal primero (para el LLM corrector)
    confianza: float                # 0 a 1
    nivel: str                      # "alta" | "media" | "baja"
    senales: dict                   # de dónde sale la confianza
    segmentos: list[Segmento] = field(default_factory=list)
    duracion_audio_s: float = 0.0
    tiempos_ms: dict = field(default_factory=dict)

    def a_dict(self) -> dict:
        return asdict(self)


def _pedir(audio: bytes, nombre: str, modelo: str, prompt: str | None):
    """Una transcripción con segmentos y sus métricas (verbose_json)."""
    t0 = time.perf_counter()
    kw = dict(file=(nombre, audio), model=modelo, language=config.ASR_IDIOMA,
              response_format="verbose_json", timestamp_granularities=["segment"], temperature=0.0)
    if prompt:
        kw["prompt"] = prompt
    r = _groq().audio.transcriptions.create(**kw)
    return r, (time.perf_counter() - t0) * 1000


def _segmentos(r) -> list[Segmento]:
    return [Segmento(inicio=s.start, fin=s.end, texto=s.text.strip(), avg_logprob=s.avg_logprob,
                     no_speech_prob=s.no_speech_prob, compression_ratio=s.compression_ratio)
            for s in (r.segments or [])]


def calcular_confianza(segmentos: list[Segmento], texto_crudo: str, texto_limpio: str,
                       alternativa_limpia: str | None = None) -> tuple[float, dict]:
    """Confianza de 0 a 1 a partir de señales que da Whisper y del acuerdo entre hipótesis.

    - prob_tokens: exp(avg_logprob promedio, ponderado por duración). Qué tan seguro estaba Whisper.
    - no_speech: probabilidad de que no haya habla (silencio, ruido).
    - acuerdo: 1 - WER entre la hipótesis principal y la alternativa. Si dos modelos coinciden, es más confiable.
    - borrado_por_reglas: fracción de palabras que las reglas eliminaron (bucles). Mucho borrado = Whisper alucinó.
    - bucle: algún segmento con compression_ratio > 2,4 (texto muy repetitivo).
    """
    if not segmentos or not normalizar(texto_limpio):
        return 0.0, {"motivo": "sin texto"}
    dur = [max(s.fin - s.inicio, 0.01) for s in segmentos]
    total = sum(dur)
    prob_tokens = math.exp(sum(d * s.avg_logprob for d, s in zip(dur, segmentos)) / total)
    no_speech = sum(d * s.no_speech_prob for d, s in zip(dur, segmentos)) / total
    bucle = max(s.compression_ratio for s in segmentos) > 2.4
    n_crudo = len(normalizar(texto_crudo).split())
    n_limpio = len(normalizar(texto_limpio).split())
    borrado = 1 - n_limpio / n_crudo if n_crudo else 0.0

    acuerdo = None
    if alternativa_limpia is not None:
        a, b = normalizar(texto_limpio), normalizar(alternativa_limpia)
        acuerdo = 1.0 if a == b else max(0.0, 1 - jiwer.wer(a, b)) if a and b else 0.0

    base = prob_tokens if acuerdo is None else 0.6 * prob_tokens + 0.4 * acuerdo
    confianza = base * (1 - no_speech) * (1 - borrado) * (0.5 if bucle else 1.0)
    senales = dict(prob_tokens=round(prob_tokens, 3), no_speech=round(no_speech, 3),
                   acuerdo=None if acuerdo is None else round(acuerdo, 3),
                   borrado_por_reglas=round(borrado, 3), bucle=bucle)
    return round(min(max(confianza, 0.0), 1.0), 3), senales


def nivel_de(confianza: float) -> str:
    if confianza >= config.CONFIANZA_ALTA:
        return "alta"
    if confianza >= config.CONFIANZA_MEDIA:
        return "media"
    return "baja"


def transcribir(audio: bytes, nombre: str = "audio.wav", vocabulario: list[str] | None = None,
                alternativa: bool = True) -> Transcripcion:
    """Transcribe un audio (wav, mp3, m4a, ogg, webm...).

    vocabulario: nombres o palabras que la persona usa (contactos, medicamentos). Van como `prompt` a Whisper
    para que los escriba bien. Usar con moderación: Whisper puede "oírlos" donde no están.
    alternativa: pide en paralelo una segunda transcripción a otro modelo (hipótesis alternativa + acuerdo).
    """
    t0 = time.perf_counter()
    prompt = ("Vocabulario: " + ", ".join(vocabulario) + ".") if vocabulario else None
    fut_p = _hilos.submit(_pedir, audio, nombre, config.ASR_MODELO, prompt)
    fut_a = _hilos.submit(_pedir, audio, nombre, config.ASR_MODELO_ALTERNATIVO, prompt) if alternativa else None

    r, ms_p = fut_p.result()
    tiempos = {"asr_principal": round(ms_p)}
    alt_texto = None
    if fut_a is not None:
        try:
            r_alt, ms_a = fut_a.result(timeout=config.ASR_ESPERA_ALTERNATIVA_S)
            alt_texto = " ".join(r_alt.text.split())
            tiempos["asr_alternativa"] = round(ms_a)
        except FuturoTimeout:
            tiempos["asr_alternativa"] = "descartada por lenta"
        except Exception as e:  # la alternativa es opcional: si falla, se sigue
            tiempos["asr_alternativa"] = f"error: {type(e).__name__}"

    crudo = " ".join((r.text or "").split())
    limpio = postprocesar_reglas(crudo)
    alt_limpia = postprocesar_reglas(alt_texto) if alt_texto else None
    hipotesis = [limpio] + ([alt_limpia] if alt_limpia and normalizar(alt_limpia) != normalizar(limpio) else [])
    segs = _segmentos(r)
    confianza, senales = calcular_confianza(segs, crudo, limpio, alt_limpia)
    tiempos["asr_total"] = round((time.perf_counter() - t0) * 1000)
    return Transcripcion(texto=limpio, texto_crudo=crudo, hipotesis=hipotesis, confianza=confianza,
                         nivel=nivel_de(confianza), senales=senales, segmentos=segs,
                         duracion_audio_s=round(getattr(r, "duration", 0) or 0, 2), tiempos_ms=tiempos)

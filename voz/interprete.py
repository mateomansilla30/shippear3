"""Interpretación: de lo que transcribió Whisper a lo que la persona quiso decir (LLM + memoria de la persona).

Orden:
1. Si la memoria tiene una corrección validada parecida, se usa (aprendizaje con el uso).
2. Si la confianza es baja, NO se adivina: se devuelve la transcripción y la app pide repetir.
3. Si no, un LLM corrige errores de reconocimiento usando contactos, vocabulario y correcciones de la persona.
   Salvaguarda: si el LLM cambia demasiado el largo, se descarta su respuesta.
"""
from __future__ import annotations

import json

import config
import memoria
from asr import Transcripcion

SISTEMA = """Sos el intérprete de Voz Clara, un asistente para personas con habla atípica (disartria por ELA, Parkinson o secuelas de ACV). Recibís lo que transcribió el reconocimiento de voz (a veces con versiones alternativas) y datos de la persona. Escribí lo que la persona quiso decir, para mandarlo como mensaje.

Reglas:
- Corregí solo errores de reconocimiento evidentes: palabras que suenan parecido, nombres de sus contactos, palabras de su vocabulario.
- Usá las correcciones anteriores de la persona: si dice algo parecido, probablemente quiere decir lo mismo.
- No agregues información que no esté en la transcripción, no resumas y no cambies el sentido. Respetá su forma de hablar (voseo, muletillas).
- Si no se entiende qué quiso decir, no adivines: devolvé la transcripción tal cual con "seguro": false.
- Respondé solo con JSON: {"mensaje": "...", "seguro": true o false}"""

_cliente = None


def _openai():
    global _cliente
    if _cliente is None:
        from openai import OpenAI
        if not config.OPENAI_API_KEY:
            raise RuntimeError("Falta OPENAI_API_KEY en voz/.env")
        _cliente = OpenAI(api_key=config.OPENAI_API_KEY, max_retries=1, timeout=10)
    return _cliente


def _contexto(tr: Transcripcion, m: dict) -> str:
    persona = m.get("persona", {})
    contactos = ", ".join(f"{c['nombre']} ({c.get('relacion', '')})" for c in m.get("contactos", []) if c.get("nombre"))
    correcciones = "\n".join(f'- Whisper escribió "{c["original"]}" → quiso decir "{c["texto"]}"'
                             for c in m.get("correcciones", [])[:8])
    alternativas = "\n".join(f"- {h}" for h in tr.hipotesis[1:]) or "- (ninguna)"
    return (f"Persona: {persona.get('nombre', '')}. {persona.get('notas', '')}\n"
            f"Contactos: {contactos or '(ninguno)'}\n"
            f"Vocabulario propio: {', '.join(m.get('vocabulario', [])) or '(ninguno)'}\n"
            f"Correcciones anteriores:\n{correcciones or '- (ninguna)'}\n\n"
            f"Transcripción (confianza {tr.confianza:.2f}): {tr.texto}\n"
            f"Versiones alternativas:\n{alternativas}")


def _con_llm(tr: Transcripcion, m: dict) -> tuple[str, bool]:
    r = _openai().chat.completions.create(
        model=config.LLM_MODELO, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": _contexto(tr, m)}])
    datos = json.loads(r.choices[0].message.content or "{}")
    return str(datos.get("mensaje", "")).strip(), bool(datos.get("seguro", False))


def interpretar(tr: Transcripcion, m: dict) -> tuple[str, dict]:
    """Devuelve (texto a mostrar y decir, info sobre cómo se obtuvo)."""
    if not tr.texto.strip():
        return "No te entendí. ¿Podés repetirlo?", {"fuente": "nada", "seguro": False}

    texto, correccion = memoria.aplicar_correcciones(m, tr.texto)
    if correccion:
        return texto, {"fuente": "memoria", "seguro": True, "correccion": correccion}

    if tr.nivel == "baja" or not config.INTERPRETAR_CON_LLM:
        return tr.texto, {"fuente": "transcripcion", "seguro": tr.nivel != "baja"}

    try:
        mensaje, seguro = _con_llm(tr, m)
    except Exception as e:
        return tr.texto, {"fuente": "transcripcion", "seguro": True, "error_llm": f"{type(e).__name__}: {str(e)[:150]}"}
    n_base, n_llm = len(tr.texto.split()), len(mensaje.split())
    if not mensaje or n_llm < 0.5 * n_base or n_llm > 1.5 * n_base + 3:
        return tr.texto, {"fuente": "transcripcion", "seguro": True, "llm_descartado": mensaje}
    return mensaje, {"fuente": "llm" if mensaje != tr.texto else "transcripcion", "seguro": seguro}

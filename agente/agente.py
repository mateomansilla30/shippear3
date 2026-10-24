"""Agente de Voz Clara: maneja la memoria de cada persona, la usa en cada turno y aprende de lo validado.

Entrada: lo que transcribió el pipeline de voz. Salida: qué entendió, qué quiere hacer la persona y si
hay que decirlo, confirmarlo u ofrecer opciones. Contrato completo en AGENTE.md.
"""

import json
import os
import re
import sqlite3
import unicodedata
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from difflib import SequenceMatcher

DB = os.environ.get("AGENTE_DB", "agente.db")
LLM_MODELO = os.environ.get("AGENTE_LLM_MODELO", "gpt-4.1-mini")
LLM_URL = os.environ.get("AGENTE_LLM_URL")  # None = OpenAI. Groq: https://api.groq.com/openai/v1
LLM_KEY_ENV = os.environ.get("AGENTE_LLM_KEY_ENV", "OPENAI_API_KEY")

# Umbrales de confianza para actuar / confirmar / ofrecer opciones.
# ponytail: valores a ojo; ajustarlos con hablantes de validación, nunca con los de test.
CONFIANZA_ALTA = 0.85
CONFIANZA_BAJA = 0.5
EJEMPLOS_MAX = 5
SIMILITUD_MIN = 0.5
TURNOS_CONTEXTO = 3
HISTORIAL_MAX = 200
SUGERENCIA_MIN_VECES = 3


def ahora():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- memoria

# ponytail: un JSON por persona en SQLite. Alcanza para cientos de turnos por persona; pasar a
# tablas si hace falta consultar entre personas (por ejemplo, para entrenar un corrector general).
@contextmanager
def _db():
    con = sqlite3.connect(DB)
    try:
        with con:  # commit al salir
            con.execute("CREATE TABLE IF NOT EXISTS personas (id TEXT PRIMARY KEY, datos TEXT NOT NULL)")
            yield con
    finally:
        con.close()


def _vacia(persona):
    return {"persona": persona, "contactos": [], "vocabulario": [], "ejemplos": [], "historial": [],
            "descartadas": []}


def cargar(persona_id):
    with _db() as con:
        fila = con.execute("SELECT datos FROM personas WHERE id = ?", (persona_id,)).fetchone()
    if not fila:
        raise KeyError(persona_id)
    return json.loads(fila[0])


def guardar(m):
    with _db() as con:
        con.execute("INSERT OR REPLACE INTO personas (id, datos) VALUES (?, ?)",
                    (m["persona"]["id"], json.dumps(m, ensure_ascii=False)))
    return m


def listar_personas():
    with _db() as con:
        filas = con.execute("SELECT datos FROM personas").fetchall()
    return [json.loads(f[0])["persona"] for f in filas]


def crear_persona(nombre, notas=""):
    return guardar(_vacia({"id": str(uuid.uuid4()), "nombre": nombre, "notas": notas}))["persona"]


def para_front(m):
    """Lo que ve el front: los ejemplos corregidos son 'Lo que aprendí'."""
    return {
        "persona": m["persona"],
        "contactos": m["contactos"],
        "vocabulario": m["vocabulario"],
        "correcciones": [{"original": e["texto_asr"], "texto": e["texto_final"], "fecha": e["fecha"]}
                         for e in m["ejemplos"] if e["corregido"]],
        "historial": m["historial"],
        "sugerencias": sugerencias(m),
    }


def editar(persona_id, persona, contactos, vocabulario, correcciones):
    """PUT /memoria: la persona edita su perfil o borra correcciones aprendidas."""
    m = cargar(persona_id)
    quedan = {(c["original"], c["texto"]) for c in correcciones}
    m["ejemplos"] = [e for e in m["ejemplos"]
                     if not e["corregido"] or (e["texto_asr"], e["texto_final"]) in quedan]
    m.update(persona={**persona, "id": persona_id}, contactos=contactos, vocabulario=vocabulario)
    return guardar(m)


# ---------------------------------------------------------------- contexto

def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^\w\s]", " ", texto).split())


def ejemplos_parecidos(m, texto_asr, k=EJEMPLOS_MAX):
    """Las validaciones de esta persona más parecidas a lo que se escuchó ahora.

    ponytail: similitud de texto con difflib, recorre todos los ejemplos (O(n)). Si hace falta
    similitud fonética o hay miles de ejemplos, cambiar por embeddings.
    """
    objetivo = normalizar(texto_asr)
    puntuados = []
    for e in m["ejemplos"]:
        s = SequenceMatcher(None, objetivo, normalizar(e["texto_asr"])).ratio()
        if s >= SIMILITUD_MIN:
            puntuados.append((s, e["corregido"], e["usos"], e))
    puntuados.sort(key=lambda t: t[:3], reverse=True)
    return [t[3] for t in puntuados[:k]]


SISTEMA = """Sos el agente de Voz Clara, un asistente para personas con habla atípica (disartria por ELA, Parkinson, ACV u otras causas).
Recibís lo que un sistema de reconocimiento de voz transcribió de lo que dijo la persona y tenés que entender qué quiso decir.

Reglas:
- Hacé ediciones mínimas. No agregues ideas que no estén en la transcripción ni parafrasees.
- Usá la memoria de la persona (ejemplos validados, contactos, palabras frecuentes) SOLO para resolver palabras dudosas. Si un ejemplo validado se parece, seguí cómo lo corrigió la persona.
- Los ejemplos validados mandan sobre la versión corregida automática: si la persona usa un término (por ejemplo, uno médico), respetalo.
- intencion es "mensaje" solo si la persona pide mandarle algo a alguien ("mandale a María que..."); si no, "decir".
- Si es un mensaje, destinatario es el nombre del contacto tal como figura en la lista, o null si no está; mensaje es el texto a enviar.
- confianza (0 a 1): qué tan seguro estás de haber entendido. Bajala si la transcripción es confusa o contradictoria.
- opciones: si dudás, hasta 3 interpretaciones alternativas distintas de texto; si no, [].
- proponer_memoria: si la persona nombra a alguien con su relación ("mi nieto Tomás") o un término propio (medicamento, lugar, nombre) que NO está en sus contactos ni en sus palabras frecuentes, proponelo para que lo guarde. Solo lo que dijo claramente; si no hay nada, [].

Respondé solo un JSON: {"texto": str, "intencion": "decir"|"mensaje", "destinatario": str|null, "mensaje": str|null, "confianza": float, "opciones": [str], "proponer_memoria": [{"tipo": "contacto", "valor": str, "relacion": str} | {"tipo": "palabra", "valor": str}]}"""


def armar_mensajes(m, texto_asr, texto_corregido):
    p = m["persona"]
    partes = [f"Persona: {p['nombre']}." + (f" {p['notas']}" if p.get("notas") else "")]
    if m["contactos"]:
        partes.append("Contactos: " + "; ".join(
            f"{c['nombre']} ({c.get('relacion') or 'sin relación'})" for c in m["contactos"]))
    if m["vocabulario"]:
        partes.append("Palabras frecuentes: " + ", ".join(m["vocabulario"]))
    ejemplos = ejemplos_parecidos(m, texto_asr)
    if ejemplos:
        partes.append("Ejemplos validados por la persona (transcripción → lo que quiso decir):\n" + "\n".join(
            f"- «{e['texto_asr']}» → «{e['texto_final']}»" for e in ejemplos))
    recientes = [t for t in m["historial"][:TURNOS_CONTEXTO] if t["estado"] != "pendiente"]
    if recientes:
        partes.append("Lo último que dijo (más reciente primero):\n" + "\n".join(
            f"- {t.get('texto_final') or t['texto']}" for t in recientes))
    partes.append(f"Transcripción: «{texto_asr}»")
    if texto_corregido and texto_corregido != texto_asr:
        partes.append(f"Versión corregida automática (sin memoria de la persona): «{texto_corregido}»")
    return [{"role": "system", "content": SISTEMA}, {"role": "user", "content": "\n\n".join(partes)}], ejemplos


_cliente = None


def llamar_llm(mensajes):
    global _cliente
    if _cliente is None:
        from openai import OpenAI
        _cliente = OpenAI(api_key=os.environ[LLM_KEY_ENV], base_url=LLM_URL, max_retries=2, timeout=20)
    r = _cliente.chat.completions.create(model=LLM_MODELO, messages=mensajes, temperature=0,
                                         response_format={"type": "json_object"})
    return r.choices[0].message.content


def interpretar(respuesta, texto_respaldo, contactos):
    """Parsea la respuesta del LLM. Si viene rota, devuelve el texto de respaldo con confianza baja."""
    try:
        r = json.loads(respuesta)
        texto = str(r.get("texto") or "").strip()
        if not texto:
            raise ValueError("sin texto")
    except (ValueError, TypeError, json.JSONDecodeError):
        return {"texto": texto_respaldo, "intencion": "decir", "destinatario": None, "mensaje": None,
                "confianza": 0.0, "opciones": [], "propuestas": []}
    nombres = {c["nombre"].lower(): c["nombre"] for c in contactos}
    destinatario = nombres.get(str(r.get("destinatario") or "").strip().lower())
    intencion = "mensaje" if r.get("intencion") == "mensaje" else "decir"
    try:
        confianza = min(1.0, max(0.0, float(r.get("confianza", 0))))
    except (TypeError, ValueError):
        confianza = 0.0
    opciones = [o.strip() for o in r.get("opciones") or [] if isinstance(o, str) and o.strip()]
    opciones = [o for o in dict.fromkeys(opciones) if o != texto][:3]
    propuestas = []
    for p in r.get("proponer_memoria") or []:
        if isinstance(p, dict) and p.get("tipo") in ("contacto", "palabra") and str(p.get("valor") or "").strip():
            propuestas.append({"tipo": p["tipo"], "valor": str(p["valor"]).strip(),
                               "relacion": str(p.get("relacion") or "").strip() if p["tipo"] == "contacto" else ""})
    return {"texto": texto, "intencion": intencion, "destinatario": destinatario,
            "mensaje": (r.get("mensaje") or texto) if intencion == "mensaje" else None,
            "confianza": confianza, "opciones": opciones, "propuestas": propuestas[:3]}


def decidir(r):
    """decir: lo dice directo. confirmar: pregunta antes. opciones: muestra alternativas para tocar."""
    if r["intencion"] == "mensaje":
        return "confirmar"  # nunca manda nada afuera sin que la persona diga que sí
    if r["confianza"] >= CONFIANZA_ALTA:
        return "decir"
    if r["confianza"] < CONFIANZA_BAJA and r["opciones"]:
        return "opciones"
    return "confirmar"


# ---------------------------------------------------------------- turno y aprendizaje

def procesar_turno(persona_id, texto_asr, texto_corregido=None, llm=llamar_llm):
    """Lo llama el pipeline de voz después de transcribir. Devuelve el turno para el front."""
    m = cargar(persona_id)
    respaldo = texto_corregido or texto_asr
    if not texto_asr.strip():
        r = interpretar("", respaldo, m["contactos"])
    else:
        mensajes, _ = armar_mensajes(m, texto_asr, texto_corregido)
        try:
            r = interpretar(llm(mensajes), respaldo, m["contactos"])
        except Exception:
            r = interpretar("", respaldo, m["contactos"])  # sin LLM: se pide confirmación
    turno = {"id": str(uuid.uuid4()), "fecha": ahora(), "estado": "pendiente", "texto_asr": texto_asr,
             **r, "accion": decidir(r)}
    m["historial"] = [turno, *m["historial"]][:HISTORIAL_MAX]
    guardar(m)
    return turno


def validar(persona_id, turno_id, texto_final):
    """La persona dijo 'sí' (texto_final == texto) o corrigió. Las dos cosas se guardan como ejemplo."""
    m = cargar(persona_id)
    turno = next((t for t in m["historial"] if t["id"] == turno_id), None)
    if turno is None:
        raise KeyError(turno_id)
    texto_final = texto_final.strip()
    corregido = texto_final != turno["texto"].strip()
    turno.update(estado="corregido" if corregido else "validado", texto_final=texto_final)

    previo = next((e for e in m["ejemplos"] if normalizar(e["texto_asr"]) == normalizar(turno["texto_asr"])
                   and e["texto_final"] == texto_final), None)
    if previo:
        previo["usos"] += 1
        previo["corregido"] = previo["corregido"] or corregido
    elif turno["texto_asr"].strip():
        m["ejemplos"].insert(0, {"texto_asr": turno["texto_asr"], "texto_final": texto_final,
                                 "corregido": corregido, "usos": 1, "fecha": ahora()})
    return guardar(m)


def sugerencias(m):
    """Lo que el agente propone guardar; la persona acepta o descarta. Dos fuentes:

    1. Lo que el LLM detectó en un turno que la persona validó tal cual ("mi nieto Tomás").
       Si lo corrigió, la propuesta pudo salir de un error y no se usa.
    2. Nombres propios que aparecen en varios turnos validados (tipo None: la persona elige).
       ponytail: heurística de mayúsculas en medio de la frase.
    """
    conocidas = {normalizar(c["nombre"]) for c in m["contactos"]}
    conocidas |= {normalizar(v) for v in m["vocabulario"]} | {normalizar(d) for d in m["descartadas"]}
    lista = []

    def agregar(s):
        if normalizar(s["valor"]) not in conocidas:
            conocidas.add(normalizar(s["valor"]))
            lista.append(s)

    for t in m["historial"]:
        if t["estado"] == "validado":
            for p in t.get("propuestas", []):
                agregar(p)

    cuenta = Counter()
    for t in m["historial"]:
        if t["estado"] == "pendiente":
            continue
        palabras = re.findall(r"[\wÁÉÍÓÚÑáéíóúñü]+|[.!?]", t.get("texto_final") or t["texto"])
        for previa, palabra in zip(["."] + palabras, palabras):
            if palabra[:1].isupper() and previa not in ".!?":
                cuenta[palabra] += 1
    for palabra, n in cuenta.most_common():
        if n >= SUGERENCIA_MIN_VECES:
            agregar({"tipo": None, "valor": palabra, "relacion": ""})
    return lista


def responder_sugerencia(persona_id, valor, tipo, relacion=""):
    """tipo: 'contacto', 'palabra' o 'descartar' (no se vuelve a sugerir)."""
    m = cargar(persona_id)
    if tipo == "contacto":
        m["contactos"].append({"nombre": valor, "relacion": relacion})
    elif tipo == "palabra":
        m["vocabulario"].append(valor)
    else:
        m["descartadas"].append(valor)
    return guardar(m)

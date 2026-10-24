"""Normalización de texto y reglas anti-alucinación.

Copiado del notebook reconocimiento-voz/notebooks/notebook_sdiverse_whisper.ipynb (sección 3),
para que el pipeline en vivo limpie exactamente igual que en la evaluación.
"""
import re
import unicodedata

import jiwer
from num2words import num2words

def _num_a_palabras(m):
    s = m.group(0).replace(".", "")
    try:
        return " " + num2words(int(s), lang="es") + " "
    except Exception:
        return " " + s + " "

def normalizar(texto, quitar_tildes=False):
    t = unicodedata.normalize("NFC", str(texto)).lower()
    t = t.replace("<unk>", " ")
    t = re.sub(r"\d{1,3}(?:\.\d{3})+(?!\d)|\d+", _num_a_palabras, t)
    t = re.sub(r"[^\w\s]|_", " ", t)
    if quitar_tildes:
        t = unicodedata.normalize("NFD", t)
        t = re.sub("[\u0300\u0301\u0308]", "", t)   # grave, agudo, diéresis (la virgulilla de la ñ queda)
        t = unicodedata.normalize("NFC", t)
    return " ".join(t.split())

def contar_errores(ref, hyp):
    """Errores de un segmento con jiwer. ref/hyp ya normalizados."""
    r, h = ref.split(), hyp.split()
    if not r:
        return dict(S=0, D=0, I=len(h), N=0)
    if not h:
        return dict(S=0, D=len(r), I=0, N=len(r))
    o = jiwer.process_words(ref, hyp)
    return dict(S=o.substitutions, D=o.deletions, I=o.insertions, N=o.hits + o.substitutions + o.deletions)


def _reducir_palabra(w):
    if len(w) <= 15:
        return w
    for L in range(1, len(w) // 2 + 1):
        if (w[:L] * (len(w) // L + 1))[:len(w)] == w:
            return w[:L]
    return w

def _clave(w):
    return re.sub(r"[^\w]", "", w.lower())

def postprocesar_reglas(texto, max_n=40):
    """Las 3 reglas del paper (sección 3.4). Solo borran: nunca agregan palabras."""
    toks = [_reducir_palabra(w) for w in str(texto).split()]
    out = []
    for w in toks:                                         # (ii) palabra repetida
        if out and _clave(w) and _clave(w) == _clave(out[-1]):
            continue
        out.append(w)
    toks, claves = out, [_clave(w) for w in out]
    cambio = True
    while cambio:                                          # (iii) frase repetida
        cambio = False
        for n in range(min(len(toks) // 2, max_n), 1, -1):
            i = 0
            while i + 2 * n <= len(toks):
                if claves[i:i + n] == claves[i + n:i + 2 * n]:
                    del toks[i + n:i + 2 * n]; del claves[i + n:i + 2 * n]; cambio = True
                else:
                    i += 1
    return " ".join(toks)

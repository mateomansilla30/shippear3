"""Genera la misma frase con varias voces para elegir la que mejor suena en español.

Uso (desde voz/):
    .venv/Scripts/python probar_voces.py                 # voces argentinas de ElevenLabs (proveedor por defecto)
    .venv/Scripts/python probar_voces.py openai          # voces de OpenAI
    .venv/Scripts/python probar_voces.py gemini          # voces de Gemini
Los audios quedan en voz/salidas/voces/. Poné la elegida en TTS_ELEVEN_VOZ (su id), TTS_OPENAI_VOZ o TTS_GEMINI_VOZ.
"""
import sys
import time
from concurrent.futures import TimeoutError as FuturoTimeout

import config
from tts import _con_tope, duracion_wav

FRASE = "Hola, soy Voz Clara. ¿Querés que le mande un mensaje a María para avisarle que llegás tarde?"
VOCES = {
    # ElevenLabs: nombre → voice_id (biblioteca pública, acento argentino; se usan sin agregarlas a la cuenta)
    "elevenlabs": {
        "Valeria": "9oPKasc15pfAbMr7N6Gs",
        "Malena": "p7AwDmKvTdoHTBuueGvP",
        "Melanie": "bN1bDXgDIGX5lw0rtY2B",
        "Mariana": "9rvdnhrYoXoUt4igKpBw",
        "Agustin": "ByVRQtaK1WDOvTmP1PKO",
        "Tomas": "QK4xDwo9ESPHA4JNUpX3",
        "Lionel": "MjtZn5tagxL1RO6w9ER5",
        "Carlos": "gBTPbHzRd0ZmV75Z5Zk4",
    },
    "openai": {v: v for v in ["marin", "cedar", "coral", "nova", "sage", "shimmer"]},
    "gemini": {v: v for v in ["Sulafat", "Achird", "Vindemiatrix", "Kore", "Iapetus", "Aoede"]},
}


def main():
    proveedor = sys.argv[1] if len(sys.argv) > 1 else config.TTS_PROVEEDOR
    carpeta = config.SALIDAS / "voces"
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, voz in VOCES[proveedor].items():
        t0 = time.perf_counter()
        try:
            wav = _con_tope(proveedor, FRASE, voz, None)
        except FuturoTimeout:
            print(f"{nombre:10s} no respondió en {config.TTS_TIMEOUT_S:.0f} s")
            continue
        except Exception as e:
            print(f"{nombre:10s} ERROR {type(e).__name__}: {str(e)[:150]}")
            continue
        (carpeta / f"{proveedor}_{nombre}.wav").write_bytes(wav)
        print(f"{nombre:10s} {time.perf_counter() - t0:5.1f} s de espera | {duracion_wav(wav):4.1f} s de audio"
              f" | id {voz}", flush=True)
    print(f"\nEscuchalos en {carpeta}")


if __name__ == "__main__":
    main()

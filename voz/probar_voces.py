"""Genera la misma frase con varias voces para elegir la que mejor suena en español.

Uso (desde voz/):
    .venv/Scripts/python probar_voces.py            # voces de OpenAI (proveedor por defecto)
    .venv/Scripts/python probar_voces.py gemini     # voces de Gemini
Los audios quedan en voz/salidas/voces/. Poné la elegida en TTS_OPENAI_VOZ o TTS_GEMINI_VOZ dentro de .env.
"""
import sys
import time
from concurrent.futures import TimeoutError as FuturoTimeout

import config
from tts import _con_tope, duracion_wav

FRASE = "Hola, soy Voz Clara. ¿Querés que le mande un mensaje a María para avisarle que llegás tarde?"
VOCES = {
    "openai": ["marin", "cedar", "coral", "nova", "sage", "shimmer"],
    "gemini": ["Sulafat", "Achird", "Vindemiatrix", "Kore", "Iapetus", "Aoede"],
}


def main():
    proveedor = sys.argv[1] if len(sys.argv) > 1 else "openai"
    carpeta = config.SALIDAS / "voces"
    carpeta.mkdir(parents=True, exist_ok=True)
    for voz in VOCES[proveedor]:
        t0 = time.perf_counter()
        try:
            wav = _con_tope(proveedor, FRASE, voz, None)
        except FuturoTimeout:
            print(f"{voz:14s} no respondió en {config.TTS_TIMEOUT_S:.0f} s")
            continue
        except Exception as e:
            print(f"{voz:14s} ERROR {type(e).__name__}: {str(e)[:150]}")
            continue
        (carpeta / f"{proveedor}_{voz}.wav").write_bytes(wav)
        print(f"{voz:14s} {time.perf_counter() - t0:5.1f} s de espera | {duracion_wav(wav):4.1f} s de audio", flush=True)
    print(f"\nEscuchalos en {carpeta}")


if __name__ == "__main__":
    main()

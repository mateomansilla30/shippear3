"""Mide cuánto tarda cada etapa del recorrido completo (audio → texto → voz → nota de voz).

Uso (desde voz/):
    .venv/Scripts/python medir_latencia.py carpeta_con_audios [--sin-alternativa] [--max 10]
Ejemplo con los audios de S-DiverSe:
    .venv/Scripts/python medir_latencia.py ../../data_src/s-diverse/data/audio/ALS --max 8

Imprime la mediana y el peor caso por etapa y guarda el detalle en voz/salidas/latencia.csv.
"""
import argparse
import csv
import statistics
from pathlib import Path

import config
from pipeline import turno

ETAPAS = ["asr_principal", "asr_alternativa", "asr_total", "interpretar", "tts", "ogg", "total"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--max", type=int, default=10, help="cantidad de audios a probar")
    ap.add_argument("--sin-alternativa", action="store_true", help="no pedir la segunda hipótesis")
    args = ap.parse_args()

    audios = sorted(p for p in Path(args.carpeta).rglob("*")
                    if p.suffix.lower() in {".wav", ".mp3", ".m4a", ".ogg", ".webm"})[:args.max]
    if not audios:
        raise SystemExit(f"No hay audios en {args.carpeta}")

    filas = []
    for p in audios:
        try:
            t = turno(p.read_bytes(), p.name, alternativa=not args.sin_alternativa, nota_de_voz=True)
        except Exception as e:
            print(f"{p.name}: ERROR {type(e).__name__}: {str(e)[:150]}")
            continue
        fila = {"audio": p.name, "duracion_audio_s": t.transcripcion.duracion_audio_s,
                "confianza": t.transcripcion.confianza, "nivel": t.transcripcion.nivel, **t.tiempos_ms}
        filas.append(fila)
        print(f"{p.name:28s} {fila['duracion_audio_s']:5.1f} s audio | total {t.tiempos_ms['total']:5d} ms | "
              f"confianza {t.transcripcion.confianza:.2f} ({t.transcripcion.nivel}) | {t.texto_a_decir[:60]}")

    if not filas:
        return
    print("\nEtapa              mediana      peor")
    for e in ETAPAS:
        v = [f[e] for f in filas if isinstance(f.get(e), (int, float))]
        if v:
            print(f"{e:18s} {statistics.median(v):7.0f} ms {max(v):7.0f} ms")
    config.SALIDAS.mkdir(exist_ok=True)
    salida = config.SALIDAS / "latencia.csv"
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for fila in filas for k in fila}))
        w.writeheader()
        w.writerows(filas)
    print(f"\nDetalle en {salida}")


if __name__ == "__main__":
    main()

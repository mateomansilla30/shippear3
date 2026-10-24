"""Conversión a nota de voz de WhatsApp: OGG con códec OPUS, mono.

Uso:
    from nota_voz import a_nota_de_voz
    ogg = a_nota_de_voz(wav_bytes)
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess

import config


def ruta_ffmpeg() -> str:
    """ffmpeg desde FFMPEG en .env, el PATH, o la instalación de winget en Windows."""
    if config.FFMPEG and os.path.exists(config.FFMPEG):
        return config.FFMPEG
    en_path = shutil.which("ffmpeg")
    if en_path:
        return en_path
    winget = glob.glob(os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"))
    if winget:
        return winget[0]
    raise RuntimeError("No encuentro ffmpeg: instalalo o poné su ruta en FFMPEG dentro de voz/.env")


def a_nota_de_voz(audio: bytes, bitrate: str | None = None) -> bytes:
    """Cualquier audio que ffmpeg entienda (WAV de Gemini, webm del navegador) → .ogg OPUS mono 48 kHz."""
    cmd = [ruta_ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
           "-ac", "1", "-ar", "48000", "-c:a", "libopus", "-b:a", bitrate or config.NOTA_VOZ_BITRATE,
           "-application", "voip", "-f", "ogg", "pipe:1"]
    r = subprocess.run(cmd, input=audio, capture_output=True, timeout=60)
    if r.returncode != 0 or not r.stdout.startswith(b"OggS"):
        raise RuntimeError(f"ffmpeg falló: {r.stderr.decode(errors='ignore')[:500]}")
    return r.stdout

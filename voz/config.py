"""Configuración del pipeline de voz. Todo se puede cambiar desde voz/.env (ver .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

CARPETA = Path(__file__).resolve().parent
load_dotenv(CARPETA / ".env")

# --- Transcripción (Groq, API compatible con OpenAI) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1"
ASR_MODELO = os.getenv("ASR_MODELO", "whisper-large-v3-turbo")          # rápido: el que usa la demo
ASR_MODELO_ALTERNATIVO = os.getenv("ASR_MODELO_ALTERNATIVO", "whisper-large-v3")  # segunda hipótesis
ASR_IDIOMA = "es"
# Cuánto más se espera a la hipótesis alternativa después de tener la principal (segundos).
# Si tarda más, se sigue sin ella: la alternativa nunca debe frenar la respuesta.
ASR_ESPERA_ALTERNATIVA_S = float(os.getenv("ASR_ESPERA_ALTERNATIVA_S", "1.0"))

# Umbrales de confianza (provisorios: calibrarlos con hablantes de validación, nunca de test)
CONFIANZA_ALTA = float(os.getenv("CONFIANZA_ALTA", "0.75"))
CONFIANZA_MEDIA = float(os.getenv("CONFIANZA_MEDIA", "0.45"))

# --- Voz (TTS): proveedor principal + respaldo, con tope de tiempo ---
TTS_PROVEEDOR = os.getenv("TTS_PROVEEDOR", "elevenlabs")  # "elevenlabs" | "openai" | "gemini"
TTS_RESPALDO = os.getenv("TTS_RESPALDO", "openai")         # cualquiera de los anteriores o "ninguno"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
TTS_ELEVEN_MODELO = os.getenv("TTS_ELEVEN_MODELO", "eleven_flash_v2_5")
TTS_ELEVEN_VOZ = os.getenv("TTS_ELEVEN_VOZ", "9oPKasc15pfAbMr7N6Gs")  # Valeria (acento argentino, biblioteca pública)
TTS_ELEVEN_VELOCIDAD = float(os.getenv("TTS_ELEVEN_VELOCIDAD", "1.0"))
TTS_TIMEOUT_S = float(os.getenv("TTS_TIMEOUT_S", "15"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TTS_OPENAI_MODELO = os.getenv("TTS_OPENAI_MODELO", "gpt-4o-mini-tts")
TTS_OPENAI_VOZ = os.getenv("TTS_OPENAI_VOZ", "marin")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TTS_GEMINI_MODELO = os.getenv("TTS_GEMINI_MODELO", "gemini-3.8-flash-tts")
TTS_GEMINI_VOZ = os.getenv("TTS_GEMINI_VOZ", "Sulafat")
TTS_ESTILO = os.getenv(
    "TTS_ESTILO",
    "voz cálida y clara, español rioplatense, hablando con calma y pronunciando bien cada palabra",
)

# --- Nota de voz ---
FFMPEG = os.getenv("FFMPEG")  # ruta a ffmpeg si no está en el PATH
NOTA_VOZ_BITRATE = os.getenv("NOTA_VOZ_BITRATE", "32k")

SALIDAS = CARPETA / "salidas"

# --- Publicación ---
# URL pública del backend (p. ej. https://api.vozclara.com). Si está, se usa para armar los audio_url; si no, se usa la
# URL del pedido, que detrás de un proxy https puede salir como http y el navegador la bloquearía.
URL_PUBLICA = (os.getenv("URL_PUBLICA") or "").rstrip("/") or None
# Audios de prueba de S-DiverSe que el front pide al backend. No van al repo (licencia): se copian a mano.
AUDIOS_PRUEBA = CARPETA / "audios_prueba"

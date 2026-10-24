# Pipeline de voz

Recorrido completo de un turno: **audio de la persona → texto limpio con confianza → voz clara**, y la conversión a
nota de voz de WhatsApp. Es un servicio Python (FastAPI) que la web llama por HTTP.

```
audio (web: webm / wav)
  → Groq whisper-large-v3-turbo        transcripción + métricas por segmento
  ∥ Groq whisper-large-v3              hipótesis alternativa, en paralelo (opcional)
  → reglas anti-alucinación            las mismas del notebook de evaluación
  → confianza 0–1 + nivel              alta / media / baja
  → interpretar                        memoria de la persona y, si la confianza no es baja, LLM (gpt-4.1-mini)
  → TTS: ElevenLabs, voz Valeria       WAV 24 kHz, acento argentino (respaldo: OpenAI, con tope de 15 s)
  → ffmpeg                             .ogg OPUS mono (nota de voz de WhatsApp)
  → Kapso                              se manda al chat de WhatsApp, si la persona confirma
```

## Flujo con WhatsApp

1. La persona habla. `/turno` transcribe e **interpreta lo que quiso decir** (`interprete.py`): primero busca una
   corrección parecida en su memoria; si no hay y la confianza no es baja, un LLM corrige errores de reconocimiento
   usando sus contactos, vocabulario y correcciones ("kero ablar co maia" → "Quiero hablar con María"). Con confianza
   baja no adivina. Si el LLM cambia demasiado el largo del texto, se descarta.
2. La app muestra lo que entendió; la persona lo valida o lo corrige (`/validar`).
3. La app pregunta "¿Lo mando como audio por WhatsApp?". Si dice que sí, `/enviar` genera la nota de voz con Valeria
   (.ogg OPUS) y la manda por Kapso (`kapso.py`) a `KAPSO_DESTINO`.

Para probarlo con el **sandbox de Kapso**: en el panel, WhatsApp → Sandbox → Add Test Number con tu número, y mandá
el código de activación desde ese WhatsApp. `KAPSO_DESTINO` tiene que ser ese mismo número. WhatsApp solo deja mandar
mensajes dentro de las 24 h desde que el destinatario le escribió al número.

## Instalación

Desde `voz/`:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # Windows (Mac/Linux: .venv/bin/python)
cp .env.example .env                                          # y completá GROQ_API_KEY, ELEVENLABS_API_KEY y OPENAI_API_KEY
```

Necesita **ffmpeg** instalado (Windows: `winget install Gyan.FFmpeg`). Si no está en el PATH, poné su ruta en
`FFMPEG` dentro de `.env`.

## Correr el servicio

```bash
.venv/Scripts/python -m uvicorn servidor:app --reload --port 8000
```

Abrí http://localhost:8000/docs para probar cada endpoint desde el navegador (subir un audio, escribir un texto).

**Para el front** (contrato de `frontend/src/lib/api.ts`): poné `NEXT_PUBLIC_API_URL=http://localhost:8000` en
`frontend/.env.local` y levantá el front con `npm run dev`.

| Endpoint | Recibe | Devuelve |
| --- | --- | --- |
| `GET /personas` | — | Lista de personas (la primera vez crea "Marta", la persona demo) |
| `POST /personas` | JSON `{"nombre": "..."}` | La persona nueva |
| `GET /memoria/{persona_id}` | — | Memoria: persona, contactos, vocabulario, correcciones, historial |
| `PUT /memoria/{persona_id}` | JSON con persona, contactos, vocabulario, correcciones | La memoria actualizada |
| `POST /turno` | `audio` (archivo), `persona_id` | Turno: `id`, `texto`, `audio_url`, `fecha`, `estado`; y para depurar: `texto_asr`, `confianza`, `nivel`, `hipotesis`, `correccion_usada`, `tiempos_ms` |
| `POST /validar` | JSON `{"persona_id", "turno_id", "texto_final"}` | La memoria. Si el texto cambió, guarda la corrección |
| `POST /enviar` | JSON `{"persona_id", "turno_id", "destino"?}` | Manda el texto final como nota de voz por WhatsApp (Kapso). Si falla, el motivo viene en `detail` |
| `GET /voz/{persona_id}/{turno_id}` | — | La voz de un turno (a lo que apunta `audio_url`). La primera vez se genera en streaming y se guarda una copia |

**Para el agente y WhatsApp:**

| Endpoint | Recibe | Devuelve |
| --- | --- | --- |
| `GET /salud` | — | Modelos configurados y si están las claves |
| `POST /transcribir` | `audio`, `vocabulario` (opcional, "María, Lucía, levodopa"), `alternativa` | JSON: `texto`, `texto_crudo`, `hipotesis`, `confianza`, `nivel`, `senales`, `segmentos`, `tiempos_ms` |
| `POST /hablar` | JSON `{"texto": "...", "voz": "<voice_id>", "formato": "wav" \| "ogg"}` | El audio directamente (`audio/wav` o `audio/ogg`) |
| `POST /nota-de-voz` | `audio` (cualquier formato) | `.ogg` OPUS para WhatsApp |

**Memoria (versión simple).** Se guarda en `voz/datos/` (JSON, no se sube al repo). En cada turno:
1. Los contactos y el vocabulario de la persona **no** van a Whisper como pista (ver Notas): quedan para la corrección.
2. Si la transcripción se parece a una que la persona ya corrigió (WER ≤ 0,25), se usa la corrección. Así, la misma
   frase sale mal la primera vez y bien después de validarla.

El agente con LLM puede reemplazar `memoria.aplicar_correcciones` por algo mejor (pasarle las correcciones parecidas
como ejemplos) sin que el front cambie.

Desde Python, sin servidor:

```python
from pipeline import turno, hablar
t = turno(open("audio.wav", "rb").read(), "audio.wav", interpretar=mi_funcion, nota_de_voz=True)
t.transcripcion.texto, t.transcripcion.confianza, t.transcripcion.nivel, t.tiempos_ms
```

`interpretar` es el punto donde se enchufa el LLM corrector y el agente con memoria: recibe la `Transcripcion`
(con `hipotesis` y `confianza`) y devuelve el texto a decir.

## Confianza

Whisper no da una confianza única, así que la combino a partir de cinco señales (todas vienen en `senales`):

| Señal | Qué mide | Efecto |
| --- | --- | --- |
| `prob_tokens` | exp(`avg_logprob`) promedio, ponderado por duración | Qué tan seguro estaba Whisper |
| `acuerdo` | 1 − WER entre la hipótesis principal y la alternativa | Si dos modelos coinciden, es más confiable |
| `no_speech` | Probabilidad de que no haya habla | Silencio o ruido bajan la confianza |
| `borrado_por_reglas` | Fracción de palabras que las reglas eliminaron | Mucho borrado = Whisper alucinó |
| `bucle` | Algún segmento con `compression_ratio` > 2,4 | Texto repetitivo: confianza a la mitad |

`confianza = (0,6·prob_tokens + 0,4·acuerdo) × (1 − no_speech) × (1 − borrado) × (0,5 si hay bucle)`.

Niveles: **alta** ≥ 0,75 · **media** ≥ 0,45 · **baja** < 0,45. Los umbrales son provisorios: hay que calibrarlos con
hablantes de **validación** de S-DiverSe, nunca de test.

## Elegir la voz y medir tiempos

```bash
.venv/Scripts/python probar_voces.py         # misma frase con 8 voces argentinas de ElevenLabs → salidas/voces/*.wav
.venv/Scripts/python probar_voces.py openai  # lo mismo con voces de OpenAI (o gemini)
.venv/Scripts/python medir_latencia.py ../../data_src/s-diverse/data/audio/ALS --max 8
```

`medir_latencia.py` imprime la mediana y el peor caso de cada etapa y guarda el detalle en `salidas/latencia.csv`.

Medido con 3 audios cortos de S-DiverSe (6 a 19 s), desde Argentina:

| Etapa | Mediana | Peor caso |
| --- | --- | --- |
| Transcripción (Groq, con alternativa en paralelo) | 0,9 s | 1,9 s |
| Voz (ElevenLabs, Valeria, eleven_flash_v2_5) | 1,0 s | 1,6 s |
| Nota de voz `.ogg` | 0,08 s | 0,13 s |
| **Total, sin el LLM del agente** | **2,0 s** | **3,7 s** |

**La voz: ElevenLabs con Valeria** (acento argentino, de la biblioteca pública; se usa sin agregarla a la cuenta).
Probamos tres proveedores: Gemini tardó de 4 a 7 s por frase y dejó de responder tras 8 pedidos (cupo gratuito);
OpenAI responde en ~2 s pero sus voces en español suenan poco naturales; ElevenLabs responde en ~1 s con acento
rioplatense. El primer pedido con una voz tarda unos segundos más (la carga), así que conviene hacer un turno de
prueba antes de presentar. Si ElevenLabs falla o tarda más de `TTS_TIMEOUT_S` (15 s), se usa OpenAI; si los dos
fallan, el error lo dice en vez de quedarse colgado.

Palancas para bajar la latencia, de mayor a menor efecto:

1. **Sin hipótesis alternativa** (`alternativa=false`): el modelo grande es más lento que el turbo. De todos modos,
   nunca se lo espera más de `ASR_ESPERA_ALTERNATIVA_S` (1 s) después de tener la principal.
2. **Respuestas cortas** para el TTS: el tiempo de la voz crece con el largo del texto.
3. **Audio en WAV o webm corto** desde la web: Groq factura mínimo 10 s por pedido pero procesa rápido audios cortos.
4. **Voz en streaming (hecho):** `/turno` devuelve el texto sin esperar la voz; el navegador pide `audio_url` y
   ElevenLabs la manda a medida que la genera. Medido: el texto llega en ~2,3 s y la voz empieza a sonar ~0,4 s
   después (antes: texto y voz juntos recién después de generar el audio completo). La conexión con ElevenLabs se
   reutiliza y la voz se "calienta" al arrancar el servidor, para que el primer turno no tarde de más.

## Notas

- **Privacidad:** el audio va a Groq y el texto a ElevenLabs (y a OpenAI si se usa el respaldo). Son datos de salud y de voz: no los mandes a otros
  servicios ni los guardes sin necesidad.
- **Vocabulario como pista para Whisper: apagado.** Con habla difícil, Whisper copia la pista en lugar de transcribir:
  con ALS_M06_08_01 devolvió "María, Juan, Riluzol, kinesiólogo, Háblalo." con confianza 0,86. Se puede activar con
  `ASR_USAR_VOCABULARIO=1`; si Whisper devuelve solo palabras de la pista, la confianza pasa a 0.
- Las reglas (`reglas.py`) son copia exacta de las del notebook de evaluación, para que el sistema en vivo limpie igual
  que lo que medimos.

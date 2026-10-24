# Agente de Voz Clara

Es la capa que hace que el sistema sea personal: guarda la memoria de cada persona, la usa en cada turno para entender qué quiso decir, decide si decirlo, confirmarlo u ofrecer opciones, y aprende de lo que la persona valida. **No reentrena nada**: aprende en el momento, pasándole al LLM los ejemplos validados más parecidos.

```
Audio → [pipeline de voz] → texto_asr (+ texto_corregido) → [agente] → turno → front
                                                                ↑
                                         front: validar / corregir / sugerencias
```

## Cómo se integra en el back

El agente es un paquete Python dentro del mismo FastAPI. El pipeline de voz implementa `POST /turno` y, después de transcribir, llama al agente:

```python
from agente import agente
from agente.rutas import router as rutas_agente

app.include_router(rutas_agente)  # /personas, /memoria, /validar, /sugerencia

@app.post("/turno")
async def turno(audio: UploadFile, persona_id: str = Form(...)):
    texto_asr, texto_corregido = pipeline_de_voz(audio)  # lo de tu lado
    t = agente.procesar_turno(persona_id, texto_asr, texto_corregido)
    t["audio_url"] = tts(t["texto"])                     # Gemini TTS, opcional
    return t
```

- `texto_asr`: la transcripción **después de las reglas anti-alucinación** y **antes** del LLM corrector. Es obligatorio.
- `texto_corregido`: la salida del LLM corrector genérico, si hay. Es opcional. El agente la ve, pero puede contradecirla con la memoria de la persona (ej.: "paresia" vs. "parálisis").
- `procesar_turno` es sincrónico (llama al LLM con el SDK de OpenAI). Dentro de un endpoint `async`, envolverlo en `await run_in_threadpool(...)` si molesta.

## Qué devuelve `procesar_turno` (y `POST /turno`)

```json
{
  "id": "uuid", "fecha": "ISO", "estado": "pendiente",
  "texto_asr": "mandale a maia ke yego tarde",
  "texto": "Mandale a María que llego tarde.",
  "intencion": "mensaje",          // "decir" | "mensaje"
  "destinatario": "María",         // solo si es un contacto de la persona; si no, null
  "mensaje": "Llego tarde.",       // texto a enviar si intencion = "mensaje"
  "confianza": 0.9,
  "accion": "confirmar",           // "decir" | "confirmar" | "opciones"
  "opciones": ["..."],             // alternativas, para accion = "opciones"
  "propuestas": [{"tipo": "contacto", "valor": "Tomás", "relacion": "nieto"}],  // ver "Cómo aprende"
  "audio_url": "..."               // lo agrega el pipeline (TTS)
}
```

Reglas de `accion`:
- `mensaje` → siempre `confirmar`: nunca se manda nada afuera sin un "sí".
- confianza ≥ 0,85 → `decir`.
- confianza < 0,5 y hay alternativas → `opciones`.
- Si no → `confirmar`.
- Si el LLM falla o responde mal, se devuelve `texto_corregido` (o `texto_asr`) con confianza 0 y `confirmar`.

Los umbrales están puestos a ojo en `agente.py`. Hay que ajustarlos con hablantes de **validación**, nunca de test.

## Rutas para el front (`rutas.py`)

| Ruta | Qué hace |
| --- | --- |
| `GET /personas` · `POST /personas {nombre}` | Listar y crear personas. |
| `GET /memoria/{id}` | `{persona, contactos, vocabulario, correcciones, historial, sugerencias}` |
| `PUT /memoria/{id}` | La persona edita su perfil o borra correcciones aprendidas. |
| `POST /validar {persona_id, turno_id, texto_final}` | "Sí" (texto_final = texto) o corrección. Las dos cosas se guardan como ejemplo. |
| `POST /sugerencia {persona_id, valor, tipo, relacion?}` | Aceptar una sugerencia como `contacto` o `palabra`, o `descartar` (no se vuelve a sugerir). |

## Cómo aprende (modo mixto)

- **Solo:** cada "sí" y cada corrección quedan como ejemplo `texto_asr → texto_final`. Si el mismo ejemplo se repite, suma usos.
- **Con confirmación:** el agente nunca escribe la memoria por su cuenta, solo **propone**. Las propuestas aparecen en `sugerencias` de `GET /memoria`, con la forma `{tipo: "contacto" | "palabra" | null, valor, relacion}`. Salen de dos lugares:
  1. **Del LLM**, cuando la persona menciona algo nuevo: "mi nieto Tomás" → contacto Tomás (nieto); "tomar el riluzol" → palabra. Solo se proponen si la persona validó ese turno con "sí". Si lo corrigió, la propuesta pudo salir de un error y se descarta.
  2. **Por repetición:** un nombre propio que aparece en 3 turnos validados (`tipo: null`, la persona elige si es contacto o palabra).

  La persona responde con `POST /sugerencia`: la acepta como `contacto` o `palabra`, o la descarta (`descartar`, no se vuelve a proponer).
- En cada turno el LLM recibe: el perfil, los contactos, las palabras frecuentes, hasta 5 ejemplos parecidos (por similitud de texto) y los últimos 3 turnos validados.

## Configuración (variables de entorno)

| Variable | Por defecto |
| --- | --- |
| `OPENAI_API_KEY` | (obligatoria) |
| `AGENTE_LLM_MODELO` | `gpt-4.1-mini` |
| `AGENTE_LLM_URL` | OpenAI. Para Groq: `https://api.groq.com/openai/v1` con `AGENTE_LLM_KEY_ENV=GROQ_API_KEY` |
| `AGENTE_DB` | `agente.db`. En Easypanel ponerlo en un **volumen**, si no se pierde en cada deploy. |

Dependencias: `openai`, `fastapi` (ya está en el back). La memoria usa `sqlite3` de la librería estándar.

## Probarlo

```bash
python -m agente.test_agente   # desde la raíz del repo, con un LLM falso: no gasta tokens
```

Con `gpt-4.1-mini` real tarda alrededor de 1–1,5 s por turno.

## Pendiente

- **Calibrar la confianza:** el LLM la sobreestima. Sin memoria, cambió "paresia" por "parálisis" con 0,9 de confianza, un error silencioso. Medir con validación y ajustar los umbrales.
- **Curva de mejora con el uso:** WER con 0, 5, 10 y 20 correcciones en memoria, simulado con los segmentos de test de cada hablante en orden.
- **Enviar el WhatsApp** (Kapso) cuando la persona confirma un `mensaje`.
- Los audios y textos son datos de salud: no loguearlos ni mandarlos a servicios que no hagan falta.

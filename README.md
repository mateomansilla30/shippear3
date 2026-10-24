# Voz Clara

**Un asistente de voz que aprende a entenderte: cuanto más lo usás, mejor te entiende, y habla por vos.**

Voz Clara es un agente de voz para personas con habla atípica (disartria por ELA, Parkinson, ACV y otras enfermedades neurológicas). La persona habla, el sistema transcribe, interpreta lo que quiso decir y lo dice con voz clara. Un agente con memoria recuerda a la persona, sus contactos y sus correcciones, así que mejora con cada uso.

Proyecto para un hackatón de IA, construido sobre el dataset [S-DiverSe](https://github.com/ferugit/s-diverse).

---

## El problema

Los asistentes de voz y los sistemas de reconocimiento del habla se entrenan con habla típica y fallan con personas con disartria. Con habla disártrica, Whisper además **inventa texto**: entra en bucles ("no, no, no, no...") y agrega cientos de palabras que nadie dijo. Estas personas no pueden usar asistentes ni hacerse entender por teléfono o en un comercio sin depender de un familiar. Las pocas soluciones especializadas que existen están pensadas sobre todo para el inglés.

Muchas pueden escribir, pero no es lo mismo. Escribir es lento, saca a la persona del ritmo de la conversación y la convierte en alguien a quien hay que leer en vez de escuchar. Hablar es parte de quién somos: es como le decimos "te quiero" a una hija o contamos un chiste. **No queremos que dejen de hablar: queremos que sigan hablando y que se las entienda.**

---

## Cómo funciona

Flujo de un turno:

1. **La persona habla.** Botón de mantener apretado, para no cortar en las pausas largas.
2. **ASR:** Whisper transcribe el audio. Puede devolver también hipótesis alternativas y una confianza (`avg_logprob`).
3. **LLM corrector:** reconstruye lo que la persona quiso decir (ej.: "kero ablar co maia" → "quiero hablar con María"). Antes, unas reglas borran las repeticiones que Whisper inventó.
4. **Agente con memoria:** completa con lo que sabe de la persona y decide según su confianza:
   - **Alta:** habla o actúa directamente.
   - **Media:** confirma ("¿Querés mandarle un mensaje a María?").
   - **Baja:** ofrece 2 o 3 opciones para tocar.
5. **Voz:** Gemini Flash TTS dice el texto final con voz clara.
6. **Validación:** la persona confirma o corrige (botón grande de sí/no u opciones). Lo validado se guarda en la memoria.

La idea es preguntar antes que equivocarse en silencio, con respuestas cortas y voz pausada.

---

## Agente y memoria

Memoria por persona, persistente (JSON o SQLite alcanza para el hackatón):

- **Contactos:** nombre, relación y teléfono. Ej.: María, su hija; Juan, su amigo.
- **Vocabulario propio:** medicamentos, lugares, frases que repite.
- **Correcciones validadas:** pares "Whisper escribió X, la persona quiso decir Y".

**Mejora con el uso, sin reentrenar.** En cada turno se buscan las correcciones validadas más parecidas (por similitud de texto o fonética) y se le pasan al LLM como ejemplos, junto con los contactos y el vocabulario. Funciona desde la primera validación.

Demo clave: la misma frase sale mal al principio y bien después de una o dos validaciones.

---

## Integración con WhatsApp (Kapso)

"Mandale a María que llego tarde" → el agente resuelve quién es María desde la memoria → genera la nota de voz → la manda por WhatsApp.

- Plan gratuito de Kapso: número sandbox, API key y 2.000 mensajes.
- Las notas de voz tienen que ser `.ogg` con códec OPUS: hay que convertir la salida de Gemini con ffmpeg.
- Solo se pueden mandar mensajes libres dentro de las 24 h posteriores a que el destinatario le escriba al número. Para la demo, "María" le escribe al bot antes de presentar.
- El mensaje sale del número del bot, no del WhatsApp personal de la persona. Que cada persona conecte su propio número queda como trabajo futuro.

---

## Resultados

WER (tasa de error por palabra, en %; menor es mejor) sobre los **hablantes de test de S-DiverSe**: 6 personas que ningún modelo vio al entrenar, 98 segmentos, 2.430 palabras. El split es por hablante, no por segmento.

| Condición | Qué es | Total | High | High/Medium | Medium | Medium/Low | Low |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | *segmentos / hablantes* | *98 / 6* | *26 / 1* | *7 / 1* | *7 / 2* | *12 / 1* | *46 / 2* |
| A | whisper-small sin entrenar | 88,4 | 47,7 | 27,0 | 24,0 | 14,2 | 167,1 |
| A + reglas | A + las 3 reglas anti-alucinación del paper | 43,6 | 28,6 | 27,0 | 24,0 | 14,2 | 71,0 |
| B | A + reglas + LLM | 41,4 | 26,8 | 22,7 | 21,2 | 10,1 | 69,3 |
| C | whisper-small + LoRA | 55,8 | 29,5 | 7,8 | 16,1 | 18,2 | 105,8 |
| C + reglas | C + reglas | 38,5 | 29,0 | 8,5 | 16,1 | 18,2 | 61,4 |
| D | C + reglas + LLM | 36,9 | 26,0 | 12,8 | 16,6 | 15,5 | 60,0 |
| Turbo | whisper-large-v3-turbo sin entrenar | 73,0 | 19,0 | 12,1 | 13,8 | 12,2 | 162,2 |
| Turbo + reglas | turbo + reglas | 31,1 | 18,7 | 10,6 | 11,1 | 12,2 | 54,9 |
| **Turbo + reglas + LLM** | **pipeline final** | **30,7** | 18,6 | 10,6 | 11,5 | 11,5 | 54,1 |
| B + contexto | B con contexto simulado de la persona | 41,0 | [completar] | [completar] | [completar] | [completar] | [completar] |
| D + contexto | D con contexto simulado de la persona | 35,1 | [completar] | [completar] | [completar] | [completar] | [completar] |

**El mejor pipeline es turbo + reglas + LLM (30,7 %).** Casi toda la mejora viene de las reglas: turbo baja de 73,0 a 31,1 solo con ellas, y el LLM agrega 0,4 puntos (IC 95 % por hablantes: 0,0 a 1,2). Contra D, con el mismo LLM, el pipeline final es 5,3 puntos mejor (IC 2,3 a 6,6).

Notas para leer la tabla:

- **LLM usado:** B y D, `openai/gpt-oss-120b` (Groq). Contexto y turbo + reglas + LLM, `gpt-4.1-mini` (OpenAI). Con `gpt-4.1-mini`, B da 41,1 y D da 36,0: el contexto no cambia B (41,1 → 41,0, IC −0,5 a 0,4) y mejora D en 0,9 puntos (IC 0,3 a 1,3).
- **El contexto es simulado** con lo que la persona dijo en sus *otros* segmentos, nunca el evaluado. No demuestra que un perfil real ayude.
- **Inteligibilidad ≈ hablante:** cada nivel corresponde a 1 o 2 personas. "Low" lo domina ALS_M06, que alucina mucho, y STROKE_M02 tiene solo 12 palabras en total.
- **Lo que el sistema no hace:** cuando Whisper solo produce un bucle, deja de inventar pero no recupera lo que se dijo.
- **El LLM puede corregir de más:** en STROKE_F01_02 cambió "paresia" (correcto) por "parálisis". Por eso hay una salvaguarda que descarta su respuesta si cambia demasiado el largo del texto.

Tablas por enfermedad y por hablante en [reconocimiento-voz/resultados/](reconocimiento-voz/resultados/); métricas e intervalos de confianza explicados en [reconocimiento-voz/GUIA.md](reconocimiento-voz/GUIA.md).

---

## Estructura del repo

```
.
├── README.md                     este archivo
└── reconocimiento-voz/
    ├── README.md, GUIA.md        documentación del módulo de reconocimiento
    ├── notebooks/                los 3 notebooks de Colab
    └── resultados/               copia de las tablas de WER y transcripciones de test (solo texto)
```

### Notebooks (correrlos en este orden)

| Notebook | Qué hace | GPU | Tiempo |
| --- | --- | --- | --- |
| [`notebook_sdiverse_whisper.ipynb`](reconocimiento-voz/notebooks/notebook_sdiverse_whisper.ipynb) | Experimento completo: split por hablante, A, reglas, B, alineación forzada, entrenamiento LoRA, C, D, referencia turbo, tablas de WER, audios de demo y app de Gradio (sección 11) | T4 | ~1–1,5 h |
| [`notebook_contexto_llm.ipynb`](reconocimiento-voz/notebooks/notebook_contexto_llm.ipynb) | Mide si el LLM corrige mejor con contexto de la persona (B vs B+ctx, D vs D+ctx). Incluye `corregir_con_perfil(texto, perfil)` | No | 10–30 min |
| [`notebook_demo_turbo.ipynb`](reconocimiento-voz/notebooks/notebook_demo_turbo.ipynb) | Mide turbo + reglas + LLM, elige audios de demo y levanta la app de Gradio con perfil opcional | No | ~5 min |

### Qué guardan en Drive (`Mi unidad/Shippear/sdiverse_hackathon/`)

| Archivo o carpeta | Lo genera | Qué tiene |
| --- | --- | --- |
| `splits.csv` | principal | Split train/val/test por hablante y folds de la validación cruzada |
| `trozos_entrenamiento.csv` | principal | Cortes de la alineación forzada de los segmentos largos |
| `resultados/pred_A.csv`, `pred_C.csv`, `pred_ref_turbo.csv` | principal | Transcripciones de A, C y turbo |
| `resultados/tabla_total.csv`, `tabla_por_enfermedad.csv`, `tabla_por_inteligibilidad.csv`, `tabla_por_hablante.csv` | principal | WER en test |
| `resultados/wer_por_segmento_A.csv` | principal | WER de A por segmento, de peor a mejor |
| `resultados/transcripciones_val_test.csv` | principal | Todas las transcripciones de val y test, lado a lado |
| `resultados/transcripciones_contexto.csv` | contexto | Resultados con y sin contexto |
| `resultados/transcripciones_turbo_llm.csv` | demo | Resultados del pipeline final |
| `resultados/cache_llm.json`, `cache_llm_contexto.json`, `cache_llm_demo.json` | cada notebook | Caché de respuestas del LLM |
| `lora/principal/` | principal | Checkpoints, `historial.csv`, `LISTO.json` y `adaptador_final/` (adaptador LoRA, ~25 MB) |
| `demo/` | principal | 5 audios de test con `demo.csv` |
| `demo_turbo/` | demo | Audios de test donde turbo solo falla y el pipeline acierta, con `demo_turbo.csv` |

### Copia en el repo (`reconocimiento-voz/resultados/`)

| Archivo | Qué tiene |
| --- | --- |
| `splits.csv` | Split por hablante de los 444 segmentos |
| `transcripciones_test.csv` | Los 98 segmentos de test: referencia y la salida de cada condición |
| `wer_total.csv`, `wer_por_enfermedad.csv`, `wer_por_inteligibilidad.csv`, `wer_por_hablante.csv` | WER de cada condición |
| `wer_contexto.csv` | WER con y sin contexto |

Los audios no están en el repo (ver [Cuidados](#cuidados)).

---

## Cómo correrlo en Google Colab

### Conseguir los audios

Los autores de S-DiverSe publican solo anotaciones y links de YouTube. Cloná [su repositorio](https://github.com/ferugit/s-diverse) y corré su script de descarga (necesita yt-dlp, Deno y ffmpeg). Armá un zip con `s-diverse.tsv` y la carpeta `audio/` (adentro: `sdiverse/audio/<Enfermedad>/<ID>.wav`) y subilo a `Mi unidad/Shippear/`. El resultado esperado son 444 segmentos en WAV de 16 kHz, unos 293 MB.

### Notebook principal

1. **Datos:** subí el zip a `Mi unidad/Shippear/`. El nombre no importa: el notebook busca el `.zip` que contiene `s-diverse.tsv`.
2. **Notebook:** en colab.research.google.com → *Subir* → el `.ipynb`.
3. **GPU:** *Entorno de ejecución → Cambiar tipo de entorno → T4 GPU*.
4. **API key del LLM:** ícono de llave (*Secrets*) → agregá `GROQ_API_KEY` (de console.groq.com) y activá "Acceso al notebook". Sin clave, corre igual pero salta B y D.
5. *Entorno de ejecución → Ejecutar todas*. Aceptá el permiso para montar Drive.
6. **Dejá la pestaña abierta y a la vista.** Colab gratis corta las sesiones inactivas o que quedan mucho tiempo en segundo plano.

Correlo completo de entrada, sin una "corrida de prueba" con menos épocas: al terminar, el entrenamiento marca `LISTO.json` y una segunda corrida lo saltaría.

El notebook también corre en Kaggle (acelerador *GPU T4 x2*; usa una sola GPU).

#### Tiempos aproximados en T4

Son estimaciones, no medidas en GPU.

| Etapa | Tiempo |
| --- | --- |
| Instalación + descompresión | 3–5 min |
| A: whisper-small sobre los 444 segmentos (+5 hipótesis por segmento corto) | 10–20 min |
| B: LLM sobre val+test (~120 llamadas en paralelo) | 2–5 min |
| Alineación forzada de segmentos largos | 5–10 min |
| Entrenamiento LoRA (hasta 8 épocas con early stopping) | 15–30 min |
| C y D sobre val+test | 5–8 min |
| Referencia whisper-large-v3-turbo sobre val+test | 3–6 min |
| **Total** | **~1–1,5 h** |
| Validación cruzada opcional (`CFG["ejecutar_cv"]=True`) | +1–1,5 h, no recomendada en Colab gratis |

En la corrida real, el entrenamiento LoRA tardó 6,5 min y el early stopping lo frenó en la época 5.

Colab gratis tiene un cupo de GPU que no es público y varía. Si después de varias horas de uso te niega la T4, hay que esperar o usar otra cuenta de Google.

#### Si Colab se desconecta

Reconectá, elegí T4 de nuevo si hace falta y *Ejecutar todas*. Cada etapa reutiliza lo que guardó en Drive:

- `resultados/pred_A.csv`, `pred_C.csv`, `pred_ref_turbo.csv`: si existen, no se recalculan.
- `resultados/cache_llm.json`: las respuestas del LLM no se pagan dos veces.
- `trozos_entrenamiento.csv`: la alineación forzada.
- `lora/principal/checkpoint-*`: un checkpoint por época. El entrenamiento retoma desde el último (pierde a lo sumo la época en curso).
- `lora/principal/LISTO.json`: si existe, el entrenamiento se salta.

**Para reentrenar** (por ejemplo, si cambiaste un hiperparámetro): borrá en Drive la carpeta `lora/principal/` y el archivo `resultados/pred_C.csv`. Si cambiaste el LLM o el prompt, no hace falta borrar nada: la caché distingue por modelo y prompt.

#### Cambiar el proveedor de LLM

Todo se cambia en la celda de configuración (`CFG`).

- **Groq (gratis, por defecto):** `GROQ_API_KEY` en los Secrets. Si Groq deja de ofrecer el modelo de `llm_modelo`, cambialo por otro de console.groq.com/docs/models. El plan gratuito limita las llamadas por minuto: el notebook espera y reintenta. Si al final avisa que algunas llamadas fallaron, volvé a correr la celda (las exitosas salen de la caché).
- **Anthropic:** hay una línea lista para descomentar (`claude-haiku-5-5`, secreto `ANTHROPIC_API_KEY`). Más potente: `llm_modelo="claude-opus-5-5"`.
- **OpenAI u otro compatible:** `llm_proveedor="openai_compatible"`, `llm_modelo="..."`, `llm_base_url=` la URL del proveedor (`None` para OpenAI), clave en `OPENAI_API_KEY`.
- **Sin LLM:** `llm_proveedor="ninguno"` (salta B y D).

### Notebook de contexto (`notebook_contexto_llm.ipynb`)

Mide si el LLM corrige mejor cuando sabe quién es la persona. El contexto se simula con hasta ~350 palabras de lo que esa persona dijo en sus *otros* segmentos, nunca con el evaluado.

- **No necesita GPU.** Abrilo en otra pestaña de Colab con entorno de CPU.
- Necesita que el principal ya haya generado `resultados/pred_A.csv` y `splits.csv` (los primeros ~20–30 min). Si además existe `pred_C.csv`, compara también D contra D+contexto.
- Proveedor y secreto: los de su celda `CFG` (activá "Acceso al notebook").
- Hace unas 400 llamadas al LLM con mensajes más largos. En un plan gratuito con límite por minuto puede tardar 10–30 min. Si avisa que algunas fallaron, volvé a correr la celda.
- Al final tiene `corregir_con_perfil(texto, perfil)` para probar con un perfil escrito a mano.

### Notebook de demo (`notebook_demo_turbo.ipynb`)

El pipeline que mejor rindió: turbo + reglas + LLM.

- **No necesita GPU:** la transcripción la hace Groq con `whisper-large-v3-turbo`. Usá un entorno de CPU.
- Secretos con "Acceso al notebook": `GROQ_API_KEY` (transcripción) y `OPENAI_API_KEY` (LLM, `gpt-4.1-mini`).
- Primero mide turbo + reglas + LLM sobre los hablantes de test (~120 llamadas al LLM, unos minutos) y usa el LLM en la demo solo si mejora en **validación**.
- Guarda en `demo_turbo/` audios de test donde turbo solo falla y el pipeline acierta.

#### Demo con Gradio

La última celda abre una app de Gradio con link público (`https://....gradio.live`, válido 72 h) que funciona desde el celular. Se graba o sube un audio, con un perfil opcional de la persona, y se ven lado a lado "Whisper grande sin corregir" y "Nuestro sistema". Tarda unos 5 a 10 segundos por audio.

- El link vive mientras la sesión de Colab esté activa: dejá la pestaña abierta.
- Si Colab se desconecta, *Ejecutar todas* lo levanta de nuevo en un par de minutos (todo sale de la caché).
- La API de Groq puede devolver algo distinto del turbo evaluado en Colab: tené un video de respaldo.

El notebook principal también tiene una app de Gradio (sección 11) que compara whisper-small contra su mejor enfoque.

El guion de la demo, los audios recomendados y el plan B están en la [guía del proyecto](reconocimiento-voz/GUIA.md).

---

## Estado

**Hecho**

- Pipeline de evaluación con split por hablante y WER total, por enfermedad, por inteligibilidad y por hablante, con intervalos de confianza por hablante.
- whisper-small con LoRA entrenado sobre S-DiverSe (C y D).
- Corrección con LLM, con y sin contexto simulado de la persona.
- Pipeline turbo + reglas + LLM (el mejor resultado) con app de Gradio.

**Falta**

1. **Interfaz:** botón grande para hablar, sí/no y opciones, audio de respuesta y panel de "lo que aprendí".
2. **Agente con memoria:** memoria persistente por persona, corrección con ejemplos de la memoria, detección de intención, cálculo de confianza y umbrales de actuar/confirmar/opciones, perfil de la persona de la demo.
3. **Pipeline de voz:** conectar ASR, LLM y Gemini Flash TTS, convertir a nota de voz y medir la latencia.
4. **WhatsApp con Kapso:** cuenta, número, envío de notas de voz y ventana de 24 h abierta para la demo.
5. **Evaluación por escenarios:** éxito de la tarea con escenarios guionados, mejora con el uso a medida que crece la memoria, confirmaciones por pedido y errores silenciosos (actuar con confianza alta y estar mal: tiene que tender a cero).

---

## Cuidados

- **Nunca usar hablantes de test para entrenar, elegir umbrales ni armar la memoria evaluada.** Ni sus segmentos ni los de sus hablantes. Los umbrales y el mejor enfoque se eligen en validación.
- **Licencia de S-DiverSe:** el repositorio no incluye licencia y el audio pertenece a los videos originales de YouTube. Uso de investigación y demo, citando el paper. No publiques los audios ni el zip. Revisala antes de usar audios en una demo pública y, para uso público o comercial, consultá a los autores.
- **Datos de salud y de voz:** no mandar audios a servicios innecesarios. En el pipeline de demo, el audio va a Groq (transcripción) y el texto a OpenAI (LLM). El adaptador LoRA de whisper-small es la alternativa que puede correr local.

**Cita:** López, F., Ibañez, F., Martínez, A., Alonso, I., Gómez, P., Kesiraju, S. y Luque, J. (2026). *S-DiverSe: Spanish Diverse Speech*. Interspeech 2026. [arXiv:2607.03207](https://arxiv.org/abs/2607.03207).

# Voz Clara

**Un asistente de voz que aprende a entenderte: cuanto más lo usás, mejor te entiende, y habla por vos.**

Voz Clara es un agente de voz para personas con habla atípica (disartria por Parkinson, ACV, ELA y otras enfermedades neurológicas). La persona habla, el sistema transcribe e interpreta lo que quiso decir y lo repite con voz clara. Un agente con memoria recuerda a la persona, sus contactos y sus correcciones, así que mejora con cada uso.

Proyecto para un hackatón de IA, construido sobre el dataset S-DiverSe.

---

## El problema

Los asistentes de voz y los sistemas de reconocimiento del habla están entrenados con habla típica y fallan con personas con disartria. Esas personas no pueden usar asistentes ni hacerse entender por teléfono o en un comercio sin depender de un familiar. Las pocas soluciones especializadas que existen están pensadas sobre todo para el inglés.

Muchas de estas personas pueden escribir, pero no es lo mismo. Escribir es lento, saca a la persona del ritmo de la conversación y la convierte en alguien a quien hay que leer en vez de escuchar. Hablar es parte de quién somos: es como le decimos "te quiero" a una hija o contamos un chiste. **No queremos que dejen de hablar: queremos que sigan hablando y que se las entienda.**

---

## Cómo funciona

Flujo de un turno:

1. **La persona habla** (botón de mantener apretado, para no cortar en las pausas largas).
2. **Reconocimiento:** Whisper transcribe el audio y devuelve también hipótesis alternativas y un nivel de confianza.
3. **Interpretación:** un LLM reconstruye lo que la persona quiso decir, usando el contexto y la memoria.
4. **Agente:** según su confianza, decide:
   - **Alta:** habla o actúa directamente.
   - **Media:** confirma ("¿Querés mandarle un mensaje a María?").
   - **Baja:** ofrece 2 o 3 opciones para tocar.
5. **Voz:** Gemini Flash dice el texto final con voz clara.
6. **Validación:** la persona confirma o corrige, y eso se guarda en la memoria.

### Memoria del agente

Por persona, persistente:

- **Contactos:** nombre, relación y teléfono (ej.: María, su hija; Juan, su amigo).
- **Vocabulario propio:** medicamentos, lugares, frases que repite.
- **Correcciones validadas:** "Whisper escribió X y la persona quiso decir Y".

**Mejora sin reentrenar:** en cada turno se buscan las correcciones validadas más parecidas y se le pasan al LLM como ejemplos, junto con los contactos y el vocabulario. Funciona desde la primera validación.

### Integración con WhatsApp (Kapso)

"Mandale a María que llego tarde" → el agente resuelve quién es María desde la memoria → genera la nota de voz → la manda por WhatsApp.

- Plan gratuito de Kapso: número sandbox, API key y 2.000 mensajes.
- Las notas de voz tienen que ser `.ogg` con códec OPUS (convertir la salida de Gemini con ffmpeg).
- Solo se pueden mandar mensajes libres dentro de las 24 h posteriores a que el destinatario le escriba al número. Para la demo, "María" le escribe al bot antes de presentar.
- El mensaje sale del número del bot, no del WhatsApp personal de la persona. Que cada persona conecte su propio número queda como trabajo futuro.

---

## La IA en el proyecto

La IA está en cada paso, y cada capa resuelve un problema distinto:

1. **Reconocimiento adaptado:** Whisper adaptado a habla atípica en español.
2. **Interpretación:** un LLM reconstruye lo que la transcripción no captó, usando el contexto de la frase.
3. **Agente con memoria:** recuerda contactos, vocabulario y correcciones validadas de cada persona y los usa en cada turno, así que mejora con el uso sin reentrenar.
4. **Decisión:** según su confianza, el agente actúa, confirma u ofrece opciones, para no equivocarse en silencio.
5. **Voz:** Gemini Flash convierte el resultado en voz clara.

---

## Resultados

Medidos sobre los hablantes de test de S-DiverSe (split por hablante).

| Condición | Descripción | WER test |
| --- | --- | --- |
| A | whisper-small base | [completar] |
| B | LLM sobre A | [completar] |
| C | whisper-small + LoRA | [completar] |
| D | LLM sobre C | 37 % |
| Turbo | whisper-large-v3-turbo | [completar] |
| **Turbo + reglas** | **whisper-large-v3-turbo + reglas de corrección** | **31 %** |

El mejor pipeline hasta ahora es **turbo + reglas** (31 % de WER contra 37 % de D). Los números por enfermedad, por inteligibilidad y por hablante están en `resultados/tabla_*.csv`.

---

## Estructura del proyecto

| Archivo | Qué hace | GPU |
| --- | --- | --- |
| `notebook_sdiverse_whisper.ipynb` | Pipeline principal: condiciones A, B, C, D, LoRA y referencia turbo | T4 |
| `notebook_contexto_llm.ipynb` | Mide si el LLM corrige mejor con contexto de la persona | No |
| `notebook_demo_turbo.ipynb` | Pipeline de demo: turbo + reglas + LLM, con app de Gradio | No |
| `sdiverse_data.zip` | 444 audios + metadatos (293 MB) | — |

Salidas en `Mi unidad/Shippear/sdiverse_hackathon/`:

- `splits.csv`: split train/val/test por hablante y los folds de la validación cruzada.
- `resultados/tabla_*.csv`: WER total, por enfermedad, por inteligibilidad y por hablante.
- `resultados/wer_por_segmento_A.csv`: WER de A por segmento, de peor a mejor.
- `resultados/transcripciones_val_test.csv`: todas las transcripciones lado a lado.
- `resultados/pred_A.csv`, `pred_C.csv`, `pred_ref_turbo.csv`: transcripciones.
- `resultados/cache_llm.json`: caché de respuestas del LLM.
- `lora/principal/adaptador_final/`: el adaptador LoRA (~25 MB).
- `demo/`: 5 audios de test con `demo.csv`.
- `demo_turbo/`: 5 audios de test donde turbo solo falla y el pipeline acierta.

---

## Cómo correrlo en Google Colab

### Notebook principal

1. **Datos:** subí el zip a `Mi unidad/Shippear/` (el notebook busca el `.zip` que contiene `s-diverse.tsv`).
2. **Notebook:** en colab.research.google.com → *Subir* → el `.ipynb`.
3. **GPU:** *Entorno de ejecución → Cambiar tipo de entorno → T4 GPU*.
4. **API key del LLM:** ícono de llave (*Secrets*) → agregá `GROQ_API_KEY` (de console.groq.com) y activá "Acceso al notebook". Sin clave, corre igual pero salta B y D.
5. *Entorno de ejecución → Ejecutar todas*. Aceptá el permiso para montar Drive.
6. **Dejá la pestaña abierta y a la vista.** Colab gratis corta las sesiones inactivas o en segundo plano.

Correlo directamente completo: al terminar, el entrenamiento marca `LISTO.json` y una segunda corrida lo saltaría.

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

Colab gratis tiene un cupo de GPU que varía. Si te niega la T4, hay que esperar o usar otra cuenta.

#### Si Colab se desconecta

Reconectá, elegí T4 de nuevo y *Ejecutar todas*. Cada etapa reutiliza lo guardado:

- `pred_A.csv`, `pred_C.csv`, `pred_ref_turbo.csv`: si existen, no se recalculan.
- `cache_llm.json`: las respuestas del LLM no se pagan dos veces.
- `trozos_entrenamiento.csv`: la alineación forzada.
- `lora/principal/checkpoint-*`: el entrenamiento retoma desde el último checkpoint.
- `lora/principal/LISTO.json`: si existe, el entrenamiento se salta.

**Para reentrenar:** borrá en Drive `lora/principal/` y `resultados/pred_C.csv`. Si cambiaste el LLM o el prompt, no hace falta borrar nada: la caché distingue por modelo y prompt.

#### Cambiar el proveedor de LLM

- **Groq (gratis, por defecto):** `GROQ_API_KEY` en los Secrets. Si Groq ya no ofrece `llama-3.3-70b-versatile`, cambiá `llm_modelo` por otro de console.groq.com/docs/models. Si avisa que algunas llamadas fallaron, volvé a correr la celda.
- **Anthropic:** en `CFG` hay una línea lista para descomentar (`claude-haiku-5-5`, secreto `ANTHROPIC_API_KEY`). Más potente: `llm_modelo="claude-opus-5-5"`.
- **OpenAI u otro compatible:** `llm_proveedor="openai_compatible"`, `llm_modelo="..."`, `llm_base_url=` la URL del proveedor (`None` para OpenAI), clave en `OPENAI_API_KEY`.
- **Sin LLM:** `llm_proveedor="ninguno"` (salta B y D).

### Notebook de contexto (`notebook_contexto_llm.ipynb`)

Mide si el LLM corrige mejor cuando sabe quién es la persona. El contexto se simula con lo que esa persona dijo en sus *otros* segmentos, nunca con el evaluado.

- No necesita GPU.
- Necesita que el principal ya haya generado `pred_A.csv` y `splits.csv`. Si existe `pred_C.csv`, compara también D contra D+contexto.
- Usa `GROQ_API_KEY`. Hace unas 400 llamadas; en el plan gratuito puede tardar 10–30 min.
- Incluye `corregir_con_perfil(texto, perfil)` para la demo con un perfil escrito a mano.

### Notebook de demo (`notebook_demo_turbo.ipynb`)

El pipeline que mejor rindió: turbo + reglas (31 % de WER en test, contra 37 % de D).

- No necesita GPU: la transcripción la hace Groq con `whisper-large-v3-turbo`.
- Secretos: `GROQ_API_KEY` (transcripción) y `OPENAI_API_KEY` (LLM, `gpt-4.1-mini`).
- Mide turbo + reglas + LLM sobre los hablantes de test y usa el LLM en la demo solo si mejora en validación.
- Guarda en `demo_turbo/` 5 audios donde turbo solo falla y el pipeline acierta.
- Termina con una app de Gradio (link público, válido 72 h, funciona desde el celular): audio + perfil opcional → Whisper sin corregir contra nuestro sistema, lado a lado.

---

## Estado

**Hecho**
- Pipeline de evaluación con split por hablante y WER por enfermedad, inteligibilidad y hablante.
- Whisper-small con LoRA entrenado sobre S-DiverSe.
- Corrección con LLM, con y sin contexto de la persona.
- Pipeline turbo + reglas (el mejor resultado) con app de Gradio.

**Falta**
1. **Pipeline de voz:** conectar el ASR, Gemini Flash TTS y la conversión a nota de voz; medir la latencia.
2. **Agente y memoria:** memoria por persona, corrección con ejemplos de la memoria, detección de intención, umbrales de actuar/confirmar/opciones, perfil de la persona de la demo.
3. **Interfaz:** botón grande para hablar, sí/no y opciones, audio de respuesta, panel de "lo que aprendí".
4. **WhatsApp con Kapso:** cuenta, número, envío de notas de voz y ventana de 24 h abierta para la demo.
5. **Evaluación, demo y pitch:** completar los números, demo de "antes y después" (la frase falla, se valida y sale bien), video de respaldo, slides y ensayo.

### Checkpoints
- **30 % del tiempo:** cada parte funciona por separado.
- **50 %:** todo conectado de punta a punta. Se congela el MVP.
- **75 %:** WhatsApp, panel de memoria y pulido.
- **Final:** solo demo, video y ensayo.

---

## Cuidados

- Nunca usar segmentos ni hablantes de test para entrenar, elegir umbrales o armar la memoria evaluada.
- Son datos de salud y de voz: no mandar audios a servicios innecesarios. La transcripción con turbo y la corrección con LLM corren en la nube (Groq, OpenAI); el adaptador LoRA de whisper-small es la alternativa que puede correr local.
- Revisar la licencia de S-DiverSe antes de usar los audios en una demo pública.
- Tener siempre un video de respaldo de la demo: Colab y los links de Gradio pueden caerse.

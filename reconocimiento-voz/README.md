# Whisper para habla con disartria en español (S-DiverSe)

Reconocimiento de voz para personas con **ELA, Parkinson o secuelas de ACV**. Nuestro sistema baja el error de
transcripción de Whisper de **73 % a 31 %** en personas que nunca escuchó.

El hallazgo central: con habla disártrica, Whisper **inventa texto**. Entra en bucles ("no, no, no, no...") y agrega
cientos de palabras que nadie dijo. Eliminar esas alucinaciones es lo que más mejora el resultado.

La [guía del proyecto](GUIA.md) explica en detalle las métricas, cómo hacer la demo en vivo y dónde está cada archivo.

## Resultados

Error por palabra (WER, menor es mejor) sobre 6 personas de test que ningún modelo vio al entrenar: 98 fragmentos,
2.430 palabras.

| Sistema | WER |
|---|---|
| whisper-small | 88,4 % |
| whisper-small + reglas | 43,6 % |
| whisper-small + reglas + LLM | 41,4 % |
| whisper-small con fine-tuning LoRA | 55,8 % |
| LoRA + reglas | 38,5 % |
| LoRA + reglas + LLM | 36,9 % |
| whisper-large-v3-turbo | 73,0 % |
| turbo + reglas | 31,1 % |
| **turbo + reglas + LLM (sistema final)** | **30,7 %** |

Por enfermedad:

| Enfermedad | Personas en test | Fragmentos | whisper-small | turbo | Sistema final |
|---|---|---|---|---|---|
| ELA | 3 | 47 | 130,7 % | 107,2 % | 42,4 % |
| Parkinson | 1 | 27 | 46,7 % | 19,3 % | 18,3 % |
| ACV | 2 | 24 | 21,2 % | 145,0 % | 18,1 % |

Qué muestran los números:

- **Las reglas hacen la mayor parte del trabajo:** bajan a turbo de 73 % a 31 %. El 58 % de los errores de
  whisper-small eran palabras inventadas.
- **El LLM ayuda poco pero en la dirección correcta:** +2,1 puntos sobre whisper-small (IC 95 %: 1,8 a 3,9) y
  +0,4 sobre turbo (IC 0,0 a 1,2).
- **El fine-tuning ayuda a algunas voces** (una paciente con ELA pasa de 27 % a 8 %), pero el modelo chico entrenado
  no alcanza al grande: queda 5,3 puntos atrás (IC 2,3 a 6,6).
- **El contexto del usuario** (simulado con lo que la persona dijo en otros fragmentos) casi no cambió el resultado:
  de 0 a 0,9 puntos.
- **Límite:** cuando Whisper solo produce un bucle, el sistema deja de inventar, pero no recupera lo que se dijo.

Los intervalos de confianza (IC 95 %) se calcularon remuestreando personas: si no cruzan 0, la mejora no depende de
una sola persona. Con 6 personas de test, los resultados por enfermedad son indicativos (Parkinson es una sola persona).

Tablas completas (por persona y por inteligibilidad) y transcripciones lado a lado en [`resultados/`](resultados/).

## Qué hicimos

**Datos.** [S-DiverSe](https://github.com/ferugit/s-diverse) (López et al., Interspeech 2026): 3,2 h de habla
espontánea en español de 22 personas con ELA (10), Parkinson (8) y ACV (4), con 444 fragmentos de entrevistas de
YouTube transcriptos a mano.

**Evaluación sin trampa.** Separamos por persona, no por fragmento: 12 personas para entrenar, 4 para validar y 6
para test. El test cubre las 3 enfermedades y los 5 niveles de inteligibilidad. El mejor enfoque se eligió en
validación, no en test.

**Métrica.** WER = (palabras cambiadas + faltantes + inventadas) / palabras dichas. Puede superar el 100 % cuando
Whisper inventa más palabras de las que se dijeron. Antes de comparar, el texto se normaliza igual que en el paper:
minúsculas, sin puntuación, números en palabras; las tildes se conservan.

**Enfoques comparados:**

1. **Reglas anti-alucinación** (del paper): reducen palabras estiradas ("jajajaja" → "ja"), palabras repetidas y
   frases repetidas. Solo borran, nunca agregan.
2. **Corrección con LLM:** recibe hasta 5 versiones posibles de Whisper y 3 ejemplos de entrenamiento, y devuelve la
   frase más probable. Una salvaguarda descarta la respuesta si cambia demasiado el largo del texto.
3. **Fine-tuning LoRA** de whisper-small (r=16, encoder y decoder, fp16 en una T4). Los fragmentos de más de 30 s se
   cortaron con alineación forzada (wav2vec2 en español).
4. **Contexto del usuario** para el LLM, simulado con otros fragmentos de la misma persona.
5. **Whisper grande** (`whisper-large-v3-turbo`) con reglas y LLM: el sistema final.

LLM usados: `openai/gpt-oss-120b` (Groq) en el notebook principal; `gpt-4.1-mini` (OpenAI) en los de contexto y demo.

## Cómo correrlo

Los audios no están en el repo (ver Licencia). Para obtenerlos, cloná [S-DiverSe](https://github.com/ferugit/s-diverse)
y corré su script de descarga (necesita yt-dlp, Deno y ffmpeg). Después armá un zip con `s-diverse.tsv` y la carpeta
`audio/` y subilo a Google Drive en `Mi unidad/Shippear/`.

| Notebook | Qué hace | GPU | Tiempo aprox. |
|---|---|---|---|
| [`notebook_sdiverse_whisper.ipynb`](notebooks/notebook_sdiverse_whisper.ipynb) | Experimento completo: whisper-small, reglas, LLM, LoRA, tablas | T4 | 1–1,5 h |
| [`notebook_contexto_llm.ipynb`](notebooks/notebook_contexto_llm.ipynb) | Corrección con y sin contexto del usuario | No | 10–30 min |
| [`notebook_demo_turbo.ipynb`](notebooks/notebook_demo_turbo.ipynb) | Sistema final + demo en vivo con Gradio | No | ~5 min |

Todos corren en Google Colab y se ejecutan en ese orden. Claves en *Secrets* de Colab: `GROQ_API_KEY` y
`OPENAI_API_KEY`. Cada notebook guarda sus resultados en Drive y, si la sesión se corta, retoma desde donde quedó.

**Demo en vivo:** `notebook_demo_turbo.ipynb` levanta una página donde se graba o sube un audio y se ve lado a lado
"Whisper sin corregir" y "nuestro sistema". La transcripción la hace Groq con whisper-large-v3-turbo, así que no
necesita GPU.

## Próximos pasos

- Fine-tuning LoRA del Whisper grande: el modelo chico entrenado ya mejoró mucho a algunas voces.
- Más datos de ACV y de mujeres, los grupos más chicos del corpus.
- Probar el contexto con perfiles reales de usuario en lugar de la simulación.
- Avisar "no se entendió" cuando Whisper entra en bucle, en lugar de devolver un texto vacío.

## Licencia y cita

Los audios pertenecen a los videos originales de YouTube y no se redistribuyen acá. Los autores de S-DiverSe publican
solo anotaciones y links. Este repo contiene únicamente código, métricas y transcripciones de test.

> López, F., Ibañez, F., Martínez, A., Alonso, I., Gómez, P., Kesiraju, S. y Luque, J. (2026).
> *S-DiverSe: Spanish Diverse Speech*. Interspeech 2026. [arXiv:2607.03207](https://arxiv.org/abs/2607.03207)

# S-DiverSe × Whisper: cómo correrlo en Google Colab

Notebook: `notebook_sdiverse_whisper.ipynb`. Datos: `sdiverse_data.zip` (293 MB, 444 audios + metadatos).

## Pasos

1. **Datos:** subí el zip a `Mi unidad/Shippear/` (el nombre del archivo no importa: el notebook busca el `.zip` que contiene `s-diverse.tsv`).
2. **Notebook:** en colab.research.google.com → *Subir* → el `.ipynb`.
3. **GPU:** *Entorno de ejecución → Cambiar tipo de entorno → T4 GPU*.
4. **API key del LLM:** ícono de llave en la barra izquierda (*Secrets*) → agregá `GROQ_API_KEY` (clave de console.groq.com) y activá
   "Acceso al notebook". Sin clave, el notebook corre igual pero salta B y D.
5. *Entorno de ejecución → Ejecutar todas*. Aceptá el permiso para montar Drive.
6. **Dejá la pestaña abierta y a la vista.** Colab gratis corta las sesiones inactivas o que quedan en segundo plano
   mucho tiempo.

Correlo directamente completo, sin una "corrida de prueba" con menos épocas: al terminar, el entrenamiento marca
`LISTO.json` y una segunda corrida lo saltaría (ver abajo cómo forzar el reentrenamiento).

## Tiempos aproximados en T4

Son estimaciones, no medidas en GPU. En local solo llegué a probar las primeras celdas.

| Etapa | Tiempo |
|---|---|
| Instalación + descompresión | 3–5 min |
| A: whisper-small sobre los 444 segmentos (+5 hipótesis por segmento corto) | 10–20 min |
| B: LLM sobre val+test (~120 llamadas en paralelo) | 2–5 min |
| Alineación forzada de segmentos largos | 5–10 min |
| Entrenamiento LoRA (hasta 8 épocas con early stopping) | 15–30 min |
| C y D sobre val+test | 5–8 min |
| Referencia whisper-large-v3-turbo sobre val+test | 3–6 min |
| **Total** | **~1 – 1,5 h** |
| Validación cruzada opcional (`CFG["ejecutar_cv"]=True`) | +1 – 1,5 h, no recomendada en Colab gratis |

Colab gratis tiene un cupo de GPU que no es público y varía. Si después de varias horas de uso te niega la T4,
hay que esperar o usar otra cuenta de Google.

## Si Colab se desconecta

Reconectá, volvé a elegir T4 si hace falta y *Ejecutar todas* otra vez. Cada etapa guarda su resultado en
`Mi unidad/Shippear/sdiverse_hackathon/` y lo reutiliza:
- `resultados/pred_A.csv`, `pred_C.csv`, `pred_ref_turbo.csv`: transcripciones. Si existen, no se recalculan.
- `resultados/cache_llm.json`: respuestas del LLM. No se pagan dos veces.
- `trozos_entrenamiento.csv`: la alineación forzada.
- `lora/principal/checkpoint-*`: un checkpoint por época. El entrenamiento **retoma desde el último** (pierde a lo sumo
  la época en curso).
- `lora/principal/LISTO.json`: si existe, el entrenamiento se salta.

**Para reentrenar** (por ejemplo, si cambiaste un hiperparámetro): borrá en Drive la carpeta `lora/principal/` y el
archivo `resultados/pred_C.csv`. Si cambiaste el LLM o el prompt, no hace falta borrar nada: la caché distingue por
modelo y prompt.

## Qué produce

En `Mi unidad/Shippear/sdiverse_hackathon/`:
- `splits.csv`: split train/val/test por hablante y los folds de la validación cruzada.
- `resultados/tabla_*.csv`: WER total, por enfermedad, por inteligibilidad y por hablante.
- `resultados/wer_por_segmento_A.csv`: WER de A por segmento, de peor a mejor.
- `resultados/transcripciones_val_test.csv`: todas las transcripciones lado a lado.
- `lora/principal/adaptador_final/`: el adaptador LoRA (~25 MB).
- `demo/`: 5 audios de test con `demo.csv`.

## Demo en vivo

La sección 11 abre una app de Gradio con un link público (`...gradio.live`, válido 72 h) que funciona desde el celular.
Si reconectás Colab el día de la demo, *Ejecutar todas* carga todo del caché en pocos minutos, sin reentrenar.

## Cambiar el proveedor de LLM

**Groq (gratis):** creá una clave en console.groq.com → *API Keys*, guardala en los *Secrets* de Colab como
`GROQ_API_KEY`. Es el proveedor por defecto: no hay que tocar la configuración.
Si Groq ya no ofrece `llama-3.3-70b-versatile`, cambiá `llm_modelo` por otro de console.groq.com/docs/models. El plan
gratuito limita las llamadas por minuto: el notebook espera y reintenta. Si al final avisa que algunas llamadas fallaron,
volvé a correr la celda (las exitosas salen de la caché).

Otras opciones, en la celda de configuración (`CFG`):
- Anthropic: en la celda de configuración hay una línea lista para descomentar (usa `claude-haiku-5-5`, secreto `ANTHROPIC_API_KEY`). Más potente:
  `llm_modelo="claude-opus-5-5"`.
- OpenAI u otro compatible: `llm_proveedor="openai_compatible"`, `llm_modelo="..."`, `llm_base_url=` la URL del
  proveedor (`None` para OpenAI), con la clave en `OPENAI_API_KEY`.
- Sin LLM: `llm_proveedor="ninguno"` (salta B y D).

## Notebook complementario: corrección con contexto del usuario

`notebook_contexto_llm.ipynb` mide si el LLM corrige mejor cuando sabe quién es la persona. El contexto se simula con
lo que esa persona dijo en sus *otros* segmentos, nunca con el segmento evaluado.
- **No necesita GPU.** Abrilo en otra pestaña de Colab con entorno de CPU.
- Necesita que el principal ya haya generado `resultados/pred_A.csv` y `splits.csv` (los primeros ~20–30 min).
  Si además ya existe `pred_C.csv`, compara también D contra D+ctx.
- Usa Groq por defecto, igual que el principal (mismo secreto `GROQ_API_KEY`, con "Acceso al notebook" activado).
- Hace unas 400 llamadas al LLM, con mensajes más largos por el contexto. En el plan gratuito de Groq puede tardar
  10–30 min por los límites por minuto. Si avisa que algunas fallaron, volvé a correr la celda.
- Al final tiene `corregir_con_perfil(texto, perfil)` para la demo de producto con un perfil escrito a mano.

## Notebook de demo: Whisper grande + reglas + LLM (sin GPU)

`notebook_demo_turbo.ipynb` es el pipeline que mejor rindió (turbo + reglas: 31 % de WER en test, contra 37 % de D).
- **No necesita GPU:** la transcripción en vivo la hace Groq con `whisper-large-v3-turbo`. Usá un entorno de CPU.
- Secretos con "Acceso al notebook": `GROQ_API_KEY` (transcripción) y `OPENAI_API_KEY` (LLM, `gpt-4.1-mini`).
- Primero mide turbo + reglas + LLM sobre los mismos hablantes de test (~120 llamadas al LLM, unos minutos) y usa el
  LLM en la demo solo si mejora en validación.
- Elige 5 audios de test donde turbo solo falla y el pipeline acierta, y los guarda en `demo_turbo/`.
- Termina con la app de Gradio (link público): audio + perfil opcional del usuario → Whisper sin corregir contra
  nuestro sistema, lado a lado.

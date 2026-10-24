# S-DiverSe × Whisper: guía del proyecto

Oct 24, 2026 · @Fede

## Resumen

Nuestro mejor sistema baja el error de transcripción de Whisper de **73 % a 31 %** en personas con ELA, Parkinson o secuelas de ACV que el sistema nunca escuchó. El problema principal que resolvimos: con habla disártrica, Whisper **inventa texto** (entra en bucles como "no, no, no, no..." y agrega cientos de palabras que nadie dijo).

El sistema final es simple: Whisper grande (`whisper-large-v3-turbo`) + reglas que eliminan las repeticiones inventadas + un LLM que corrige palabras dudosas. No requiere entrenar nada y corre sin GPU. También probamos adaptar un Whisper chico con fine-tuning (LoRA): ayuda mucho a algunas voces, pero no alcanza al modelo grande.

Lo que todavía no resolvemos: entender lo que Whisper no entendió. Cuando Whisper solo produce un bucle, el sistema deja de inventar, pero no adivina lo que la persona dijo.

## El dataset y de dónde salen los audios

Usamos **S-DiverSe** (López et al., Interspeech 2026): 3,2 horas de habla espontánea en español, 22 personas, 444 fragmentos con transcripción humana. Son entrevistas y documentales de YouTube, no grabaciones de laboratorio.

| Enfermedad | Personas | Fragmentos | Horas |
| --- | --- | --- | --- |
| ELA | 10 | 252 | 2,51 |
| Parkinson | 8 | 111 | 0,52 |
| ACV | 4 | 81 | 0,18 |

Cada fragmento trae: sexo, enfermedad e **inteligibilidad** (qué tan fácil es entenderlo: High, High/Medium, Medium, Medium/Low, Low). El 87 % del audio es de hombres y el 78 % de ELA.

**Cómo se obtuvieron los audios.** Los autores publican solo las anotaciones y los links de YouTube ([repositorio](https://github.com/ferugit/s-diverse)). Bajamos los 31 videos con su script (yt-dlp + Deno + ffmpeg) y cortamos los fragmentos: 444 de 444 OK (un video dio error 403 y bajó al reintentar).

**Dónde está cada audio:**

| Qué | Dónde |
| --- | --- |
| Todos los fragmentos (WAV 16 kHz) + metadatos | `Mi unidad/Shippear/sdiverse_data.zip` (adentro: `sdiverse/audio/<Enfermedad>/<ID>.wav` y `s-diverse.tsv`) |
| Copia local | `Desktop/Shippear/data_src/s-diverse/data/audio/` |
| Audios elegidos para la demo con el Whisper grande | `Mi unidad/Shippear/sdiverse_hackathon/demo_turbo/` (8 WAV + `demo_turbo.csv`) |
| Audios elegidos con el modelo chico entrenado | `Mi unidad/Shippear/sdiverse_hackathon/demo/` (5 WAV + `demo.csv`) |

El ID dice quién habla: `ALS_M06_07` = persona con ELA, hombre n.º 6, fragmento 7. Para sacar cualquier otro audio del zip, en Colab: `ZIP.read(nombres["ALS_M06_07"])` (celda de la sección 3 del notebook de demo).

## Qué hicimos

Comparamos varias formas de mejorar a Whisper, todas evaluadas sobre las mismas 6 personas de test.

| Enfoque | Qué es | Necesita GPU |
| --- | --- | --- |
| A | whisper-small tal cual (el punto de partida) | Sí |
| Reglas (PP) | 3 reglas del paper que borran repeticiones: palabras estiradas ("jajajaja" → "ja"), palabras repetidas seguidas y frases repetidas seguidas. Solo borran, nunca agregan | No |
| B | Reglas + un LLM que recibe hasta 5 versiones posibles de Whisper y devuelve la frase más probable | No |
| C | whisper-small adaptado a estas voces con fine-tuning LoRA | Sí, para entrenar |
| D | C + reglas + LLM | Sí |
| Contexto | B y D con información sobre la persona (simulada con lo que dijo en otros fragmentos) | No |
| **Final** | **Whisper grande (turbo) + reglas + LLM** | **No** (Groq lo corre en sus servidores) |

**Cómo evitamos hacer trampa.** Separamos las personas, no los fragmentos:

- **Test:** 6 personas (98 fragmentos) que ningún modelo vio al entrenar. Cubren las 3 enfermedades y los 5 niveles de inteligibilidad.
- **Validación:** 4 personas (22 fragmentos), usadas para frenar el entrenamiento y elegir el mejor enfoque.
- **Entrenamiento:** las 12 personas restantes (2,7 h).

Si separáramos por fragmento, el modelo se evaluaría con voces que ya escuchó y los números saldrían inflados.

**Lo que aprendimos del paper.** Los autores adaptaron Whisper con *otros* datos (inglés, frases leídas en hospital) y empeoró en S-DiverSe. Lo que mejor les funcionó fueron las reglas. Nosotros probamos algo que ellos no: entrenar con las propias personas de S-DiverSe.

## Qué significan las métricas

**WER (Word Error Rate, tasa de error por palabra)** mide cuántas palabras hay que corregir para que la transcripción quede igual a la humana. Menor es mejor: 0 % es perfecto.

```latex
\text{WER} = \frac{S + D + I}{N}
```

- **S (sustituciones):** palabras cambiadas. Dijo "paresia", Whisper escribió "parecia".
- **D (borrados):** palabras dichas que faltan.
- **I (inserciones):** palabras que Whisper agregó y nadie dijo.
- **N:** palabras de la transcripción humana.

Ejemplo: la persona dice 10 palabras y Whisper cambia 2 y omite 1 → WER = 3/10 = 30 %. A grandes rasgos, 30 % significa que se entiende la idea pero hay que corregir 1 de cada 3 o 4 palabras.

**¿Cómo puede pasar del 100 %?** Por las inserciones: si la persona dice 10 palabras y Whisper escribe "no, no, no..." 200 veces, son 200 errores sobre 10 palabras = 2.000 %. Por eso un WER enorme casi siempre significa *alucinación*, no "no entendió nada".

**Antes de comparar, normalizamos el texto** igual que el paper: minúsculas, sin puntuación, sin `<unk>` (marca de "inaudible"), números escritos en palabras ("2009" → "dos mil nueve"). Las tildes se conservan ("está" ≠ "esta"); sin tildes el WER baja apenas 0,5 puntos.

**Cómo se suma.** Errores de todos los fragmentos sobre palabras de todos los fragmentos (no promedio de porcentajes). Así un fragmento de 3 palabras no pesa lo mismo que uno de 300. Cada tabla dice cuántos fragmentos, personas y palabras hay detrás.

**Intervalo de confianza (IC 95 %).** Con solo 6 personas, el resultado depende de quiénes tocaron. Repetimos el cálculo miles de veces sorteando personas al azar: si el intervalo de una mejora **no cruza 0**, la mejora no se explica por una persona con suerte. Ejemplo: "mejora 6,7 puntos (IC 2,2 a 11,2)" = mejora real; "0,4 puntos (IC 0,0 a 1,2)" = mejora mínima, apenas distinguible de nada.

**Inteligibilidad.** Es la etiqueta de qué tan fácil es entender a la persona. Ojo: casi todas las personas tienen un solo nivel, así que "WER por inteligibilidad" es en la práctica "WER de 1 o 2 personas".

## Resultados

El sistema final (Whisper grande + reglas + LLM) es el mejor: **30,7 %** de error en test, contra 73,0 % del Whisper grande solo y 88,4 % de whisper-small.

&#91;embedded content: resultados/transcripciones\_turbo\_llm.csv y tabla\_total.csv · test, 6 personas, 98 fragmentos, 2.430 palabras\]

**Qué dicen los números:**

- **Las reglas hacen casi todo el trabajo.** Solo ellas bajan el Whisper grande de 73 % a 31 %, y whisper-small de 88 % a 44 %. El 58 % de los errores originales eran palabras inventadas.
- **El LLM ayuda poco pero en la dirección correcta.** Sobre whisper-small mejora 2,1 puntos (IC 1,8 a 3,9); sobre el grande, 0,4 puntos (IC 0,0 a 1,2). En el grande corrigió 28 fragmentos: mejoró 11 y empeoró 4.
- **El fine-tuning ayuda, pero no alcanza al modelo grande.** D mejora a "whisper-small + reglas" en 6,7 puntos (IC 2,2 a 11,2), pero queda 5,3 puntos por detrás del sistema final (IC 2,3 a 6,6, mismo LLM). Entrenó en 6,5 minutos y empezó a memorizar desde la segunda vuelta.
- **El contexto simulado del usuario casi no cambió nada:** 0 puntos sobre B y 0,9 sobre D (IC 0,3 a 1,3).

**Por enfermedad** (pocas personas por grupo: leer con cuidado):

| Enfermedad | Personas en test | Fragmentos | whisper-small | Whisper grande | Sistema final |
| --- | --- | --- | --- | --- | --- |
| ELA | 3 | 47 | 130,7 % | 107,2 % | 42,4 % |
| Parkinson | 1 | 27 | 46,7 % | 19,3 % | 18,3 % |
| ACV | 2 | 24 | 21,2 % | 145,0 % | 18,1 % |

En ELA y ACV el Whisper grande pasa del 100 % porque alucina; en ACV, una persona con fragmentos de una sola palabra ("silla") le hizo escribir cientos de "Z-Z-Z". Las tablas completas, por persona y por inteligibilidad, están en `RESULTADOS.md`.

## Cómo hacer la demo en vivo

La demo es una página web (Gradio): se graba o sube un audio y se ven lado a lado "Whisper grande sin corregir" y "Nuestro sistema". Corre en Colab **sin GPU** y tarda unos 5 a 10 segundos por audio.

**Preparación (15 minutos antes):**

1. Abrí `notebook_demo_turbo.ipynb` en Colab (está en Drive). Entorno de ejecución: **CPU** (no hace falta GPU).
2. Revisá los secretos (ícono de llave): `GROQ_API_KEY` y `OPENAI_API_KEY`, ambos con "Acceso al notebook" activado.
3. *Entorno de ejecución → Ejecutar todas*. Tarda unos minutos; las respuestas del LLM salen de la caché, no se pagan de nuevo.
4. Debajo de la última celda aparece el link `https://....gradio.live`. Abrilo en el navegador de la presentación (también anda en el celular).
5. Probá el ejemplo principal y una grabación con tu micrófono **antes** de subir al escenario.
6. Dejá la pestaña de Colab abierta: el link vive mientras esa sesión esté activa.

**Guión sugerido (3 minutos):**

1. **El problema.** Poné ALS\_M06\_07 (ELA, inteligibilidad baja, 31 s). Que el público escuche: es difícil de entender.
2. **Whisper falla.** Mostrá la columna izquierda: Whisper entiende el principio y después inventa "no, no, no, no..." (215 palabras que nadie dijo).
3. **Nuestro sistema.** La columna derecha conserva lo que sí se entendió y elimina lo inventado: error de 517 % a 54 %.
4. **El número.** En 6 personas que el sistema nunca escuchó: de 73 % a 31 % de error.
5. **La visión (opcional).** Escribí un perfil en el campo "Perfil del usuario" ("Se llama Marta, su hija es Lucía") y mostrá cómo el LLM usa ese contexto. Aclará que es la idea de producto, no algo que medimos.

**Audios para usar:**

| Audio | Qué muestra | Dónde mostrarlo |
| --- | --- | --- |
| ALS\_M06\_07 (31 s, ELA) | Whisper grande inventa 215 palabras en bucle; el sistema las elimina | App en vivo |
| PARKINSON\_M01\_07\_01 (4 s) | whisper-small: "sí, sí, no, no, no..." (1.809 %) → sistema 27 % | Diapositiva |
| ALS\_F02\_04 (15 s, ELA) | whisper-small escribe solo "y" → sistema 5 % | Diapositiva |
| STROKE\_F01\_02 (8 s, ACV) | Riesgo del LLM: cambia "paresia" (correcto) por "parálisis" | Diapositiva, si preguntan por riesgos |

Los dos de whisper-small van en diapositiva porque la app compara contra el Whisper grande.

**Plan B (si algo falla en vivo):**

- **La API de Groq no devuelve lo mismo que evaluamos.** En una prueba agregó una frase que nadie dijo, y puede que ALS\_M06\_07 no entre en bucle esa vez. Tené lista una diapositiva con el ejemplo y sus números.
- **Se cayó la sesión de Colab.** *Ejecutar todas* de nuevo: en 2 o 3 minutos hay link nuevo.
- **Sin internet o sin Groq.** Mostrá las transcripciones guardadas en `Mi unidad/Shippear/sdiverse_hackathon/demo_turbo/demo_turbo.csv` y reproducí los WAV desde Drive.

## Qué decir en el pitch y qué no prometer

**Mensaje en una frase:** "Whisper falla con habla disártrica sobre todo porque inventa texto; nuestro sistema elimina esas alucinaciones y corrige con un LLM, y baja el error de 73 % a 31 % en personas que nunca escuchó."

**Sí se puede decir:**

- El mayor problema son las alucinaciones: el 58 % de los errores de Whisper son palabras inventadas.
- Evaluamos con personas que el sistema nunca escuchó (separación por hablante).
- El fine-tuning ayudó mucho a algunas voces: una paciente con ELA pasó de 27 % a 8 %.
- Coincide con lo que encontró el paper de S-DiverSe (Interspeech 2026).

**No prometer:**

- **"Entiende lo que Whisper no entiende".** No: cuando Whisper solo produce un bucle, el sistema deja de inventar pero no recupera lo dicho.
- **"El LLM es la clave".** No: aporta 0,4 puntos sobre las reglas. Lo que más mejora son las reglas.
- **"El contexto del usuario mejora el reconocimiento".** No lo demostramos: con contexto simulado el efecto fue de 0 a 0,9 puntos. Es una hipótesis de producto.
- **Resultados por enfermedad como generales.** Parkinson en test es **una sola persona**; ACV son dos, y una tiene solo 12 palabras en total.

**Preguntas probables:**

| Pregunta | Respuesta |
| --- | --- |
| ¿Y contra un Whisper más grande? | Usamos el grande. Solo, tiene 73 % de error porque alucina; con nuestras reglas, 31 %. |
| ¿Por qué no entrenaron el grande? | Por tiempo de GPU. Es el próximo paso: el chico entrenado mejoró mucho a algunas voces. |
| ¿Es seguro usar un LLM? | Puede "corregir" de más (cambió "paresia" por "parálisis"). Por eso tiene salvaguardas: si cambia demasiado el texto, se descarta su respuesta. |
| ¿Cuántos datos hay? | 3,2 h de 22 personas: poco. Los resultados son indicativos, no clínicos. |

## Próximos pasos

El paso con más potencial es adaptar el Whisper grande con LoRA, porque el chico entrenado ya mejoró mucho a algunas voces.

1. **LoRA sobre `whisper-large-v3-turbo`.** El notebook principal ya lo soporta cambiando `CFG["modelo_base"]`; hace falta un lote más chico (4 con acumulación 4) y \~1 a 1,5 h de T4.
2. **Más datos de ACV y de mujeres.** Son los grupos más chicos (ACV: 0,18 h). El fine-tuning empeoró a una paciente con ACV por falta de ejemplos.
3. **Contexto real del usuario.** Probar con perfiles reales (nombres de la familia, rutinas, vocabulario propio) en vez de la simulación. Es la hipótesis de producto de Buendía y todavía no está demostrada.
4. **Detectar "no entendí".** Cuando Whisper entra en bucle, hoy el sistema devuelve casi nada. Mejor: avisar "no se entendió, ¿podés repetir?" en lugar de un texto vacío.
5. **Validación cruzada.** Medir el modelo entrenado sobre las 22 personas (4 rondas, ya programado en el notebook) para que el número no dependa de quiénes quedaron en test.
6. **Evaluar en vivo.** Medir el WER con la API de Groq sobre el test completo: puede diferir del Whisper que evaluamos en Colab.

## Mapa de archivos

Todo lo generado vive en Drive, en `Mi unidad/Shippear/sdiverse_hackathon/`; los notebooks y documentos están también en `Desktop/Shippear/entregables/`.

**Notebooks (en este orden):**

| Notebook | Para qué | GPU | Tiempo |
| --- | --- | --- | --- |
| `notebook_sdiverse_whisper.ipynb` | Experimento completo: A, reglas, B, entrenamiento LoRA, C, D, tablas | T4 | \~1–1,5 h |
| `notebook_contexto_llm.ipynb` | Mide si el contexto del usuario ayuda al LLM | No | 10–30 min |
| `notebook_demo_turbo.ipynb` | Mide el sistema final y levanta la demo en vivo | No | \~5 min |

Cada notebook guarda lo que calcula en Drive. Si Colab se corta, *Ejecutar todas* retoma desde donde quedó, sin recalcular ni volver a pagar llamadas al LLM.

**Resultados en `sdiverse_hackathon/`:**

| Archivo | Qué tiene |
| --- | --- |
| `splits.csv` | Qué persona está en entrenamiento, validación o test |
| `resultados/tabla_*.csv` | WER por enfoque: total, por enfermedad, por inteligibilidad, por persona |
| `resultados/transcripciones_val_test.csv` | Todas las transcripciones de val y test, lado a lado |
| `resultados/transcripciones_contexto.csv` | Resultados con y sin contexto |
| `resultados/transcripciones_turbo_llm.csv` | Resultados del sistema final |
| `resultados/wer_por_segmento_A.csv` | Error de Whisper por fragmento, de peor a mejor |
| `lora/principal/adaptador_final/` | El modelo entrenado (adaptador LoRA, \~25 MB) |
| `demo_turbo/`, `demo/` | Audios elegidos para la demo |

**Documentos de apoyo** (en `entregables/`): `README.md` (cómo correr cada notebook), `RESULTADOS.md` (todas las tablas), `DECISIONES_Y_RIESGOS.md` (por qué se hizo cada cosa).

**Claves que se usan** (en *Secrets* de Colab): `GROQ_API_KEY` (transcripción en vivo en la demo, y LLM del notebook principal con el modelo `openai/gpt-oss-120b`) y `OPENAI_API_KEY` (LLM `gpt-4.1-mini` en los notebooks de contexto y demo).

## Licencia, cita y limitaciones

**Licencia.** El repositorio de S-DiverSe no incluye licencia. Los autores distribuyen solo anotaciones y links; el audio pertenece a los videos originales de YouTube. Uso: investigación y demo, citando el paper. **No publiques el zip.** Para un uso público o comercial, consultar a los autores (fernando.lopez@telefonica.com).

**Cita:** López, F., Ibañez, F., Martínez, A., Alonso, I., Gómez, P., Kesiraju, S. y Luque, J. (2026). *S-DiverSe: Spanish Diverse Speech*. Interspeech 2026. [arXiv:2607.03207](https://arxiv.org/abs/2607.03207).

**Limitaciones:**

- **Pocas personas.** 6 en test: un hablante atípico mueve el promedio varios puntos. ALS\_M06 domina el error por sus alucinaciones.
- **Desbalance.** ELA es el 78 % del audio y los hombres el 87 %. ACV y mujeres son los resultados menos confiables.
- **Diagnósticos autodeclarados**, tomados de lo que dicen los videos, no de una evaluación clínica.
- **Cortes al segundo.** Algunos fragmentos empiezan o terminan a mitad de palabra.
- **Los videos pueden desaparecer** de YouTube; el zip es nuestra copia local.
- **La demo en vivo usa la API de Groq**, que puede comportarse distinto del Whisper evaluado en Colab.

**Fuentes:** [paper S-DiverSe](https://arxiv.org/abs/2607.03207) · [repositorio con anotaciones y links](https://github.com/ferugit/s-diverse).

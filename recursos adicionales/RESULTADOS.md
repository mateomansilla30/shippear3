# Resultados: S-DiverSe × Whisper

Test: 6 hablantes que ningún modelo vio, 98 segmentos, 2.430 palabras. WER en %; menor es mejor.
El mejor enfoque se eligió en validación (4 hablantes, 22 segmentos): fue **D**.
LLM del notebook principal: `openai/gpt-oss-120b` (Groq). Notebook de contexto: `gpt-4.1-mini` (OpenAI).

## Tabla principal (test)

| Enfoque | WER total | ELA (3 hab., 47 seg.) | Parkinson (1 hab., 27 seg.) | ACV (2 hab., 24 seg.) |
|---|---|---|---|---|
| A: whisper-small | 88,4 | 130,7 | 46,7 | 21,2 |
| A+PP: + reglas del paper | 43,6 | 59,0 | 28,2 | 20,6 |
| B: A+PP + LLM | 41,4 | 56,9 | 26,3 | 16,2 |
| C: whisper-small + LoRA | 55,8 | 81,2 | 29,0 | 26,9 |
| C+PP | 38,5 | 48,3 | 28,5 | 25,6 |
| **D: C+PP + LLM** | **36,9** | **47,8** | 25,5 | 23,1 |
| Ref.: whisper-large-v3-turbo | 73,0 | 107,2 | 19,3 | 145,0 |
| Ref.+PP: turbo + reglas (calculado después) | **31,1** | **42,7** | **18,4** | 20,6 |

WER sin tildes: prácticamente igual (~0,5 puntos menos en todos los enfoques).

## Qué dicen los números

1. **El mayor problema de Whisper son las alucinaciones.** En A, el 58 % de los errores son palabras inventadas
   (inserciones): el modelo se queda en bucle. Solo las reglas del paper bajan el WER de 88 a 44. Esto confirma lo que
   encontró el paper.
2. **Fine-tuning + reglas + LLM (D) es lo mejor sobre whisper-small:** 6,7 puntos mejor que A+PP, con un intervalo de
   confianza del 95 % por hablantes de 2,2 a 11,2 (no cruza 0). La comparación contra A (88 → 37) es real, pero su
   intervalo es enorme (4,6 a 96,8) porque depende sobre todo de un hablante con alucinaciones extremas.
3. **El LLM ayuda poco pero de forma consistente:** B mejora a A+PP en 2,1 puntos (IC 1,8 a 3,9).
4. **El fine-tuning ayuda mucho a algunos hablantes:** ALS_F02 pasa de 27,0 a 7,8 (mejor incluso que turbo, 12,1),
   ALS_M02 de 25,5 a 17,0. Pero **empeora a STROKE_F01** (14,2 → 18,2): hay muy pocos datos de ACV para entrenar.
5. **Hallazgo clave para la demo: whisper-large-v3-turbo + reglas (31,1) le gana a D (36,9),** por 5,7 puntos
   (IC −6,7 a −3,3). Un Whisper 3 veces más grande, solo con las reglas, supera a nuestro modelo chico adaptado.
   Contra turbo *sin* reglas (73,0) sí ganamos, porque turbo también alucina (en STROKE_M02, 1.783 %).
6. **El contexto del usuario (simulado) casi no cambia nada:**
   - Sobre B: 41,1 → 41,0 (IC −0,5 a 0,4: sin efecto).
   - Sobre D: 36,0 → 35,1, una mejora de 0,9 puntos (IC 0,3 a 1,3): pequeña pero consistente. Cambió 51 segmentos, mejoró 23 y empeoró 13.
   - El solapamiento entre el contexto y el segmento evaluado es bajo (1,6 %), así que no hay "trampa".
   - El contexto simulado es débil (fragmentos de la misma entrevista, sin nombres de familiares ni rutinas): un perfil real de usuario podría ayudar más, pero **esto no lo demuestra**.

## Entrenamiento

LoRA r=16 sobre whisper-small. Tardó 6,5 minutos. La mejor pérdida de validación fue en la época 2 (0,79); después
el modelo sobreajustó (pérdida de entrenamiento 0,15, validación subiendo a 0,96) y el *early stopping* lo frenó en la
época 5. Con ~2,7 h de 12 hablantes, el modelo memoriza rápido.

## Cautelas para presentar

- **6 hablantes de test.** Los resultados por enfermedad salen de 1 a 3 personas cada uno: Parkinson es una sola persona.
- **STROKE_M02 tiene 12 segmentos de una palabra cada uno** (12 palabras en total): su WER no es interpretable.
- **ALS_M06 (inteligibilidad baja) domina el promedio** por sus alucinaciones. Sin él y sin STROKE_M02, el WER es:
  A 38,9 → A+PP 26,3 → D 22,3; turbo + reglas 16,2.
- **Inteligibilidad ≈ hablante:** cada nivel corresponde a 1 o 2 personas.

## Pipeline final de la demo: Whisper grande + reglas + LLM

Medido con `notebook_demo_turbo.ipynb` (LLM `gpt-4.1-mini`). Mismos 98 segmentos de test.

| Enfoque | Validación | Test | ELA | Parkinson | ACV |
|---|---|---|---|---|---|
| A: whisper-small | 77,8 | 88,4 | 130,7 | 46,7 | 21,2 |
| D (mismo LLM) | — | 36,0 | 46,4 | 25,2 | 23,8 |
| Turbo solo | 17,0 | 73,0 | 107,2 | 19,3 | 145,0 |
| Turbo + reglas | 17,0 | 31,1 | 42,7 | 18,4 | 20,6 |
| **Turbo + reglas + LLM** | **16,2** | **30,7** | **42,4** | **18,3** | **18,1** |

- Es **el mejor de todos**: 5,3 puntos mejor que D con el mismo LLM (IC 95 % por hablantes: 2,3 a 6,6).
- **Casi todo el beneficio viene de las reglas:** 73 → 31. El LLM agrega solo 0,4 puntos (IC 0,0 a 1,2).
  Cambió 28 segmentos de test: mejoró 11 y empeoró 4.
- Sin los dos hablantes atípicos (ALS_M06 y STROKE_M02): turbo 16,9 → turbo + reglas + LLM 16,1.

### Lo que el sistema hace y lo que no

- **Hace:** cuando Whisper entra en bucle, el sistema borra lo inventado. Ejemplo ALS_M06_07: turbo agrega 215
  palabras ("no, no, no, no...") y su error pasa de 517 % a 54 %, conservando la parte bien transcripta.
- **No hace:** recuperar lo que Whisper no entendió. En los segmentos donde turbo solo produjo un bucle
  ("el mismo, el mismo..."), el sistema deja casi nada: deja de inventar, pero no adivina lo que se dijo.
- **El LLM puede "corregir" de más:** en STROKE_F01_02 la persona dice "paresia" (término médico correcto), turbo
  escribe "parecia" y el LLM lo cambia a "parálisis", que es otra cosa. Es un buen ejemplo para mostrar por qué el
  LLM necesita salvaguardas.
- **En vivo puede diferir:** la API de Groq no siempre devuelve lo mismo que el turbo que evaluamos. En la prueba con
  ALS_F02_03_01 agregó al principio "son así tan famosos", que no está en la referencia.

### Audios recomendados para la demo

| Audio | Qué muestra |
|---|---|
| ALS_M06_07 (31 s, ELA, inteligibilidad baja) | Whisper grande inventa 215 palabras en bucle; el sistema las elimina |
| PARKINSON_M01_07_01 (4 s) | whisper-small: "sí, sí, no, no, no, no..." (1.809 %) → sistema 27 % |
| ALS_F02_04 (15 s) | whisper-small escribe solo "y" → sistema 5 % |
| STROKE_F01_02 (8 s) | Ejemplo honesto de riesgo: el LLM cambia "paresia" por "parálisis" |

Los dos primeros sirven para la app en vivo. Los de whisper-small conviene mostrarlos en una diapositiva, porque la
app compara contra el Whisper grande.

## Mensaje honesto sugerido

> "Whisper falla con habla disártrica sobre todo porque **inventa texto**: entra en bucles y agrega cientos de
> palabras que nadie dijo. Nuestro sistema detecta y elimina esas alucinaciones y corrige con un LLM: con el Whisper
> grande baja el error de 73 % a 31 % en personas que nunca escuchó, y con whisper-small de 88 % a 37 %. Probamos
> también fine-tuning con LoRA: ayuda mucho a algunas voces, pero con 3 horas de datos no alcanza al modelo grande.
> Lo que todavía no resolvemos es entender lo que Whisper no entendió: ahí está el siguiente paso, con más datos y con
> el contexto real de cada usuario."

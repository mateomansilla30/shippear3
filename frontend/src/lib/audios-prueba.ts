// Audios de test de S-DiverSe para la demo de la app (hablantes que ningún modelo vio al entrenar).
// Elegidos con el pipeline en vivo (Groq + reglas): uno donde la confianza sale baja y la app debería preguntar,
// dos donde Whisper cambia palabras con confianza alta y la memoria aprende de la corrección, y uno largo y difícil.
// Los WAV no van al repo por la licencia: copialos de Drive (sdiverse_hackathon/ o del zip) a frontend/public/audios-prueba/<id>.wav.
// `texto` es lo que devolvió el pipeline en vivo (para el modo sin back).

export type AudioPrueba = {
  id: string
  titulo: string
  detalle: string
  referencia: string // lo que dijo la persona (transcripción humana)
  texto: string // lo que devuelve el sistema (para el modo sin back)
}

export const AUDIOS_PRUEBA: AudioPrueba[] = [
  {
    id: "ALS_M06_08_01",
    titulo: "ELA · no está seguro",
    detalle: "10 s · confianza baja: debería preguntar",
    referencia: "Bien, muy bien de ánimo. Con unas fasciculaciones en los hombros, pero bien.",
    texto: "bien muy bien y en octubre",
  },
  {
    id: "STROKE_F01_02",
    titulo: "ACV · aprende una palabra",
    detalle: "8 s · corregí \"parecia\" por \"paresia\" y probá de nuevo",
    referencia: "Y, eh, tuve como secuela una paresia bilateral derecha",
    texto: "tuve como secuela una parecia bilateral derecha",
  },
  {
    id: "ALS_M02_02",
    titulo: "ELA · aprende una frase",
    detalle: "7 s · corregí \"productivo\" y \"un buen\" y probá de nuevo",
    referencia: "Pues diría que soy inteligente, proactivo y que soy muy cabezón.",
    texto: "Pues diría que soy inteligente, productivo y que soy un buen cabezón.",
  },
  {
    id: "ALS_M06_07",
    titulo: "ELA · audio largo",
    detalle: "31 s · inteligibilidad baja",
    referencia:
      "Porque no me entiende muchas veces. Me olvido y hablo rápido, antes me emocionaba, porque yo lloraba porque ella no me entendía. Ahora uso una aplicación que es de un argentino, Matteo Salvatto, se llama \"Háblalo\", la uso con ella para hacer la tarea, por ejemplo.",
    texto:
      "Pues no me entiendo muchas veces. Pues me olvido de hablar rápido. Antes me emocionaba porque yo no me entendía. Ahora uso una aplicación que es un argentino, Mateo Zabato, que no habla o no.",
  },
]

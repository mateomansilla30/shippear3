// Audios de test de S-DiverSe recomendados para la demo (ver reconocimiento-voz/GUIA.md).
// Los WAV no van al repo por la licencia: copialos de Drive (sdiverse_hackathon/ o del zip) a frontend/public/audios-prueba/<id>.wav. Los textos salen de transcripciones_test.csv.

export type AudioPrueba = {
  id: string
  titulo: string
  detalle: string
  referencia: string // lo que dijo la persona (transcripción humana)
  texto: string // lo que devuelve el sistema (para el modo sin back)
}

export const AUDIOS_PRUEBA: AudioPrueba[] = [
  {
    id: "ALS_M06_07",
    titulo: "ELA · audio largo",
    detalle: "31 s · inteligibilidad baja",
    referencia:
      "Porque no me entiende muchas veces. Me olvido y hablo rápido, antes me emocionaba, porque yo lloraba porque ella no me entendía. Ahora uso una aplicación que es de un argentino, Matteo Salvatto, se llama \"Háblalo\", la uso con ella para hacer la tarea, por ejemplo.",
    texto:
      "Pues no me entiendo muchas veces. Pues me olvido de hablar rápido. Antes me emocionaba porque yo no me entendía. Ahora uso una aplicación que me ayudó, un argentino, Mateo Zabato, que no habla, o no.",
  },
  {
    id: "PARKINSON_M01_07_01",
    titulo: "Parkinson · frase corta",
    detalle: "4 s · frase corta",
    referencia: "Si, si no me cabe duda, de hecho ya estoy perdiendo.",
    texto: "Ganará. Sí, no cabe duda, de hecho ya estoy perdiendo.",
  },
  {
    id: "ALS_F02_04",
    titulo: "ELA · casi perfecto",
    detalle: "15 s · casi perfecto",
    referencia:
      "Empezamos a charlar, bueno, acerca de algunos proyectos y demás, y no pensé que iba a tener todo tanta repercusión.",
    texto: "Empezamos a charlar acerca de algunos proyectos y demás y no pensé que iba a tener todo tanta repercusión.",
  },
  {
    id: "STROKE_F01_02",
    titulo: "ACV · paresia",
    detalle: "8 s · el LLM cambia \"paresia\" por \"parálisis\"",
    referencia: "Y, eh, tuve como secuela una paresia bilateral derecha",
    texto: "Tuve como secuela una parálisis bilateral derecha.",
  },
]

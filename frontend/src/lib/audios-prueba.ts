// Audios de test de S-DiverSe para la demo de la app (hablantes que ningún modelo vio al entrenar).
// Destacados: uno de inteligibilidad baja, dos donde la memoria aprende de la corrección
// y uno largo y difícil. El de Parkinson quedó quinto.
// Los WAV están en frontend/public/audios-prueba/<id>.wav (con permiso de los autores de S-DiverSe), cortados con
// los tiempos de data/s-diverse.tsv del repo del dataset. Los 4 primeros son los destacados para la demo.
// `texto` es lo que devolvió el pipeline en vivo (para el modo sin back).

export type AudioPrueba = {
  id: string
  titulo: string
  detalle: string
  referencia: string // lo que dijo la persona (transcripción humana)
  texto: string // lo que devuelve el sistema (para el modo sin back)
  // Si es true, el back usa `texto` en lugar de transcribir.
  demo?: boolean
}

export const AUDIOS_PRUEBA: AudioPrueba[] = [
  {
    id: "ALS_M06_08_01",
    titulo: "ELA · no está seguro",
    detalle: "10 s · inteligibilidad baja",
    referencia: "Bien, muy bien de ánimo. Con unas fasciculaciones en los hombros, pero bien.",
    texto: "Bien, muy bien de ánimo. Con fascinaciones de los hombros, pero bien.",
    demo: true,
  },
  {
    id: "STROKE_F01_02",
    titulo: "ACV · aprende una palabra",
    detalle: "8 s · inteligibilidad media-baja",
    referencia: "Y, eh, tuve como secuela una paresia bilateral derecha",
    texto: "tuve como secuela una parecia bilateral derecha",
  },
  {
    id: "ALS_M02_02",
    titulo: "ELA · aprende una frase",
    detalle: "7 s · inteligibilidad media",
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
  {
    id: "PARKINSON_M01_05",
    titulo: "Parkinson · Y luego pues, me…",
    detalle: "6 s · inteligibilidad alta",
    referencia: "Y luego pues, me suelo ir a rehabilitación a una asociación de párkinson.",
    texto: "Y luego pues me suelo ir a rehabilitación, a la Asociación de Parkinson.",
  },
  {
    id: "STROKE_M02_01",
    titulo: "ACV · Pala",
    detalle: "1 s · inteligibilidad baja",
    referencia: "Pala",
    texto: "Para",
  },
  {
    id: "STROKE_M02_11",
    titulo: "ACV · Lima",
    detalle: "1 s · inteligibilidad baja",
    referencia: "Lima",
    texto: "más",
  },
  {
    id: "STROKE_F01_09",
    titulo: "ACV · Y ellos me enseñaron",
    detalle: "3 s · inteligibilidad media-baja",
    referencia: "Y ellos me enseñaron.",
    texto: "Y ellos me enseñaron",
  },
  {
    id: "STROKE_F01_03",
    titulo: "ACV · Todo mi lado derecho…",
    detalle: "6 s · inteligibilidad media-baja",
    referencia: "Todo mi lado derecho quedó dormido.",
    texto: "Todo mi lado derecho quedó dormido.",
  },
  {
    id: "STROKE_F01_10",
    titulo: "ACV · También el apoyo que…",
    detalle: "6 s · inteligibilidad media-baja",
    referencia: "También el apoyo que dan es primordial.",
    texto: "También el apoyo que dan es primordial.",
  },
  {
    id: "ALS_M06_08",
    titulo: "ELA · A vos Diego. Feliz…",
    detalle: "4 s · inteligibilidad baja",
    referencia: "A vos Diego. Feliz día del periodista.",
    texto: "Gracias por recibirnos.",
  },
  {
    id: "ALS_F02_02",
    titulo: "ELA · Me dan el diagnóstico…",
    detalle: "7 s · inteligibilidad media-alta",
    referencia: "Me dan el diagnóstico, más o menos, a los seis meses de que empecé.",
    texto: "Me dan el diagnóstico más o menos a los seis meses de que me...",
  },
  {
    id: "ALS_F02_03_01",
    titulo: "ELA · Es increíble, realmente cuando…",
    detalle: "8 s · inteligibilidad media-alta",
    referencia: "Es increíble, realmente cuando conocí a Darío.",
    texto: "Es increíble. Realmente, cuando conocí a Darío,",
  },
  {
    id: "ALS_M02_03",
    titulo: "ELA · Ayudar a otros enfermos…",
    detalle: "8 s · inteligibilidad media",
    referencia: "Ayudar a otros enfermos me hace sentir muy bien y también ver sonreír a la gente que me rodea día a día.",
    texto: "Ayudar a otros enfermos me hace sentir muy bien y también ver sonreír a la gente que me rodea día a día.",
  },
  {
    id: "ALS_M06_23",
    titulo: "ELA · Agradecer, agradecer, agradecer, agradecer…",
    detalle: "8 s · inteligibilidad baja",
    referencia: "Agradecer, agradecer, agradecer, agradecer a Dios, a la gente a la vida.",
    texto: "Agradecer a Dios, a la gente, a la vida.",
  },
  {
    id: "ALS_M02_01",
    titulo: "ELA · Sí, sin duda, porque…",
    detalle: "13 s · inteligibilidad media",
    referencia: "Sí, sin duda, porque al final logro muchas cosas gracias a ello. Soy Juan Antonio Mangudo, tengo treinta y cinco años y llevo con ELA seis años.",
    texto: "Porque al final logro muchas cosas gracias a ellos. Soy Juan Antonio Mangudo, tengo 35 años y llevo con él 6 años.",
  },
  {
    id: "ALS_F02_01",
    titulo: "ELA · Hace dos años y…",
    detalle: "14 s · inteligibilidad media-alta",
    referencia: "Hace dos años y medio, cuando empecé con este dedo a tener debilidad.",
    texto: "Hace dos años y medio, cuando empecé con este dedo a tener debilidad.",
  },
  {
    id: "PARKINSON_M01_02_01",
    titulo: "Parkinson · Parece que estoy enfadado…",
    detalle: "4 s · inteligibilidad alta",
    referencia: "Parece que estoy enfadado cuando realmente no lo estoy aunque tuviera motivos para estarlo.",
    texto: "Parece que estoy enfadado cuando realmente no lo estoy, aunque tuviera motivos para estarlo.",
  },
  {
    id: "PARKINSON_M01_07_01",
    titulo: "Parkinson · Si, si no me…",
    detalle: "4 s · inteligibilidad alta",
    referencia: "Si, si no me cabe duda, de hecho ya estoy perdiendo.",
    texto: "Ganará. Sí, no cabe duda, de hecho ya estoy perdiendo.",
  },
  {
    id: "PARKINSON_M01_09",
    titulo: "Parkinson · Entonces hacer planes es…",
    detalle: "4 s · inteligibilidad alta",
    referencia: "Entonces hacer planes es un poco aleatorio.",
    texto: "Entonces hacer planes es un poco aleatorio.",
  },
]

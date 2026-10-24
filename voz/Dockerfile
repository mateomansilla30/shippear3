FROM python:3.12-slim

# ffmpeg: conversión a nota de voz (.ogg OPUS) y lectura del audio del navegador
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# La memoria y los audios de cada turno van en /app/datos: montar un volumen ahí en Easypanel.
VOLUME /app/datos
EXPOSE 8000

# --proxy-headers: detrás del proxy HTTPS de Easypanel, audio_url sale con https:// y no http://
CMD ["uvicorn", "servidor:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

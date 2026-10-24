"""Envío de notas de voz por WhatsApp con Kapso (API compatible con la de Meta).

Pasos: subir el .ogg OPUS (POST /{phone_number_id}/media) → mandar un mensaje de audio con voice=true usando el id.
Docs: https://docs.kapso.ai/docs/whatsapp/send-messages/audio

Límites a tener en cuenta:
- WhatsApp solo deja mandar mensajes libres dentro de las 24 h desde que el destinatario le escribió al número.
- En el sandbox de Kapso, el destino tiene que ser el número registrado en la sesión de prueba.
"""
from __future__ import annotations

import httpx

import config

BASE_WHATSAPP = "https://api.kapso.ai/meta/whatsapp/v24.0"
BASE_PLATAFORMA = "https://api.kapso.ai/platform/v1"


class ErrorKapso(RuntimeError):
    pass


def _cabeceras() -> dict:
    if not config.KAPSO_API_KEY:
        raise ErrorKapso("Falta KAPSO_API_KEY en voz/.env")
    return {"X-API-Key": config.KAPSO_API_KEY}


def _revisar(r: httpx.Response, que: str) -> dict:
    if r.status_code >= 400:
        try:
            detalle = r.json().get("error", r.json())
            detalle = detalle.get("message", detalle) if isinstance(detalle, dict) else detalle
        except Exception:
            detalle = r.text[:300]
        raise ErrorKapso(f"Kapso ({que}) respondió {r.status_code}: {detalle}")
    return r.json()


def numero_de_envio() -> str:
    """phone_number_id desde .env o, si no está, el primero de la cuenta (por ejemplo, el del sandbox)."""
    if config.KAPSO_PHONE_NUMBER_ID:
        return config.KAPSO_PHONE_NUMBER_ID
    r = httpx.get(f"{BASE_PLATAFORMA}/whatsapp/phone_numbers", headers=_cabeceras(), timeout=20)
    datos = _revisar(r, "listar números").get("data", [])
    if not datos:
        raise ErrorKapso("La cuenta de Kapso no tiene números de WhatsApp: creá el sandbox o conectá un número")
    config.KAPSO_PHONE_NUMBER_ID = datos[0]["phone_number_id"]
    return config.KAPSO_PHONE_NUMBER_ID


def subir_audio(ogg: bytes, nombre: str = "nota.ogg") -> str:
    r = httpx.post(f"{BASE_WHATSAPP}/{numero_de_envio()}/media", headers=_cabeceras(),
                   data={"messaging_product": "whatsapp"}, files={"file": (nombre, ogg, "audio/ogg")}, timeout=30)
    return _revisar(r, "subir audio")["id"]


def _mandar(cuerpo: dict) -> str:
    r = httpx.post(f"{BASE_WHATSAPP}/{numero_de_envio()}/messages", headers=_cabeceras(),
                   json={"messaging_product": "whatsapp", **cuerpo}, timeout=30)
    datos = _revisar(r, "mandar mensaje")
    return (datos.get("messages") or [{}])[0].get("id", "")


def enviar_nota_de_voz(destino: str, ogg: bytes) -> str:
    """Sube el .ogg y lo manda como nota de voz. Devuelve el id del mensaje."""
    media_id = subir_audio(ogg)
    return _mandar({"to": _solo_digitos(destino), "type": "audio", "audio": {"id": media_id, "voice": True}})


def enviar_texto(destino: str, texto: str) -> str:
    return _mandar({"to": _solo_digitos(destino), "type": "text", "text": {"body": texto}})


def _solo_digitos(numero: str) -> str:
    d = "".join(c for c in str(numero) if c.isdigit())
    if not d:
        raise ErrorKapso("Falta el número de destino (KAPSO_DESTINO en voz/.env), con código de país: 5491112345678")
    return d

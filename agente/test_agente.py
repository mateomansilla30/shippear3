"""Prueba del agente con un LLM falso. Correr desde la raíz del repo: python -m agente.test_agente"""

import json
import os
import tempfile

from . import agente


def llm_falso(mensajes):
    """Imita al LLM: si la memoria trae el ejemplo de 'paresia', lo respeta; si no, 'corrige' mal."""
    pedido = mensajes[-1]["content"]
    if "mandale a maria" in agente.normalizar(pedido):
        return json.dumps({"texto": "Mandale a María que llego tarde.", "intencion": "mensaje",
                           "destinatario": "maría", "mensaje": "Llego tarde.", "confianza": 0.95, "opciones": []})
    if "parecia" in pedido:
        texto = "Tuve como secuela una paresia bilateral derecha." if "→ «Tuve como secuela una paresia" in pedido \
            else "Tuve como secuela una parálisis bilateral derecha."
        return json.dumps({"texto": texto, "intencion": "decir", "confianza": 0.7, "opciones": []})
    if "tomas" in agente.normalizar(pedido):
        return json.dumps({"texto": "Mi nieto Tomás viene el sábado.", "intencion": "decir", "confianza": 0.9,
                           "opciones": [], "proponer_memoria": [
                               {"tipo": "contacto", "valor": "Tomás", "relacion": "nieto"},
                               {"tipo": "contacto", "valor": "María", "relacion": "hija"},  # ya está: se ignora
                               {"tipo": "otra cosa", "valor": "x"}]})                     # inválida: se ignora
    if "lucia" in agente.normalizar(pedido):
        return json.dumps({"texto": "Hoy viene Lucía.", "intencion": "decir", "confianza": 0.9, "opciones": []})
    return json.dumps({"texto": "Quiero agua.", "intencion": "decir", "confianza": 0.3,
                       "opciones": ["Quiero agua.", "Quiero algo.", "Tengo sed."]})


def demo():
    agente.DB = os.path.join(tempfile.mkdtemp(), "prueba.db")
    p = agente.crear_persona("Marta", "Tiene ACV.")
    pid = p["id"]
    m = agente.cargar(pid)
    m["contactos"] = [{"nombre": "María", "relacion": "hija"}]
    agente.guardar(m)

    # 1. Sin memoria, el LLM cambia "paresia" por "parálisis"; la persona corrige.
    t1 = agente.procesar_turno(pid, "tuve como secuela una parecia bilateral derecha", llm=llm_falso)
    assert "parálisis" in t1["texto"] and t1["accion"] == "confirmar", t1
    m = agente.validar(pid, t1["id"], "Tuve como secuela una paresia bilateral derecha.")
    assert m["historial"][0]["estado"] == "corregido"
    assert agente.para_front(m)["correcciones"][0]["texto"].startswith("Tuve como secuela una paresia")

    # 2. La próxima vez, la corrección viaja en el contexto y sale bien: aprendió sin reentrenar.
    t2 = agente.procesar_turno(pid, "tuve como secuela una parecia bilateral", llm=llm_falso)
    assert "paresia" in t2["texto"], t2
    m = agente.validar(pid, t2["id"], t2["texto"])
    assert m["historial"][0]["estado"] == "validado"

    # 3. Mensajes: resuelve el contacto y siempre pide confirmación, aunque la confianza sea alta.
    t3 = agente.procesar_turno(pid, "mandale a maria que llego tarde", llm=llm_falso)
    assert t3["intencion"] == "mensaje" and t3["destinatario"] == "María" and t3["accion"] == "confirmar", t3

    # 4. Confianza baja con alternativas: ofrece opciones (sin repetir el texto principal).
    t4 = agente.procesar_turno(pid, "ero aua", llm=llm_falso)
    assert t4["accion"] == "opciones" and "Quiero agua." not in t4["opciones"] and len(t4["opciones"]) == 2, t4

    # 5. Si el LLM falla o responde cualquier cosa, no se cae: devuelve el texto y pide confirmación.
    def roto(_):
        raise TimeoutError
    t5 = agente.procesar_turno(pid, "hola", "Hola.", llm=roto)
    assert t5["texto"] == "Hola." and t5["accion"] == "confirmar"
    assert agente.interpretar("no es json", "x", [])["confianza"] == 0.0

    # 6. Sugerencias por repetición: un nombre que aparece en 3 turnos validados y no está en la memoria.
    for _ in range(3):
        t = agente.procesar_turno(pid, "hoy viene lucia", llm=llm_falso)
        agente.validar(pid, t["id"], t["texto"])
    assert agente.para_front(agente.cargar(pid))["sugerencias"] == [{"tipo": None, "valor": "Lucía", "relacion": ""}]
    agente.responder_sugerencia(pid, "Lucía", "contacto", "nieta")
    assert agente.para_front(agente.cargar(pid))["sugerencias"] == []

    # 6b. Sugerencias del LLM: "mi nieto Tomás" se propone solo si la persona validó ese turno tal cual.
    t = agente.procesar_turno(pid, "mi nieto tomas viene el sabado", llm=llm_falso)
    assert t["propuestas"] == [{"tipo": "contacto", "valor": "Tomás", "relacion": "nieto"},
                               {"tipo": "contacto", "valor": "María", "relacion": "hija"}], t["propuestas"]
    assert agente.para_front(agente.cargar(pid))["sugerencias"] == []  # pendiente: todavía no
    agente.validar(pid, t["id"], "Mi nieto Tomás viene el domingo.")   # corregido: no se usa
    assert agente.para_front(agente.cargar(pid))["sugerencias"] == []
    t = agente.procesar_turno(pid, "mi nieto tomas viene el sabado", llm=llm_falso)
    agente.validar(pid, t["id"], t["texto"])
    assert agente.para_front(agente.cargar(pid))["sugerencias"] == [{"tipo": "contacto", "valor": "Tomás", "relacion": "nieto"}]
    agente.responder_sugerencia(pid, "Tomás", "descartar")
    assert agente.para_front(agente.cargar(pid))["sugerencias"] == []

    # 7. La persona puede borrar lo aprendido desde el perfil.
    m = agente.cargar(pid)
    agente.editar(pid, m["persona"], m["contactos"], m["vocabulario"], correcciones=[])
    assert agente.para_front(agente.cargar(pid))["correcciones"] == []

    # 8. Rutas HTTP (si FastAPI está instalado).
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
    except ImportError:
        print("FastAPI no está instalado: salteo las rutas")
    else:
        from .rutas import router
        app = FastAPI()
        app.include_router(router)
        c = TestClient(app)
        nueva = c.post("/personas", json={"nombre": "Juan"}).json()
        assert any(x["id"] == nueva["id"] for x in c.get("/personas").json())
        t = agente.procesar_turno(nueva["id"], "hoy viene lucia", llm=llm_falso)
        r = c.post("/validar", json={"persona_id": nueva["id"], "turno_id": t["id"], "texto_final": "Hoy viene Lucía."})
        assert r.status_code == 200 and r.json()["historial"][0]["estado"] == "validado"
        assert c.get("/memoria/no-existe").status_code == 404
        assert c.post("/sugerencia", json={"persona_id": nueva["id"], "valor": "x", "tipo": "otro"}).status_code == 422

    print("ok")


if __name__ == "__main__":
    demo()

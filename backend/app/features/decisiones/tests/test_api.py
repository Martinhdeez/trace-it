"""End-to-end against the local database: `docker compose up db -d` and migrations applied.

Ingestion and extraction do not exist yet, so the instances, sources and compiled rules are
inserted directly. The sandbox is replaced by a fake, as agreed with Martín.
"""

import json
import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import session_factory
from app.features.agentes import sandbox
from app.features.fuentes.model import Fuente
from app.features.ingesta.model import Fichero, Instancia
from app.features.reglas.model import Regla
from app.main import app

PROVEEDORES = [
    {"nif": "B96233419", "iban": "ES2100752345670600123456"},
    {"nif": "B78451236", "iban": "ES9368884400123588900142"},
]
ASIENTOS = [
    {"pedido": "PO-2026-0008", "estado": "PENDIENTE"},
    {"pedido": "PO-2026-0474", "estado": "PAGADA"},
    {"pedido": "PO-2026-0813", "estado": "PENDIENTE"},
]

# Two rules of the v3 norm, as the compiler will eventually produce them.
REGLAS_V3 = {
    "iban_distinto": (
        "ESCALAR",
        lambda i, f, o, c: (
            i["iban"] != next(p for p in f["proveedores"] if p["nif"] == i["nif"])["iban"]
        ),
    ),
    "pedido_ya_pagado": (
        "NO_PAGAR",
        lambda i, f, o, c: (
            next(a for a in f["erp"] if a["pedido"] == i["pedido"])["estado"] == "PAGADA"
        ),
    ),
}

FACTURAS = {
    "factura_1217.pdf": {
        "nif": "B96233419",
        "iban": "ES2100752345670600123456",
        "pedido": "PO-2026-0008",
    },
    "FA-1016_papelería.pdf": {
        "nif": "B96233419",
        "iban": "ES2100752345670600123456",
        "pedido": "PO-2026-0474",
    },
    "FA-5044_mensajería2.pdf": {
        "nif": "B78451236",
        "iban": "ES3900815290070012345678",
        "pedido": "PO-2026-0813",
    },
    "FA-9999_sin_leer.pdf": None,  # ingested but not extracted yet
}


def fake_sandbox(codigo: str, instancia: dict, fuentes: dict, otras: list, contexto: dict) -> dict:
    salta = REGLAS_V3[codigo][1](instancia, fuentes, otras, contexto)
    return {"salta": salta, "motivo": codigo if salta else ""}


async def sembrar(proceso_id: int) -> None:
    """Everything Álvaro's ingestion and Martín's compiler will produce later."""
    async with session_factory() as session:
        for nombre, simbolos in FACTURAS.items():
            digest = uuid.uuid4().hex
            session.add(Fichero(hash=digest, nombre=nombre, contenido=b"%PDF", texto=""))
            session.add(
                Instancia(
                    proceso_id=proceso_id, fichero_hash=digest, nombre=nombre, simbolos=simbolos
                )
            )
        session.add(Fuente(proceso_id=proceso_id, nombre="proveedores", origen="x", filas=[]))
        session.add(
            Fuente(proceso_id=proceso_id, nombre="proveedores", origen="y", filas=PROVEEDORES)
        )
        session.add(Fuente(proceso_id=proceso_id, nombre="erp", origen="erp:t", filas=ASIENTOS))
        for nombre, (decision, _) in REGLAS_V3.items():
            session.add(
                Regla(
                    proceso_id=proceso_id,
                    texto=nombre,
                    tipo="prohibicion",
                    decision=decision,
                    codigo_a=nombre,
                    codigo_b=nombre,
                    hash=f"hash-{nombre}",
                    estado="activa",
                    informe={"valida": True},
                )
            )
        await session.commit()


async def test_ejecutar_revisar_y_exportar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "ejecutar", fake_sandbox)
    sufijo = uuid.uuid4().hex[:8]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post(
            "/usuarios",
            json={"nombre": "Ana", "email": f"ana-{sufijo}@x.com", "rol": "responsable"},
        )
        cabeceras = {"X-Usuario-Id": str(r.json()["id"])}

        r = await api.post(
            "/procesos",
            json={
                "nombre": f"facturas-{sufijo}",
                "tipos_decision": [
                    {"nombre": "ESCALAR", "prioridad": 3, "requiere_persona": True},
                    {"nombre": "NO_PAGAR", "prioridad": 2},
                    {"nombre": "PAGAR", "prioridad": 1, "por_defecto": True},
                ],
                "simbolos": [{"nombre": "nif", "tipo": "texto"}],
            },
        )
        assert r.status_code == 201, r.text
        proceso_id = r.json()["id"]
        await sembrar(proceso_id)

        # The engine decides everything that has symbols. The unread invoice is left alone.
        r = await api.post(f"/procesos/{proceso_id}/ejecutar")
        assert r.status_code == 200, r.text
        resumen = r.json()
        assert resumen["por_decision"] == {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1}
        assert resumen["contexto"]["ahora"]

        r = await api.get(f"/procesos/{proceso_id}/instancias", params={"estado": "PENDIENTE"})
        assert [i["nombre"] for i in r.json()] == ["FA-9999_sin_leer.pdf"]

        # The export refuses to invent a result for an instance nobody decided.
        r = await api.get(f"/procesos/{proceso_id}/exportar")
        assert r.status_code == 409, r.text
        assert "FA-9999_sin_leer.pdf" in r.json()["message"]

        # What a person has to look at.
        r = await api.get(f"/procesos/{proceso_id}/cola")
        assert [i["nombre"] for i in r.json()] == ["FA-5044_mensajería2.pdf"]
        escalada = r.json()[0]["id"]

        r = await api.get(f"/instancias/{escalada}")
        detalle = r.json()
        assert detalle["decision"] == "ESCALAR"
        assert detalle["simbolos"]["pedido"] == "PO-2026-0813"
        assert len(detalle["decisiones"]) == 1
        decision = detalle["decisiones"][0]
        assert decision["autor"] == "motor"
        assert decision["motivo"] == "iban_distinto"
        assert decision["contexto"]["ahora"] == resumen["contexto"]["ahora"]
        # Every rule's answer is recorded, not just the one that fired.
        assert {(r["motivo"], r["salta"]) for r in decision["resultados"]} == {
            ("iban_distinto", True),
            ("", False),
        }
        assert [e["paso"] for e in detalle["eventos"]] == ["decision"]

        # A person resolves it. The engine's decision stays exactly as it was.
        r = await api.post(
            f"/instancias/{escalada}/resolver",
            json={"decision": "NO_PAGAR", "motivo": "IBAN no verificado con el proveedor"},
            headers=cabeceras,
        )
        assert r.status_code == 200, r.text
        historico = r.json()["decisiones"]
        assert [(d["autor"], d["decision"]) for d in historico] == [
            ("motor", "ESCALAR"),
            ("Ana", "NO_PAGAR"),
        ]
        assert r.json()["decision"] == "NO_PAGAR"

        # She also decides the one that was never extracted.
        pendiente = next(
            i["id"]
            for i in (await api.get(f"/procesos/{proceso_id}/instancias")).json()
            if i["nombre"] == "FA-9999_sin_leer.pdf"
        )
        r = await api.post(
            f"/instancias/{pendiente}/resolver",
            json={"decision": "ESCALAR", "motivo": "El PDF no se puede leer"},
            headers=cabeceras,
        )
        assert r.status_code == 200, r.text

        r = await api.get(f"/procesos/{proceso_id}/exportar")
        assert r.status_code == 200, r.text
        salida = [json.loads(linea) for linea in r.text.splitlines()]
        assert salida == [
            {"file_id": "factura_1217.pdf", "result": "PAGAR"},
            {"file_id": "FA-1016_papelería.pdf", "result": "NO_PAGAR"},
            {"file_id": "FA-5044_mensajería2.pdf", "result": "NO_PAGAR"},
            {"file_id": "FA-9999_sin_leer.pdf", "result": "ESCALAR"},
        ]
        # The file_id must survive byte for byte, accents included.
        assert "papeler\\u00eda" not in r.text


async def test_resolver_rechaza_una_decision_que_no_es_del_proceso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox, "ejecutar", fake_sandbox)
    sufijo = uuid.uuid4().hex[:8]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post(
            "/usuarios", json={"nombre": "Ana", "email": f"ana-{sufijo}@x.com", "rol": "operador"}
        )
        cabeceras = {"X-Usuario-Id": str(r.json()["id"])}
        r = await api.post(
            "/procesos",
            json={
                "nombre": f"facturas-{sufijo}",
                "tipos_decision": [
                    {"nombre": "ESCALAR", "prioridad": 3, "requiere_persona": True},
                    {"nombre": "NO_PAGAR", "prioridad": 2},
                    {"nombre": "PAGAR", "prioridad": 1, "por_defecto": True},
                ],
                "simbolos": [],
            },
        )
        proceso_id = r.json()["id"]
        await sembrar(proceso_id)
        instancias: list[dict[str, Any]] = (
            await api.get(f"/procesos/{proceso_id}/instancias")
        ).json()

        r = await api.post(
            f"/instancias/{instancias[0]['id']}/resolver",
            json={"decision": "REEMBOLSAR", "motivo": "no existe en este proceso"},
            headers=cabeceras,
        )
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "conflict"

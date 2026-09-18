"""End-to-end against the local database: `docker compose up db -d` and migrations applied."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_proceso_regla_flujo(monkeypatch: pytest.MonkeyPatch) -> None:
    async def llm_caido(*args, **kwargs):
        raise RuntimeError("sin LLM en tests")

    monkeypatch.setattr("app.features.llm.cliente.completar", llm_caido)
    sufijo = uuid.uuid4().hex[:8]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post(
            "/usuarios",
            json={"nombre": "Ana", "email": f"ana-{sufijo}@x.com", "rol": "responsable"},
        )
        assert r.status_code == 201, r.text
        r = await api.post("/login", json={"email": f"ana-{sufijo}@x.com"})
        assert r.status_code == 200, r.text
        cabeceras = {"X-Usuario-Id": str(r.json()["id"])}

        r = await api.post(
            "/procesos",
            json={
                "nombre": f"facturas-{sufijo}",
                "tipos_decision": [
                    {"nombre": "ESCALAR", "prioridad": 3},
                    {"nombre": "NO_PAGAR", "prioridad": 2},
                    {"nombre": "PAGAR", "prioridad": 1, "por_defecto": True},
                ],
                "simbolos": [
                    {"nombre": "importe", "tipo": "numero"},
                    {"nombre": "proveedor", "tipo": "texto"},
                ],
            },
        )
        assert r.status_code == 201, r.text
        proceso = r.json()
        assert [t["nombre"] for t in proceso["tipos_decision"]] == ["ESCALAR", "NO_PAGAR", "PAGAR"]
        assert len(proceso["simbolos"]) == 2

        r = await api.post(
            f"/procesos/{proceso['id']}/reglas",
            json={
                "texto": "Si importe > 1000, escalar",
                "tipo": "prohibicion",
                "decision": "ESCALAR",
            },
        )
        assert r.status_code == 201, r.text
        regla = r.json()
        assert regla["estado"] == "borrador"

        r = await api.post(f"/reglas/{regla['id']}/compilar")
        assert r.status_code == 502, r.text
        assert r.json()["code"] == "compilation_failed"

        r = await api.post(f"/reglas/{regla['id']}/activar", headers=cabeceras)
        assert r.status_code == 409, r.text

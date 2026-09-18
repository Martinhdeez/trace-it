"""Loading process definitions from `procesos/*.json`, against the local database."""

import json
import uuid
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.main import app

PROCESOS = Path(__file__).parents[5] / "procesos"


def _definicion(fichero: str) -> dict:
    """The file's definition with a unique process name and emails, so reruns start fresh."""
    datos = json.loads((PROCESOS / fichero).read_text(encoding="utf-8"))
    sufijo = uuid.uuid4().hex[:8]
    datos["nombre"] += f" {sufijo}"
    for u in datos.get("usuarios", []):
        u["email"] = f"{sufijo}-{u['email']}"
    return datos


async def _cargar(api: AsyncClient, datos: dict) -> dict:
    r = await api.post("/procesos/definicion", json=datos)
    assert r.status_code == 200, r.text
    carga = r.json()
    r = await api.get(f"/procesos/{carga['proceso']['id']}/reglas")
    carga["reglas"] = len(r.json())
    return carga


async def test_cargar_dos_veces_es_idempotente() -> None:
    datos = _definicion("pago-facturas.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        primera = await _cargar(api, datos)
        segunda = await _cargar(api, datos)
    assert primera["reglas_nuevas"] == primera["reglas"] == len(datos["reglas"])
    assert primera["usuarios_nuevos"] == len(datos["usuarios"])
    assert segunda["reglas_nuevas"] == segunda["usuarios_nuevos"] == 0
    assert segunda["reglas"] == primera["reglas"]
    assert segunda["proceso"] == primera["proceso"]
    assert [t["nombre"] for t in primera["proceso"]["tipos_decision"]] == [
        "ESCALAR",
        "NO_PAGAR",
        "PAGAR",
    ]


async def test_proceso_que_no_es_de_facturas() -> None:
    datos = _definicion("gastos-viaje.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        carga = await _cargar(api, datos)
    assert carga["reglas"] == 2
    assert {t["nombre"] for t in carga["proceso"]["tipos_decision"]} == {
        "REVISAR",
        "RECHAZAR",
        "APROBAR",
    }


async def test_dos_por_defecto_se_rechaza() -> None:
    datos = _definicion("gastos-viaje.json")
    datos["tipos_decision"][1]["por_defecto"] = True
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post("/procesos/definicion", json=datos)
        assert r.status_code == 422, r.text
        assert "por defecto" in r.text
        nombres = [p["nombre"] for p in (await api.get("/procesos")).json()]
    assert datos["nombre"] not in nombres

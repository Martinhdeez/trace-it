"""Loading process definitions from `procesos/*.json`, against the local database."""

import json
import uuid
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.core.database import session_factory
from app.features.procesos.definicion import Definicion, cargar_definicion
from app.features.reglas import service as reglas
from app.main import app

PROCESOS = Path(__file__).parents[5] / "procesos"


def _definicion(fichero: str, con_codigo: bool = False) -> dict:
    """The file's definition with a unique process name and emails, so reruns start fresh.

    A rule's `codigo` names a file next to the definition, which only the CLI can resolve,
    so it is dropped unless a test is specifically about that.
    """
    datos = json.loads((PROCESOS / fichero).read_text(encoding="utf-8"))
    sufijo = uuid.uuid4().hex[:8]
    datos["nombre"] += f" {sufijo}"
    for u in datos.get("usuarios", []):
        u["email"] = f"{sufijo}-{u['email']}"
    if not con_codigo:
        for r in datos.get("reglas", []):
            r.pop("codigo", None)
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


async def test_por_http_no_se_cargan_reglas_con_codigo_en_un_fichero() -> None:
    """A path would be resolved on the server, against whatever the backend can read."""
    datos = _definicion("pago-facturas.json", con_codigo=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post("/procesos/definicion", json=datos)

    assert r.status_code == 409, r.text
    assert "app.cli" in r.json()["message"]


async def test_desde_disco_las_reglas_llegan_con_su_codigo_y_se_activan() -> None:
    """How a process runs before any model is configured."""
    datos = Definicion.model_validate(_definicion("pago-facturas.json", con_codigo=True))

    async with session_factory() as session:
        carga = await cargar_definicion(session, datos, PROCESOS)
        proceso_id = carga.proceso.id
        for regla in await reglas.listar(session, proceso_id, "borrador"):
            detalle = await reglas.obtener(session, regla.id)
            assert detalle.codigo_a and detalle.codigo_a == detalle.codigo_b
            assert detalle.informe["origen"] == "escrita a mano"
            await reglas.activar(session, regla.id)

        activas = await reglas.listar(session, proceso_id, "activa")

    assert len(activas) == len(datos.reglas) == 16
    assert all(r.hash for r in activas)

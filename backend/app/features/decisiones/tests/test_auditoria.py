"""A rule change is checked against every decision already taken, before it is adopted.

Same setup as `test_api.py`: instances, sources and compiled rules inserted directly, the
sandbox faked.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import session_factory
from app.features.agentes import sandbox
from app.features.decisiones.tests.test_api import REGLAS_V3, sembrar
from app.features.reglas.model import Regla
from app.main import app

# A rule nobody has activated yet: it escalates any invoice from this supplier. It stays
# out of REGLAS_V3 so `sembrar` does not seed it as active.
REGLA_NUEVA = "proveedor_vigilado"
EXTRA = {REGLA_NUEVA: ("ESCALAR", lambda i, f, o: i["nif"] == "B96233419")}


def fake_sandbox(codigo: str, instancia: dict, fuentes: dict, otras: list) -> dict:
    salta = {**REGLAS_V3, **EXTRA}[codigo][1](instancia, fuentes, otras)
    return {"salta": salta, "motivo": codigo if salta else ""}


async def crear_borrador(proceso_id: int) -> int:
    async with session_factory() as session:
        regla = Regla(
            proceso_id=proceso_id,
            texto=REGLA_NUEVA,
            tipo="prohibicion",
            decision="ESCALAR",
            codigo_a=REGLA_NUEVA,
            codigo_b=REGLA_NUEVA,
            hash=f"hash-{REGLA_NUEVA}",
            estado="borrador",
            informe={"valida": True},
        )
        session.add(regla)
        await session.commit()
        return regla.id


async def preparar(api: AsyncClient, sufijo: str) -> tuple[int, dict[str, str]]:
    """A process with its invoices already decided by the engine."""
    r = await api.post(
        "/usuarios", json={"nombre": "Ana", "email": f"ana-{sufijo}@x.com", "rol": "responsable"}
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
    proceso_id = r.json()["id"]
    await sembrar(proceso_id)
    await api.post(f"/procesos/{proceso_id}/ejecutar")
    return proceso_id, cabeceras


async def test_impacto_se_ve_antes_de_activar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "ejecutar", fake_sandbox)
    sufijo = uuid.uuid4().hex[:8]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        proceso_id, cabeceras = await preparar(api, sufijo)
        regla_id = await crear_borrador(proceso_id)

        r = await api.get(f"/reglas/{regla_id}/impacto")
        assert r.status_code == 200, r.text
        impacto = r.json()

        # Both invoices from that supplier move: ESCALAR outranks what they concluded
        # before. FA-5044 is another supplier and was escalated by the IBAN rule anyway.
        assert [(c["nombre"], c["antes"], c["despues"]) for c in impacto["cambios"]] == [
            ("factura_1217.pdf", "PAGAR", "ESCALAR"),
            ("FA-1016_papelería.pdf", "NO_PAGAR", "ESCALAR"),
        ]
        assert impacto["conflictos"] == []
        assert impacto["sin_cambio"] == 1

        # Looking does not change anything.
        assert (await api.get(f"/reglas/{regla_id}")).json()["estado"] == "borrador"
        assert (await api.get(f"/procesos/{proceso_id}/hallazgos")).json() == []


async def test_activar_registra_hallazgos_y_no_toca_el_pasado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox, "ejecutar", fake_sandbox)
    sufijo = uuid.uuid4().hex[:8]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        proceso_id, cabeceras = await preparar(api, sufijo)
        regla_id = await crear_borrador(proceso_id)

        r = await api.post(f"/reglas/{regla_id}/activar", headers=cabeceras)
        assert r.status_code == 200, r.text

        hallazgos = (await api.get(f"/procesos/{proceso_id}/hallazgos")).json()
        assert [h["detalle"].split(":")[0] for h in hallazgos] == [
            "PAGAR -> ESCALAR",
            "NO_PAGAR -> ESCALAR",
        ]
        assert {h["regla_id"] for h in hallazgos} == {regla_id}

        # The decision itself is untouched: the finding is a notice, not a correction.
        instancias = (await api.get(f"/procesos/{proceso_id}/instancias")).json()
        afectada = next(i for i in instancias if i["nombre"] == "factura_1217.pdf")
        assert afectada["decision"] == "PAGAR"
        detalle = (await api.get(f"/instancias/{afectada['id']}")).json()
        assert len(detalle["decisiones"]) == 1


async def test_una_decision_humana_bloquea_la_regla(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rules do not overrule a person, and a person does not silently veto a rule."""
    monkeypatch.setattr(sandbox, "ejecutar", fake_sandbox)
    sufijo = uuid.uuid4().hex[:8]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        proceso_id, cabeceras = await preparar(api, sufijo)
        instancias = (await api.get(f"/procesos/{proceso_id}/instancias")).json()
        afectada = next(i for i in instancias if i["nombre"] == "factura_1217.pdf")
        await api.post(
            f"/instancias/{afectada['id']}/resolver",
            json={"decision": "PAGAR", "motivo": "Comprobado con el proveedor por teléfono"},
            headers=cabeceras,
        )
        regla_id = await crear_borrador(proceso_id)

        r = await api.get(f"/reglas/{regla_id}/impacto")
        assert [c["nombre"] for c in r.json()["conflictos"]] == ["factura_1217.pdf"]
        # The other invoice would still change; the conflict is what blocks the rule.
        assert [c["nombre"] for c in r.json()["cambios"]] == ["FA-1016_papelería.pdf"]

        r = await api.post(f"/reglas/{regla_id}/activar", headers=cabeceras)
        assert r.status_code == 409, r.text
        assert "factura_1217.pdf" in r.json()["message"]
        assert (await api.get(f"/reglas/{regla_id}")).json()["estado"] == "borrador"
        assert (await api.get(f"/procesos/{proceso_id}/hallazgos")).json() == []


async def test_retirar_se_comprueba_igual_que_activar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "ejecutar", fake_sandbox)
    sufijo = uuid.uuid4().hex[:8]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        proceso_id, cabeceras = await preparar(api, sufijo)
        reglas = (await api.get(f"/procesos/{proceso_id}/reglas")).json()
        ya_pagado = next(r for r in reglas if r["texto"] == "pedido_ya_pagado")

        # Without it, the invoice the ERP already paid would be paid again.
        r = await api.get(f"/reglas/{ya_pagado['id']}/impacto")
        assert [(c["nombre"], c["antes"], c["despues"]) for c in r.json()["cambios"]] == [
            ("FA-1016_papelería.pdf", "NO_PAGAR", "PAGAR")
        ]

        r = await api.post(f"/reglas/{ya_pagado['id']}/retirar", headers=cabeceras)
        assert r.status_code == 200, r.text
        hallazgos = (await api.get(f"/procesos/{proceso_id}/hallazgos")).json()
        assert hallazgos[0]["detalle"].startswith("NO_PAGAR -> PAGAR")


async def test_un_caso_escalado_no_genera_hallazgo(monkeypatch: pytest.MonkeyPatch) -> None:
    """An instance sitting in the human queue was never acted on, so nothing went wrong."""
    monkeypatch.setattr(sandbox, "ejecutar", fake_sandbox)
    sufijo = uuid.uuid4().hex[:8]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        proceso_id, cabeceras = await preparar(api, sufijo)
        reglas = (await api.get(f"/procesos/{proceso_id}/reglas")).json()
        iban = next(r for r in reglas if r["texto"] == "iban_distinto")

        # Retiring it turns the escalated invoice into PAGAR: a change, but not a finding.
        r = await api.get(f"/reglas/{iban['id']}/impacto")
        assert [(c["nombre"], c["antes"]) for c in r.json()["cambios"]] == [
            ("FA-5044_mensajería2.pdf", "ESCALAR")
        ]

        await api.post(f"/reglas/{iban['id']}/retirar", headers=cabeceras)
        assert (await api.get(f"/procesos/{proceso_id}/hallazgos")).json() == []

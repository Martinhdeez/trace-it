"""Against the local database (`docker compose up db -d` + migrations); skipped if absent.
The LLM is monkeypatched: no network."""

import json
import socket
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import engine, session_factory
from app.features.agentes import asistente
from app.features.decisiones.model import Decision
from app.features.ingesta.model import Fichero, Instancia
from app.features.llm.cliente import Respuesta
from app.features.procesos.model import Proceso, TipoDecision
from app.features.reglas.model import Regla
from app.features.trazas.model import Evento
from app.main import app


def _db_disponible() -> bool:
    url = make_url(settings.database_url)
    try:
        socket.create_connection((url.host, url.port or 5432), timeout=1).close()
        return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _db_disponible(), reason="Postgres local no disponible")

SUGERENCIA = {
    "decision": "NO_PAGAR",
    "razonamiento": "importe=5000 (texto) supera el límite de la regla 'importe > 1000'",
    "regla_propuesta": "Si importe (texto de la factura) > 4000 y proveedor (Excel) = 'ACME', "
    "no pagar",
    "tipo_propuesto": "prohibicion",
}


@pytest.fixture
async def caso(request):
    """A process with an escalated instance, a past human resolution and a pending one. The
    human-queue type is named ESCALAR unless the test passes another name as param."""
    escalar = getattr(request, "param", "ESCALAR")
    sufijo = uuid.uuid4().hex[:8]
    async with session_factory() as s:
        proceso = Proceso(nombre=f"asistente-{sufijo}")
        s.add(proceso)
        await s.flush()
        s.add_all(
            [
                TipoDecision(
                    proceso_id=proceso.id, nombre=escalar, prioridad=3, requiere_persona=True
                ),
                TipoDecision(proceso_id=proceso.id, nombre="NO_PAGAR", prioridad=2),
                TipoDecision(proceso_id=proceso.id, nombre="PAGAR", prioridad=1, por_defecto=True),
            ]
        )
        await s.flush()
        regla = Regla(
            proceso_id=proceso.id,
            texto="Si importe > 1000, escalar",
            tipo="prohibicion",
            decision=escalar,
            estado="activa",
        )
        fichero = Fichero(
            hash=uuid.uuid4().hex, nombre="f.pdf", contenido=b"x", texto="Total: 5000 EUR"
        )
        s.add_all([regla, fichero])
        await s.flush()
        simbolos = {"importe": {"valor": 5000, "origen": "texto"}}
        escalada, antigua, pendiente = (
            Instancia(proceso_id=proceso.id, fichero_hash=fichero.hash, nombre=n, simbolos=simbolos)
            for n in ("a", "b", "c")
        )
        s.add_all([escalada, antigua, pendiente])
        await s.flush()
        resultados = [{"id": regla.id, "hash": "h", "salta": True, "motivo": "importe > 1000"}]
        s.add_all(
            [
                Decision(
                    instancia_id=escalada.id,
                    decision=escalar,
                    resultados=resultados,
                    reglas_hash="h",
                    autor="motor",
                ),
                Decision(
                    instancia_id=antigua.id,
                    decision="NO_PAGAR",
                    resultados=resultados,
                    reglas_hash="h",
                    autor="Ana",
                    motivo="ACME no cobra por encima de 4000",
                ),
            ]
        )
        await s.commit()
        yield {"escalada": escalada.id, "pendiente": pendiente.id}
    await engine.dispose()  # connections are bound to this test's event loop


def _llm(monkeypatch, respuestas: list[dict]) -> list[list[dict]]:
    llamadas = []

    async def falso(session, papel, mensajes, formato=None):
        assert papel == "asistente"
        llamadas.append(list(mensajes))
        return Respuesta(json.dumps(respuestas.pop(0)), "falso/modelo", 0.01, 5)

    monkeypatch.setattr(asistente, "completar", falso)
    return llamadas


async def test_sugiere_y_registra_evento(caso, monkeypatch) -> None:
    llamadas = _llm(monkeypatch, [SUGERENCIA])
    async with session_factory() as s:
        sugerencia = await asistente.sugerir(s, caso["escalada"])
    assert sugerencia == asistente.Sugerencia(**SUGERENCIA)

    contexto = json.loads(llamadas[0][1]["content"])
    assert contexto["tipos_decision"] == ["ESCALAR", "NO_PAGAR", "PAGAR"]
    assert contexto["tipos_requieren_persona"] == ["ESCALAR"]
    assert contexto["motivo_escalado"]["reglas_que_saltaron"][0]["texto"].startswith("Si importe")
    assert contexto["resoluciones_humanas"][0]["motivo"] == "ACME no cobra por encima de 4000"
    assert contexto["caso"]["texto_fichero"] == "Total: 5000 EUR"

    async with session_factory() as s:
        evento = await s.scalar(select(Evento).where(Evento.instancia_id == caso["escalada"]))
    assert evento.paso == "sugerir_escalado"
    assert evento.datos["modelo"] == "falso/modelo"
    assert evento.latencia_ms == 5


@pytest.mark.parametrize("caso", ["REVISAR_MANUAL"], indirect=True)
async def test_tipo_con_persona_de_otro_nombre(caso, monkeypatch) -> None:
    llamadas = _llm(monkeypatch, [SUGERENCIA])
    async with session_factory() as s:
        sugerencia = await asistente.sugerir(s, caso["escalada"])
    assert sugerencia.decision == "NO_PAGAR"
    contexto = json.loads(llamadas[0][1]["content"])
    assert contexto["tipos_requieren_persona"] == ["REVISAR_MANUAL"]
    assert contexto["motivo_escalado"]["decision_actual"] == "REVISAR_MANUAL"


async def test_decision_invalida_reintenta_una_vez(caso, monkeypatch) -> None:
    llamadas = _llm(monkeypatch, [{**SUGERENCIA, "decision": "RECHAZAR"}, SUGERENCIA])
    async with session_factory() as s:
        sugerencia = await asistente.sugerir(s, caso["escalada"])
    assert sugerencia.decision == "NO_PAGAR"
    assert len(llamadas) == 2
    assert "RECHAZAR" in llamadas[1][-1]["content"]


async def test_no_escalada_da_409(caso, monkeypatch) -> None:
    _llm(monkeypatch, [])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.get(f"/instancias/{caso['pendiente']}/sugerencia")
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "conflict"
        r = await api.get("/instancias/0/sugerencia")
        assert r.status_code == 404, r.text

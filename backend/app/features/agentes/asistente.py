"""Escalation assistant: suggests a decision, its reasoning and a new rule (3.4).
Owner: Martín.

The LLM never decides anything in the pipeline. This is only a suggestion shown to a
person, who then resolves the case and, if they want, adds the proposed rule (which is
compiled and validated like any other rule)."""

import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError, TraceError
from app.features.decisiones.model import Decision
from app.features.ingesta.model import Fichero, Instancia
from app.features.llm.cliente import completar
from app.features.procesos.model import TipoDecision
from app.features.reglas.model import Regla
from app.features.trazas.service import registrar

MAX_TEXTO = 12_000  # chars of the file's text sent to the model
MAX_RESOLUCIONES = 10

SISTEMA = """\
You assist a person who must resolve a case that an automatic, rule-based decision process \
sent to a person (its decision type requires a person, or it is under review). You do not \
decide: you suggest, and the person decides.

Given the case, answer with:
- decision: the decision you would take. It MUST be exactly one of tipos_decision. Avoid the \
types in tipos_requieren_persona: those only send the case to a person, who needs a final one.
- razonamiento: why, citing the concrete symbol values (with their origin) and the rule(s) \
that fired. Be brief and factual. Write in Spanish.
- regla_propuesta: ONE new rule, in Spanish, that would resolve this case and similar future \
ones automatically. It must be general enough to cover similar cases but not broader: name \
the exact symbols it uses (by their name) and where each comes from, with precise conditions \
(thresholds, comparisons, lists), so a code agent can implement it without ambiguity. Do not \
restate an existing rule. Follow how people resolved past cases when they are relevant.
- tipo_propuesto: "requisito" if the rule states a condition that must hold, \
"prohibicion" if it states a condition that must not happen."""


class AsistenteError(TraceError):
    status_code = 502
    code = "llm_error"


class _Salida(BaseModel):
    decision: str
    razonamiento: str
    regla_propuesta: str
    tipo_propuesto: Literal["requisito", "prohibicion"]


@dataclass(frozen=True)
class Sugerencia:
    decision: str
    razonamiento: str
    regla_propuesta: str  # rule text, to be compiled like any other rule if accepted
    tipo_propuesto: str  # requisito | prohibicion


async def _contexto(
    session: AsyncSession, instancia: Instancia
) -> tuple[dict[str, Any], list[str]]:
    ultima = await session.scalar(
        select(Decision)
        .where(Decision.instancia_id == instancia.id)
        .order_by(Decision.id.desc())
        .limit(1)
    )
    pid = instancia.proceso_id
    todos = list(
        await session.scalars(
            select(TipoDecision)
            .where(TipoDecision.proceso_id == pid)
            .order_by(TipoDecision.prioridad.desc())
        )
    )
    tipos = [t.nombre for t in todos]
    con_persona = [t.nombre for t in todos if t.requiere_persona]
    if not (ultima and ultima.decision in con_persona) and instancia.estado != "REVISION":
        raise ConflictError(f"La instancia {instancia.id} no está escalada ni en revisión")

    reglas = {r.id: r for r in await session.scalars(select(Regla).where(Regla.proceso_id == pid))}
    fichero = await session.get(Fichero, instancia.fichero_hash)
    resoluciones = await session.execute(
        select(Decision, Instancia.simbolos)
        .join(Instancia, Decision.instancia_id == Instancia.id)
        .where(Instancia.proceso_id == pid, Decision.autor != "motor")
        .order_by(Decision.id.desc())
        .limit(MAX_RESOLUCIONES)
    )

    saltaron = [r for r in (ultima.resultados if ultima else []) if r.get("salta")]
    contexto = {
        "tipos_decision": tipos,
        "tipos_requieren_persona": con_persona,
        "caso": {
            "nombre": instancia.nombre,
            "simbolos": instancia.simbolos or {},
            "texto_fichero": ((fichero.texto if fichero else None) or "")[:MAX_TEXTO],
        },
        "motivo_escalado": {
            "decision_actual": ultima.decision if ultima else None,
            "estado": instancia.estado,
            "motivo_revision": instancia.motivo_revision,
            "reglas_que_saltaron": [
                {
                    "id": r.get("id"),
                    "motivo": r.get("motivo"),
                    "texto": reglas[r["id"]].texto if r.get("id") in reglas else None,
                    "decision": reglas[r["id"]].decision if r.get("id") in reglas else None,
                }
                for r in saltaron
            ],
        },
        "reglas_activas": [
            {"id": r.id, "texto": r.texto, "tipo": r.tipo, "decision": r.decision}
            for r in reglas.values()
            if r.estado == "activa"
        ],
        "resoluciones_humanas": [
            {"simbolos": simbolos, "decision": d.decision, "autor": d.autor, "motivo": d.motivo}
            for d, simbolos in resoluciones
        ],
    }
    return contexto, tipos


async def sugerir(session: AsyncSession, instancia_id: int) -> Sugerencia:
    instancia = await session.get(Instancia, instancia_id)
    if instancia is None:
        raise NotFoundError(f"Instancia {instancia_id} no existe")
    contexto, tipos = await _contexto(session, instancia)

    mensajes: list[dict[str, Any]] = [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": json.dumps(contexto, ensure_ascii=False, default=str)},
    ]
    latencia, coste, salida, modelo, intentos = 0, None, None, None, 0
    while intentos < 2:  # one retry if the reply is invalid
        intentos += 1
        try:
            respuesta = await completar(session, "asistente", mensajes, _Salida)
        except TraceError:
            raise
        except Exception as error:
            raise AsistenteError(f"Fallo del modelo del asistente: {error}") from error
        modelo = respuesta.modelo
        latencia += respuesta.latencia_ms
        if respuesta.coste is not None:
            coste = (coste or 0) + respuesta.coste
        try:
            salida = _Salida.model_validate_json(respuesta.contenido)
            if salida.decision in tipos:
                break
            problema = f"decision {salida.decision!r} no es uno de {tipos}"
        except ValidationError as error:
            problema = f"respuesta no válida: {error}"
        salida = None
        mensajes += [
            {"role": "assistant", "content": respuesta.contenido},
            {"role": "user", "content": f"Corrige: {problema}. Responde de nuevo."},
        ]
    if salida is None:
        raise AsistenteError(f"El asistente no dio una sugerencia válida: {problema}")

    registrar(
        session,
        "sugerir_escalado",
        instancia_id=instancia_id,
        datos={"modelo": modelo, "decision": salida.decision, "intentos": intentos},
        latencia_ms=latencia,
        coste=coste,
    )
    await session.commit()
    return Sugerencia(**salida.model_dump())

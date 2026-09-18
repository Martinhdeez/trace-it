"""Rule compiler: two independent agents turn a rule's text into code + tests (P9).

Owner: Martín. Contract used by `reglas.service.compilar`.
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import TraceError
from app.features.agentes import sandbox
from app.features.fuentes.model import Fuente
from app.features.ingesta.model import Instancia
from app.features.llm import cliente
from app.features.llm.model import ConfigLLM
from app.features.procesos.model import Proceso, Simbolo
from app.features.reglas.model import Regla
from app.features.trazas.service import registrar

# A test case, as written by an agent from the rule text alone:
# {"nombre": str, "instancia": {...}, "fuentes": {...}, "otras": [...], "salta": bool}
Test = dict[str, Any]
# (instance name, {symbol: value})
Historico = list[tuple[str, dict[str, Any]]]

PAPELES = ("compilador_a", "compilador_b")
MAX_REPARACIONES = 2
MIN_TESTS = 6


class CompilacionError(TraceError):
    """An agent could not produce valid code + tests (LLM failure or still broken after the
    repair rounds). Nothing is stored."""

    status_code = 502
    code = "compilation_failed"


@dataclass(frozen=True)
class Compilacion:
    codigo_a: str
    codigo_b: str
    tests_a: list[Test]
    tests_b: list[Test]
    # {"valida": bool, "tests": [...], "historico": {"instancias": n, "coinciden": k},
    #  "discrepancias": [str, ...]}
    # `valida` is True only if both codes pass every test and agree on every past instance.
    informe: dict[str, Any]


# Structured output. instancia/fuentes/otras travel as JSON strings: free-form objects are
# not representable in strict JSON-schema modes (OpenAI would force them to be empty).
class TestPropuesto(BaseModel):
    nombre: str
    instancia_json: str
    fuentes_json: str
    otras_json: str
    salta: bool


class Propuesta(BaseModel):
    codigo: str
    tests: list[TestPropuesto]


SISTEMA = """Eres un compilador de reglas de negocio a Python. Conviertes UNA regla escrita en \
texto en código determinista y en tests, solo a partir del texto de la regla y del contexto dado.

Contrato del código (campo `codigo`, solo código Python, sin markdown):
- Define `def evaluar(instancia, fuentes, otras) -> dict` que devuelve \
{"salta": bool, "motivo": str}.
- `instancia`: {símbolo: valor} de la instancia evaluada.
- `fuentes`: {nombre_fuente: [fila, ...]}, cada fila un dict {columna: valor}.
- `otras`: lista de las demás instancias del proceso, cada una {símbolo: valor} más la clave \
"_instancia" (su nombre). Úsala solo si la regla habla de otras instancias \
(duplicados, acumulados...).
- Función pura y determinista: sin red, disco, reloj, aleatoriedad ni estado global. \
Solo se permiten estos imports: decimal, datetime, re, math, unicodedata.
- Tipo de regla: `requisito` = algo que debe cumplirse; salta cuando NO se cumple. \
`prohibicion` = algo que no debe darse; salta cuando SÍ se cumple.
- Importes y otros decimales: compara con Decimal(str(valor)). Usa tolerancia solo si la \
regla la indica.
- Los valores pueden faltar o ser None: trátalo de forma explícita y según la regla.
- `motivo`: código corto en MAYÚSCULAS_CON_GUIONES_BAJOS (p. ej. "VALOR_NO_COINCIDE", \
"LIMITE_SUPERADO"). Cuando no salta, un motivo como "OK".

Descripción del proceso: si el contexto la trae, contiene convenciones que valen para todas \
las reglas del proceso (normalización de claves, unidades de importes, tolerancias, qué hacer \
si falta un valor...). Aplícalas siempre y antes que tus propias suposiciones. Si contradicen \
el texto de la regla, manda el texto de la regla.

Tests (campo `tests`, al menos 6): cada uno con `nombre`, `instancia_json` (objeto JSON), \
`fuentes_json` (objeto JSON), `otras_json` (lista JSON) y `salta` (lo que debe devolver la \
regla). Cubre casos en que salta y en que no, y los límites y excepciones que el texto de la \
regla menciona. Los tests deben pasar con tu propio código."""


def _contexto(
    regla: Regla,
    simbolos: list[Simbolo],
    fuentes: dict[str, list[dict[str, Any]]],
    descripcion: str,
) -> str:
    lineas = [
        "Descripción del proceso (convenciones comunes a todas sus reglas):",
        descripcion or "(sin descripción)",
        "",
        f"Regla ({regla.tipo}): {regla.texto}",
        "",
        "Símbolos de cada instancia (nombre, tipo, descripción):",
        *(f"- {s.nombre} ({s.tipo}): {s.descripcion}" for s in simbolos),
        "",
        "Fuentes de verdad disponibles (columnas y 3 filas de ejemplo):",
    ]
    for nombre, filas in fuentes.items():
        columnas = list(dict.fromkeys(c for f in filas for c in f))
        lineas.append(f"- {nombre}: columnas {columnas}")
        lineas += [f"    {json.dumps(f, ensure_ascii=False, default=str)}" for f in filas[:3]]
    if not fuentes:
        lineas.append("- (ninguna)")
    return "\n".join(lineas)


def _tests(propuesta: Propuesta) -> list[Test]:
    if len(propuesta.tests) < MIN_TESTS:
        raise ValueError(f"Hacen falta al menos {MIN_TESTS} tests; hay {len(propuesta.tests)}")
    tests = []
    for t in propuesta.tests:
        try:
            tests.append(
                {
                    "nombre": t.nombre,
                    "instancia": json.loads(t.instancia_json),
                    "fuentes": json.loads(t.fuentes_json),
                    "otras": json.loads(t.otras_json),
                    "salta": t.salta,
                }
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Test {t.nombre!r}: JSON inválido ({e})") from e
    return tests


def _casos(tests: list[Test]) -> list[tuple[dict, dict, list]]:
    return [(t["instancia"], t["fuentes"], t["otras"]) for t in tests]


def _texto(resultado: Any) -> str:
    if isinstance(resultado, dict) and isinstance(resultado.get("salta"), bool):
        return f"salta ({resultado.get('motivo')})" if resultado["salta"] else "no salta"
    return f"error: {resultado}"


def _salta(resultado: Any) -> bool | None:
    """The verdict, or None if the run failed or returned something malformed."""
    if isinstance(resultado, dict) and isinstance(resultado.get("salta"), bool):
        return resultado["salta"]
    return None


def _errores_propios(codigo: str, tests: list[Test]) -> str | None:
    """What is wrong with an agent's own code against its own tests, or None."""
    try:
        sandbox.comprobar(codigo)
        resultados = sandbox.ejecutar_lote(codigo, _casos(tests))
    except sandbox.ErrorSandbox as e:
        return f"El código no pasa la comprobación del sandbox: {e}"
    fallos = [
        f"- {t['nombre']}: esperado {'salta' if t['salta'] else 'no salta'}, obtenido {_texto(r)}"
        for t, r in zip(tests, resultados, strict=True)
        if _salta(r) is not t["salta"]
    ]
    return "Tu código falla tus propios tests:\n" + "\n".join(fallos) if fallos else None


async def _agente(session: AsyncSession, papel: str, contexto: str) -> tuple[str, list[Test], dict]:
    """One blind agent. It only ever sees the context and its own errors."""
    mensajes: list[dict[str, Any]] = [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": contexto},
    ]
    traza: dict[str, Any] = {"papel": papel, "reparaciones": 0, "coste": None, "latencia_ms": 0}
    for ronda in range(MAX_REPARACIONES + 1):
        try:
            respuesta = await cliente.completar(session, papel, mensajes, Propuesta)
        except Exception as e:
            raise CompilacionError(f"{papel}: la llamada al LLM falló: {e}") from e
        traza["modelo"] = respuesta.modelo
        traza["latencia_ms"] += respuesta.latencia_ms
        if respuesta.coste is not None:
            traza["coste"] = (traza["coste"] or 0) + respuesta.coste
        try:
            propuesta = Propuesta.model_validate_json(respuesta.contenido)
            tests = _tests(propuesta)
            error = await asyncio.to_thread(_errores_propios, propuesta.codigo, tests)
        except (ValidationError, ValueError) as e:
            error = f"Respuesta mal formada: {e}"
        if error is None:
            traza["reparaciones"] = ronda
            return propuesta.codigo, tests, traza
        mensajes += [
            {"role": "assistant", "content": respuesta.contenido},
            {
                "role": "user",
                "content": f"{error}\n\nCorrige y devuelve la propuesta completa "
                "(código y tests) en el mismo formato.",
            },
        ]
    raise CompilacionError(
        f"{papel}: sigue fallando tras {MAX_REPARACIONES} rondas de reparación: {error}"
    )


def validar(
    codigo_a: str,
    codigo_b: str,
    tests_a: list[Test],
    tests_b: list[Test],
    historico: Historico,
    fuentes: dict[str, list[dict[str, Any]]],
    ejecutar_lote: Callable[..., list[Any]],
) -> dict[str, Any]:
    """Cross-check: every test on both codes, both codes on the whole history (P9)."""
    tests = [("A", t) for t in tests_a] + [("B", t) for t in tests_b]
    # ponytail: O(n²) `otras` per instance; fine for a process history of hundreds.
    casos = _casos([t for _, t in tests]) + [
        (simbolos, fuentes, [dict(s, _instancia=n) for j, (n, s) in enumerate(historico) if j != i])
        for i, (_, simbolos) in enumerate(historico)
    ]

    def correr(codigo: str) -> list[Any]:
        try:
            return ejecutar_lote(codigo, casos)
        except Exception as e:  # the whole batch failed: every case reports it
            return [e] * len(casos)

    ra, rb = correr(codigo_a), correr(codigo_b)
    informe_tests, discrepancias = [], []
    for (autor, t), a, b in zip(tests, ra, rb, strict=False):
        pasa = _salta(a) is t["salta"] and _salta(b) is t["salta"]
        informe_tests.append(
            {
                "autor": autor,
                "nombre": t["nombre"],
                "esperado": t["salta"],
                "a": _texto(a),
                "b": _texto(b),
                "pasa": pasa,
            }
        )
        if not pasa:
            esperado = "salta" if t["salta"] else "no salta"
            discrepancias.append(
                f"Test {autor} «{t['nombre']}» (esperado: {esperado}): "
                f"A dice {_texto(a)}; B dice {_texto(b)}"
            )
    coinciden = 0
    for (nombre, _), a, b in zip(historico, ra[len(tests) :], rb[len(tests) :], strict=True):
        if _salta(a) is not None and _salta(a) is _salta(b):
            coinciden += 1
        else:
            discrepancias.append(f"Instancia {nombre}: A dice {_texto(a)}; B dice {_texto(b)}")
    return {
        "valida": all(t["pasa"] for t in informe_tests) and coinciden == len(historico),
        "tests": informe_tests,
        "historico": {"instancias": len(historico), "coinciden": coinciden},
        "discrepancias": discrepancias,
    }


async def _leer(
    session: AsyncSession, proceso_id: int
) -> tuple[str, dict[str, list[dict[str, Any]]], Historico, list[ConfigLLM]]:
    """The process description, current sources (latest load per name), the process history,
    and both agents' LLM config preloaded: the two agents run concurrently on one session,
    and `completar`'s `session.get` must then hit the identity map instead of the connection."""
    descripcion = await session.scalar(select(Proceso.descripcion).where(Proceso.id == proceso_id))
    cargas = await session.scalars(
        select(Fuente)
        .where(Fuente.proceso_id == proceso_id)
        .order_by(Fuente.nombre, Fuente.cargada.desc())
        .distinct(Fuente.nombre)
    )
    fuentes = {f.nombre: f.filas for f in cargas}
    filas = await session.execute(
        select(Instancia.nombre, Instancia.simbolos)
        .where(Instancia.proceso_id == proceso_id)
        .order_by(Instancia.id)
    )
    historico = [
        (nombre, {k: v.get("valor") for k, v in simbolos.items()})
        for nombre, simbolos in filas
        if simbolos
    ]
    configs = list(await session.scalars(select(ConfigLLM).where(ConfigLLM.papel.in_(PAPELES))))
    return descripcion or "", fuentes, historico, configs


async def compilar(session: AsyncSession, regla: Regla, simbolos: list[Simbolo]) -> Compilacion:
    """Agents A and B each write, blind to the other, a function

        def evaluar(instancia: dict, fuentes: dict[str, list[dict]], otras: list[dict]) -> dict
            # returns {"salta": bool, "motivo": str}

    plus tests. Then every test runs against both codes, and both codes run on the
    process history. The result is reported, never silently accepted."""
    descripcion, fuentes, historico, _configs = await _leer(session, regla.proceso_id)
    contexto = _contexto(regla, simbolos, fuentes, descripcion)  # `_configs`: keep refs alive
    (codigo_a, tests_a, traza_a), (codigo_b, tests_b, traza_b) = await asyncio.gather(
        *(_agente(session, papel, contexto) for papel in PAPELES)
    )
    informe = await asyncio.to_thread(
        validar, codigo_a, codigo_b, tests_a, tests_b, historico, fuentes, sandbox.ejecutar_lote
    )
    for traza in (traza_a, traza_b):
        registrar(
            session,
            "compilar_regla",
            datos={
                "regla_id": regla.id,
                "papel": traza["papel"],
                "modelo": traza["modelo"],
                "reparaciones": traza["reparaciones"],
                "valida": informe["valida"],
            },
            latencia_ms=traza["latencia_ms"],
            coste=traza["coste"],
        )
    return Compilacion(codigo_a, codigo_b, tests_a, tests_b, informe)

"""Compiler without network, LLM or database: the sandbox is faked with a plain `exec`
(acceptable in tests only) and the DB reads are monkeypatched."""

import json
from types import SimpleNamespace

import pytest

from app.features.agentes import compilador, sandbox
from app.features.llm.cliente import Respuesta


class ErrorSandbox(Exception):
    pass


def comprobar(codigo: str) -> None:
    try:
        compile(codigo, "<regla>", "exec")
    except SyntaxError as e:
        raise ErrorSandbox(str(e)) from e


def ejecutar_lote(codigo: str, casos: list, timeout_s: float = 10.0) -> list:
    espacio: dict = {}
    exec(codigo, espacio)
    resultados = []
    for caso in casos:
        try:
            resultados.append(espacio["evaluar"](*caso))
        except Exception as e:
            resultados.append(ErrorSandbox(repr(e)))
    return resultados


@pytest.fixture(autouse=True)
def sandbox_falso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "ErrorSandbox", ErrorSandbox, raising=False)
    monkeypatch.setattr(sandbox, "comprobar", comprobar, raising=False)
    monkeypatch.setattr(sandbox, "ejecutar_lote", ejecutar_lote, raising=False)


# "Si importe > 1000, escalar" (prohibición)
CODIGO = """
from decimal import Decimal

def evaluar(instancia, fuentes, otras):
    if Decimal(str(instancia["importe"])) > Decimal("1000"):
        return {"salta": True, "motivo": "IMPORTE_ALTO"}
    return {"salta": False, "motivo": "OK"}
"""
# Same rule read as ">=": only differs at exactly 1000.
CODIGO_MAYOR_IGUAL = CODIGO.replace('> Decimal("1000")', '>= Decimal("1000")')
CODIGO_ROTO = CODIGO.replace('instancia["importe"]', 'instancia["no_existe"]')


def _test(nombre: str, importe: float, salta: bool) -> dict:
    return {
        "nombre": nombre,
        "instancia": {"importe": importe},
        "fuentes": {},
        "otras": [],
        "salta": salta,
    }


TESTS = [_test("alto", 1500, True), _test("bajo", 10, False)]
HISTORICO = [("f1.pdf", {"importe": 50}), ("f2.pdf", {"importe": 2000})]


def test_validar_coinciden() -> None:
    informe = compilador.validar(CODIGO, CODIGO, TESTS, TESTS, HISTORICO, {}, ejecutar_lote)
    assert informe["valida"] is True
    assert informe["historico"] == {"instancias": 2, "coinciden": 2}
    assert informe["discrepancias"] == []
    assert len(informe["tests"]) == 4 and all(t["pasa"] for t in informe["tests"])


def test_validar_fallo_cruzado() -> None:
    tests_b = [*TESTS, _test("justo 1000", 1000, True)]
    informe = compilador.validar(
        CODIGO, CODIGO_MAYOR_IGUAL, TESTS, tests_b, HISTORICO, {}, ejecutar_lote
    )
    assert informe["valida"] is False
    [fallo] = [t for t in informe["tests"] if not t["pasa"]]
    assert fallo == {
        "autor": "B",
        "nombre": "justo 1000",
        "esperado": True,
        "a": "no salta",
        "b": "salta (IMPORTE_ALTO)",
        "pasa": False,
    }
    assert len(informe["discrepancias"]) == 1 and "justo 1000" in informe["discrepancias"][0]


def test_validar_discrepancia_historico() -> None:
    historico = [*HISTORICO, ("f3.pdf", {"importe": 1000})]
    informe = compilador.validar(
        CODIGO, CODIGO_MAYOR_IGUAL, TESTS, TESTS, historico, {}, ejecutar_lote
    )
    assert informe["valida"] is False
    assert informe["historico"] == {"instancias": 3, "coinciden": 2}
    assert informe["discrepancias"] == [
        "Instancia f3.pdf: A dice no salta; B dice salta (IMPORTE_ALTO)"
    ]


def test_validar_error_de_ejecucion() -> None:
    informe = compilador.validar(CODIGO, CODIGO_ROTO, TESTS, [], HISTORICO, {}, ejecutar_lote)
    assert informe["valida"] is False
    assert all(t["b"].startswith("error: KeyError") for t in informe["tests"])
    assert informe["historico"]["coinciden"] == 0
    assert len(informe["discrepancias"]) == 4


def test_validar_otras_excluye_la_propia() -> None:
    codigo = """
def evaluar(instancia, fuentes, otras):
    dup = any(o["num"] == instancia["num"] for o in otras)
    return {"salta": dup, "motivo": "DUPLICADA" if dup else "OK"}
"""
    historico = [("a", {"num": 1}), ("b", {"num": 1}), ("c", {"num": 2})]
    vistos = []

    def espia(codigo: str, casos: list) -> list:
        vistos.extend(casos)
        return ejecutar_lote(codigo, casos)

    informe = compilador.validar(codigo, codigo, [], [], historico, {"p": []}, espia)
    assert informe["valida"] is True
    assert vistos[0] == (
        {"num": 1},
        {"p": []},
        [{"num": 1, "_instancia": "b"}, {"num": 2, "_instancia": "c"}],
    )


def _propuesta(codigo: str) -> str:
    tests = [
        {
            "nombre": f"importe {importe}",
            "instancia_json": json.dumps({"importe": importe}),
            "fuentes_json": "{}",
            "otras_json": "[]",
            "salta": importe > 1000,
        }
        for importe in (0, 10, 999.99, 1000, 1000.01, 5000)
    ]
    return json.dumps({"codigo": codigo, "tests": tests})


class SesionFalsa:
    def __init__(self) -> None:
        self.añadidos: list = []

    def add(self, objeto: object) -> None:
        self.añadidos.append(objeto)


@pytest.fixture
def llm(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Canned answers per role, consumed in order; records what each role was sent."""
    guion: dict = {"respuestas": {}, "mensajes": {"compilador_a": [], "compilador_b": []}}

    async def completar(session, papel, mensajes, formato=None) -> Respuesta:
        guion["mensajes"][papel].append(list(mensajes))
        contenido = guion["respuestas"][papel].pop(0)
        return Respuesta(contenido=contenido, modelo=f"falso/{papel}", coste=0.01, latencia_ms=5)

    async def leer(session, proceso_id):
        return DESCRIPCION, {"proveedores": [{"cif": "B1", "iban": "ES1"}]}, HISTORICO, []

    monkeypatch.setattr(compilador.cliente, "completar", completar)
    monkeypatch.setattr(compilador, "_leer", leer)
    return guion


DESCRIPCION = "Importes en céntimos enteros; si falta un valor, la regla no salta."
REGLA = SimpleNamespace(id=7, proceso_id=1, texto="Si importe > 1000, escalar", tipo="prohibicion")
SIMBOLOS = [SimpleNamespace(nombre="importe", tipo="numero", descripcion="total factura")]


async def test_compilar_extremo_a_extremo(llm: dict) -> None:
    llm["respuestas"] = {
        "compilador_a": [_propuesta(CODIGO)],
        "compilador_b": [_propuesta(CODIGO)],
    }
    sesion = SesionFalsa()
    resultado = await compilador.compilar(sesion, REGLA, SIMBOLOS)
    assert resultado.informe["valida"] is True
    assert len(resultado.informe["tests"]) == 12
    assert resultado.tests_a[3] == {
        "nombre": "importe 1000",
        "instancia": {"importe": 1000},
        "fuentes": {},
        "otras": [],
        "salta": False,
    }
    # Both agents got the same context, which carries the rule, symbols and sources.
    [[ctx_a]], [[ctx_b]] = ([m[1:] for m in v] for v in llm["mensajes"].values())
    assert ctx_a == ctx_b
    assert "prohibicion" in ctx_a["content"] and "importe (numero)" in ctx_a["content"]
    assert '"iban": "ES1"' in ctx_a["content"]
    assert DESCRIPCION in ctx_a["content"]
    eventos = [e for e in sesion.añadidos if e.paso == "compilar_regla"]
    assert [e.datos["papel"] for e in eventos] == ["compilador_a", "compilador_b"]
    assert all(e.datos["reparaciones"] == 0 and e.coste == 0.01 for e in eventos)


async def test_compilar_autorreparacion(llm: dict) -> None:
    llm["respuestas"] = {
        "compilador_a": [_propuesta("def evaluar(:\n"), _propuesta(CODIGO)],
        "compilador_b": [_propuesta(CODIGO)],
    }
    sesion = SesionFalsa()
    resultado = await compilador.compilar(sesion, REGLA, SIMBOLOS)
    a, b = sesion.añadidos
    assert (a.datos["reparaciones"], b.datos["reparaciones"]) == (1, 0)
    assert a.latencia_ms == 10
    # A only ever saw its own broken answer and the sandbox error, never B's work.
    reparacion = llm["mensajes"]["compilador_a"][1]
    assert "sandbox" in reparacion[-1]["content"]
    assert DESCRIPCION in reparacion[1]["content"]  # its own context, kept in the repair round
    assert all(m["role"] != "assistant" or "def evaluar(:" in m["content"] for m in reparacion)
    assert resultado.informe["valida"] is True


async def test_compilar_sin_arreglo_falla(llm: dict) -> None:
    llm["respuestas"] = {
        "compilador_a": [_propuesta("def evaluar(:\n")] * 3,
        "compilador_b": [_propuesta(CODIGO)],
    }
    with pytest.raises(compilador.CompilacionError) as e:
        await compilador.compilar(SesionFalsa(), REGLA, SIMBOLOS)
    assert e.value.status_code == 502 and "compilador_a" in e.value.message

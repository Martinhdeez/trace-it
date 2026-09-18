import time

import pytest

from app.features.agentes.sandbox import ErrorSandbox, comprobar, ejecutar, ejecutar_lote

VALIDA = """
from decimal import Decimal

def evaluar(instancia, fuentes, otras):
    total = Decimal(str(instancia["total"]))
    return {"salta": total > Decimal("100.00"), "motivo": f"total {total}"}
"""


def regla(cuerpo: str) -> str:
    return f"def evaluar(instancia, fuentes, otras):\n    {cuerpo}\n"


def test_regla_valida_devuelve_resultado():
    assert ejecutar(VALIDA, {"total": "150.50"}, {}, []) == {
        "salta": True,
        "motivo": "total 150.50",
    }


@pytest.mark.parametrize(
    "cuerpo",
    [
        'return {"salta": 1, "motivo": "x"}',
        'return {"salta": "si", "motivo": "x"}',
        'return {"salta": True}',
        'return {"salta": True, "motivo": "x", "decision": "PAGAR"}',
        'return {"salta": True, "motivo": 3}',
        "return [True]",
        "return object()",
        "raise ValueError('mal')",
        "raise SystemExit(0)",
    ],
)
def test_resultado_invalido_o_excepcion(cuerpo):
    with pytest.raises(ErrorSandbox):
        ejecutar(regla(cuerpo), {}, {}, [])


@pytest.mark.parametrize(
    "codigo",
    [
        "import os\n" + regla("return {}"),
        "import socket\n" + regla("return {}"),
        "from subprocess import run\n" + regla("return {}"),
        "from . import x\n" + regla("return {}"),
        regla("open('/etc/passwd')"),
        regla("__import__('os')"),
        regla("return ().__class__.__bases__[0].__subclasses__()"),
        regla("return (x for x in []).gi_frame.f_back"),
        regla("getattr(1, 'real')"),
        "def otra():\n    pass\n",
        "def evaluar(:\n",
    ],
)
def test_codigo_prohibido_rechazado_antes_de_ejecutar(codigo):
    with pytest.raises(ErrorSandbox):
        comprobar(codigo)
    with pytest.raises(ErrorSandbox):
        ejecutar(codigo, {}, {}, [])


def test_modulo_permitido_no_expone_otros_modulos():
    with pytest.raises(ErrorSandbox, match="AttributeError"):
        ejecutar(regla("import re\n    re.enum.sys.modules"), {}, {}, [])


def test_bucle_infinito_agota_el_tiempo():
    inicio = time.monotonic()
    with pytest.raises(ErrorSandbox, match="Tiempo agotado"):
        ejecutar(regla("while True:\n        pass"), {}, {}, [], timeout_s=0.5)
    assert time.monotonic() - inicio < 2


def test_lote_con_un_caso_malo_solo_falla_ese_caso():
    casos = [({"total": "50"}, {}, []), ({}, {}, []), ({"total": "500"}, {}, [])]
    ok1, malo, ok2 = ejecutar_lote(VALIDA, casos)
    assert ok1 == {"salta": False, "motivo": "total 50"}
    assert isinstance(malo, ErrorSandbox) and "KeyError" in malo.message
    assert ok2 == {"salta": True, "motivo": "total 500"}

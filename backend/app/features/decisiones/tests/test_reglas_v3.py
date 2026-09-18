"""The hand-written v3 rules, run for real in the sandbox.

One case per rule that must fire, plus an invoice that must leave all sixteen silent. When
the compiler starts generating these, this file is what its output has to agree with.
"""

from typing import Any

import pytest

from app.features.agentes import sandbox
from app.features.decisiones.motor import decidir
from app.features.decisiones.tests.reglas_v3 import REGLAS_V3
from app.features.reglas.model import Regla

LIMPIA: dict[str, Any] = {
    "nif_emisor": "B96233419",
    "iban": "ES21 0075 2345 6706 0012 3456",
    "pedido": "PO-2026-0008",
    "fecha": "2026-05-02",
    "base": 8494.10,
    "tipo_iva": 21,
    "cuota_iva": 1783.76,
    "total": 10277.86,
}
PROVEEDOR = {"id": "P007", "nif": "B96233419", "iban": "ES2100752345670600123456"}
PEDIDO = {
    "pedido": "PO-2026-0008",
    "proveedor_id": "P007",
    "nif": "B96233419",
    "importe_total": 10277.86,
    "estado": "ABIERTO",
}
ASIENTO = {
    "pedido": "PO-2026-0008",
    "proveedor_id": "P007",
    "nif": "B96233419",
    "importe": 10277.86,
    "estado": "PENDIENTE",
}
FUENTES: dict[str, list[dict[str, Any]]] = {
    "proveedores": [PROVEEDOR],
    "pedidos": [PEDIDO],
    "erp": [ASIENTO],
    "parametros": [{"fecha_corte": "2026-09-19"}],
}

# Per rule (1-based): what to change so that it, and only it, has something to say.
QUE_LA_HACE_SALTAR: dict[int, tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]] = {
    1: ({"iban": None}, {}, []),
    2: ({"nif_emisor": "B00000000"}, {}, []),
    3: ({"iban": "ES39 0081 5290 0700 1234 5678"}, {}, []),
    4: ({}, {"proveedores": [PROVEEDOR, {**PROVEEDOR, "iban": "ES3900815290070012345678"}]}, []),
    5: ({"pedido": "PO-2026-9999"}, {}, []),
    6: ({}, {"pedidos": [{**PEDIDO, "nif": "A41220987"}]}, []),
    7: ({}, {"pedidos": [{**PEDIDO, "importe_total": 9999.00}]}, []),
    8: ({"cuota_iva": 400.00}, {}, []),
    9: ({"tipo_iva": 10}, {}, []),
    10: ({"total": 9999.99}, {}, []),
    11: ({"fecha": "2026-02-31"}, {}, []),
    12: ({"fecha": "2027-01-01"}, {}, []),
    13: ({}, {"erp": []}, []),
    14: ({}, {"erp": [{**ASIENTO, "importe": 9999.00}]}, []),
    15: ({}, {"erp": [{**ASIENTO, "estado": "PAGADA"}]}, []),
    16: ({}, {}, [{**LIMPIA, "_instancia": "otra_factura.pdf"}]),
}


def ejecutar(numero: int, instancia: dict, fuentes: dict, otras: list) -> dict[str, Any]:
    return sandbox.ejecutar(REGLAS_V3[numero - 1], instancia, fuentes, otras)


@pytest.mark.parametrize("numero", sorted(QUE_LA_HACE_SALTAR))
def test_cada_regla_salta_cuando_debe(numero: int) -> None:
    simbolos, fuentes, otras = QUE_LA_HACE_SALTAR[numero]

    resultado = ejecutar(numero, {**LIMPIA, **simbolos}, {**FUENTES, **fuentes}, otras)

    assert resultado["salta"] is True
    assert resultado["motivo"], "una regla que salta explica por qué"


@pytest.mark.parametrize("numero", sorted(QUE_LA_HACE_SALTAR))
def test_ninguna_regla_salta_con_una_factura_correcta(numero: int) -> None:
    assert ejecutar(numero, LIMPIA, FUENTES, [])["salta"] is False


@pytest.mark.parametrize("numero", sorted(QUE_LA_HACE_SALTAR))
def test_ninguna_regla_falla_sin_simbolos_ni_fuentes(numero: int) -> None:
    """Missing evidence is not an error: the rule that checks for it is the one that fires."""
    resultado = ejecutar(numero, {}, {}, [])

    assert resultado["salta"] is (numero == 1)


PRIORIDADES = {"ESCALAR": 3, "NO_PAGAR": 2, "PAGAR": 1}
DECISIONES = [
    "ESCALAR", "NO_PAGAR", "NO_PAGAR", "ESCALAR", "NO_PAGAR", "NO_PAGAR", "NO_PAGAR",
    "NO_PAGAR", "ESCALAR", "NO_PAGAR", "NO_PAGAR", "NO_PAGAR", "NO_PAGAR", "NO_PAGAR",
    "NO_PAGAR", "ESCALAR",
]  # fmt: skip
REGLAS = [
    Regla(id=n, texto=f"R{n:02d}", decision=DECISIONES[n - 1], codigo_a=codigo, hash=f"h{n}")
    for n, codigo in enumerate(REGLAS_V3, 1)
]


def decidir_factura(instancia: dict, fuentes: dict, otras: list) -> str:
    return decidir(
        REGLAS, PRIORIDADES, "PAGAR", "ESCALAR", instancia, fuentes, otras, sandbox.ejecutar
    ).decision


def test_el_proceso_completo_sobre_las_tres_facturas_de_referencia() -> None:
    """The whole norm at once, on the three cases the rules draft calls out."""
    ya_pagada = {"erp": [{**ASIENTO, "estado": "PAGADA"}]}
    iban_nuevo = {"iban": "ES39 0081 5290 0700 1234 5678"}

    assert decidir_factura(LIMPIA, FUENTES, []) == "PAGAR"
    assert decidir_factura(LIMPIA, {**FUENTES, **ya_pagada}, []) == "NO_PAGAR"
    assert decidir_factura({**LIMPIA, **iban_nuevo}, FUENTES, []) == "NO_PAGAR"


def test_escalar_gana_a_no_pagar() -> None:
    """An invoice that is both wrong and suspicious goes to a person, not to a refusal."""
    roto = {**LIMPIA, "tipo_iva": 10, "cuota_iva": 849.41, "total": 9343.51}

    fuentes = {**FUENTES, "erp": [{**ASIENTO, "estado": "PAGADA"}]}

    assert decidir_factura(roto, fuentes, []) == "ESCALAR"

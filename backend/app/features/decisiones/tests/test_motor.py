"""The engine on the invoice process: PAGAR by default, NO_PAGAR and ESCALAR by rule."""

from typing import Any

import pytest

from app.features.decisiones.motor import decidir
from app.features.reglas.model import Regla

PRIORIDADES = {"ESCALAR": 3, "NO_PAGAR": 2, "PAGAR": 1}
POR_DEFECTO = "PAGAR"
ESCALAR = "ESCALAR"

# Rule text -> what its compiled code does. The real code comes from Martín's compiler and
# runs in his sandbox; here a rule is a plain function, which is all the engine needs.
REGLAS_V3 = {
    "iban_distinto": (
        "prohibicion",
        "ESCALAR",
        lambda i, f, o: i["iban"] != _proveedor(f, i["nif"])["iban"],
    ),
    "pedido_ya_pagado": (
        "prohibicion",
        "NO_PAGAR",
        lambda i, f, o: _asiento(f, i["pedido"])["estado"] == "PAGADA",
    ),
    "fecha_futura": (
        "requisito",
        "ESCALAR",
        lambda i, f, o: i["fecha"] > f["parametros"][0]["fecha_corte"],
    ),
}

PROVEEDORES = [
    {"nif": "B96233419", "iban": "ES2100752345670600123456"},
    {"nif": "B78451236", "iban": "ES9368884400123588900142"},
]
ASIENTOS = [
    {"pedido": "PO-2026-0008", "estado": "PENDIENTE"},
    {"pedido": "PO-2026-0474", "estado": "PAGADA"},
    {"pedido": "PO-2026-0813", "estado": "PENDIENTE"},
]
PARAMETROS = [{"fecha_corte": "2026-09-19"}]  # a rule never reads the clock (P18)
FUENTES = {"proveedores": PROVEEDORES, "erp": ASIENTOS, "parametros": PARAMETROS}

# factura_1217.pdf: everything matches and the order is unpaid.
LIMPIA = {
    "nif": "B96233419",
    "iban": "ES2100752345670600123456",
    "pedido": "PO-2026-0008",
    "fecha": "2026-05-02",
}
# FA-1016_papelería.pdf: correct in every way, but the ERP already paid the order.
YA_PAGADA = {**LIMPIA, "pedido": "PO-2026-0474"}
# FA-5044_mensajería2.pdf: a new IBAN the supplier master does not know.
IBAN_NUEVO = {
    "nif": "B78451236",
    "iban": "ES3900815290070012345678",
    "pedido": "PO-2026-0813",
    "fecha": "2026-05-02",
}


def _proveedor(fuentes: dict, nif: str) -> dict:
    return next(p for p in fuentes["proveedores"] if p["nif"] == nif)


def _asiento(fuentes: dict, pedido: str) -> dict:
    return next(a for a in fuentes["erp"] if a["pedido"] == pedido)


def reglas(*nombres: str) -> list[Regla]:
    return [
        Regla(
            id=numero,
            texto=nombre,
            tipo=REGLAS_V3[nombre][0],
            decision=REGLAS_V3[nombre][1],
            codigo_a=nombre,
            hash=f"hash-{nombre}",
        )
        for numero, nombre in enumerate(nombres, start=1)
    ]


def ejecutar(codigo: str, instancia: dict, fuentes: dict, otras: list) -> dict:
    """Stand-in for `agentes.sandbox.ejecutar` until it exists. Raises, like the real one."""
    salta = REGLAS_V3[codigo][2](instancia, fuentes, otras)
    return {"salta": salta, "motivo": codigo if salta else ""}


def decidir_factura(activas: list[Regla], instancia: dict[str, Any], **extra: Any) -> Any:
    return decidir(
        activas,
        PRIORIDADES,
        POR_DEFECTO,
        ESCALAR,
        instancia,
        FUENTES,
        [],
        extra.get("ejecutar", ejecutar),
    )


def test_ninguna_regla_salta_decide_por_defecto() -> None:
    veredicto = decidir_factura(reglas("iban_distinto", "pedido_ya_pagado"), LIMPIA)

    assert veredicto.decision == "PAGAR"
    assert [(r.regla_id, r.salta) for r in veredicto.resultados] == [(1, False), (2, False)]


def test_una_regla_salta() -> None:
    veredicto = decidir_factura(reglas("iban_distinto", "pedido_ya_pagado"), YA_PAGADA)

    assert veredicto.decision == "NO_PAGAR"
    assert veredicto.motivo == "pedido_ya_pagado"


def test_saltan_varias_gana_la_de_mayor_prioridad() -> None:
    """The IBAN is unknown *and* the order is already paid: a person looks at it first."""
    activas = reglas("iban_distinto", "pedido_ya_pagado")

    veredicto = decidir_factura(activas, {**IBAN_NUEVO, "pedido": "PO-2026-0474"})

    assert veredicto.decision == "ESCALAR"
    assert all(r.salta for r in veredicto.resultados)


def test_una_regla_falla_y_el_caso_se_escala() -> None:
    """A rule that cannot be evaluated never produces a silent PAGAR."""
    desconocida = {**LIMPIA, "nif": "B00000000"}  # not in the supplier master

    veredicto = decidir_factura(reglas("iban_distinto", "pedido_ya_pagado"), desconocida)

    assert veredicto.decision == "ESCALAR"
    assert "ERROR_REGLA 1" in veredicto.motivo
    assert veredicto.resultados[0].salta is None
    assert veredicto.resultados[1].salta is False  # every rule still ran


def test_empate_de_prioridad_entre_decisiones_distintas_se_escala() -> None:
    activas = reglas("iban_distinto", "pedido_ya_pagado")
    empate = {"ESCALAR": 2, "NO_PAGAR": 2, "PAGAR": 1}

    veredicto = decidir(
        activas,
        empate,
        POR_DEFECTO,
        ESCALAR,
        {**IBAN_NUEVO, "pedido": "PO-2026-0474"},
        FUENTES,
        [],
        ejecutar,
    )

    assert veredicto.decision == "ESCALAR"
    assert "CONFLICTO_REGLAS" in veredicto.motivo


def test_la_fecha_de_corte_llega_por_una_fuente() -> None:
    """Rules are pure: they never read the clock, so a past decision replays identically."""
    activas = reglas("fecha_futura")
    futura = {**LIMPIA, "fecha": "2027-01-01"}

    assert decidir_factura(activas, futura).decision == "ESCALAR"
    assert decidir_factura(activas, LIMPIA).decision == "PAGAR"


def test_el_veredicto_identifica_el_conjunto_de_reglas() -> None:
    activas = reglas("iban_distinto", "pedido_ya_pagado")

    primero = decidir_factura(activas, LIMPIA)
    segundo = decidir_factura(list(reversed(activas)), LIMPIA)
    tercero = decidir_factura(reglas("iban_distinto"), LIMPIA)

    assert primero.reglas_hash == segundo.reglas_hash  # order is not a change
    assert primero.reglas_hash != tercero.reglas_hash  # removing a rule is


@pytest.mark.parametrize("respuesta", [{"motivo": "x"}, "no es un dict", None])
def test_una_respuesta_mal_formada_se_escala(respuesta: Any) -> None:
    def roto(*_: Any) -> Any:
        return respuesta

    veredicto = decidir_factura(reglas("iban_distinto"), LIMPIA, ejecutar=roto)

    assert veredicto.decision == "ESCALAR"

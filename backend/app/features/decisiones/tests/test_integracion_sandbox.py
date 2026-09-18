"""The engine against the real sandbox, not a fake.

The other engine tests inject a fake executor, so nothing there would notice if the two
sides of the contract drifted apart. This one runs compiled-looking code for real.
"""

from app.features.agentes import sandbox
from app.features.decisiones.motor import decidir
from app.features.reglas.model import Regla

CODIGO = """
def evaluar(instancia, fuentes, otras):
    aprobado = None
    for fila in fuentes["proveedores"]:
        if fila["nif"] == instancia["nif"]:
            aprobado = fila["iban"]
    if aprobado is None:
        return {"salta": True, "motivo": "SUPPLIER_NOT_FOUND"}
    if instancia["iban"] != aprobado:
        return {"salta": True, "motivo": "IBAN_MISMATCH"}
    return {"salta": False, "motivo": ""}
"""

FUENTES = {"proveedores": [{"nif": "B96233419", "iban": "ES2100752345670600123456"}]}
PRIORIDADES = {"ESCALAR": 3, "PAGAR": 1}
REGLAS = [Regla(id=1, texto="El IBAN es el del maestro", decision="ESCALAR", codigo_a=CODIGO)]


def decidir_con_sandbox(instancia: dict) -> str:
    veredicto = decidir(
        REGLAS, PRIORIDADES, "PAGAR", "ESCALAR", instancia, FUENTES, [], sandbox.ejecutar
    )
    return veredicto.decision


def test_el_motor_habla_con_el_sandbox_real() -> None:
    limpia = {"nif": "B96233419", "iban": "ES2100752345670600123456"}
    otro_iban = {"nif": "B96233419", "iban": "ES3900815290070012345678"}

    assert decidir_con_sandbox(limpia) == "PAGAR"
    assert decidir_con_sandbox(otro_iban) == "ESCALAR"


def test_un_codigo_que_el_sandbox_rechaza_escala() -> None:
    """A rule the sandbox refuses to run is a rule the engine cannot decide without."""
    malicioso = [Regla(id=1, texto="lee el disco", decision="ESCALAR", codigo_a="import os")]

    veredicto = decidir(
        malicioso, PRIORIDADES, "PAGAR", "ESCALAR", {"nif": "x"}, FUENTES, [], sandbox.ejecutar
    )

    assert veredicto.decision == "ESCALAR"
    assert "ERROR_REGLA 1" in veredicto.motivo

from decimal import Decimal, ROUND_HALF_UP
from datetime import date


def texto(valor):
    """Anything a source or an extractor gives us, as a comparable string."""
    return "" if valor is None else str(valor).strip()


def vacio(valor):
    return texto(valor) == ""


def clave(valor):
    """NIF, IBAN and order references all compare uppercase without separators."""
    return texto(valor).upper().replace(" ", "").replace("-", "").replace(".", "")


def iban(valor):
    return texto(valor).upper().replace(" ", "")


def centimos(valor):
    return int((Decimal(str(valor)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def coincide(uno, otro):
    """The tolerance of the norm: one cent."""
    return abs(centimos(uno) - centimos(otro)) <= 1


def filas(fuentes, nombre):
    return fuentes.get(nombre) or []


def fecha_de(valor):
    """The printed date as a real date, or None if no such day exists."""
    partes = texto(valor).split("-")
    if len(partes) != 3:
        return None
    try:
        return date(int(partes[0]), int(partes[1]), int(partes[2]))
    except ValueError:
        return None


def salta(motivo):
    return {"salta": True, "motivo": motivo}


def pasa():
    return {"salta": False, "motivo": ""}

def evaluar(instancia, fuentes, otras):
    """The invoice pays into the account the master approved."""
    nif = clave(instancia.get("nif_emisor"))
    if not nif or vacio(instancia.get("iban")):
        return pasa()
    suyas = [f for f in filas(fuentes, "proveedores") if clave(f.get("nif")) == nif]
    if not suyas:
        return pasa()
    ids = {texto(f.get("id")) for f in suyas}
    cuentas = {iban(f.get("iban")) for f in suyas}
    if len(ids) > 1 or len(cuentas) > 1:
        return pasa()
    aprobado = cuentas.pop()
    if iban(instancia.get("iban")) != aprobado:
        return salta("IBAN " + iban(instancia.get("iban")) + " no es el del maestro")
    return pasa()

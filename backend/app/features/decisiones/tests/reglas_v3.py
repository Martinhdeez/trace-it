"""The sixteen Norma_Pagos_v3 rules, written by hand.

These are a fixture, not the product. The compiler in `features/agentes` is what turns a
rule's text into code; this module exists so the engine can be exercised on the real data
before any LLM key is available, and so there is something to compare a generated rule
against. Each entry is the code for the rule with the same index in
`procesos/pago-facturas.json`, and obeys that file's conventions.

The code runs in the sandbox, so: only `decimal`, `datetime`, `re`, `math` and
`unicodedata` may be imported, and no name or attribute may start with `_`.
"""

PRELUDIO = '''
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
'''

OBLIGATORIOS = ["nif_emisor", "iban", "pedido", "fecha", "base", "tipo_iva", "cuota_iva", "total"]

R01 = f'''
def evaluar(instancia, fuentes, otras):
    """Every symbol the norm needs was extracted."""
    faltan = [s for s in {OBLIGATORIOS!r} if vacio(instancia.get(s))]
    if faltan:
        return salta("Faltan: " + ", ".join(faltan))
    return pasa()
'''

R02 = '''
def evaluar(instancia, fuentes, otras):
    """The issuer is in the supplier master."""
    nif = clave(instancia.get("nif_emisor"))
    if not nif:
        return pasa()
    for fila in filas(fuentes, "proveedores"):
        if clave(fila.get("nif")) == nif:
            return pasa()
    return salta("NIF " + nif + " no esta en proveedores")
'''

R03 = '''
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
'''

R04 = '''
def evaluar(instancia, fuentes, otras):
    """The master contradicts itself about this supplier."""
    nif = clave(instancia.get("nif_emisor"))
    if not nif:
        return pasa()
    distintas = {
        (texto(f.get("id")), iban(f.get("iban")))
        for f in filas(fuentes, "proveedores")
        if clave(f.get("nif")) == nif
    }
    if len(distintas) > 1:
        return salta("Proveedores discrepa para " + nif)
    return pasa()
'''

R05 = '''
def evaluar(instancia, fuentes, otras):
    """The order exists."""
    pedido = clave(instancia.get("pedido"))
    if not pedido:
        return pasa()
    for fila in filas(fuentes, "pedidos"):
        if clave(fila.get("pedido")) == pedido:
            return pasa()
    return salta("Pedido " + pedido + " no existe")
'''

R06 = '''
def evaluar(instancia, fuentes, otras):
    """The order belongs to the supplier that issued the invoice."""
    nif = clave(instancia.get("nif_emisor"))
    pedido = clave(instancia.get("pedido"))
    if not nif or not pedido:
        return pasa()
    suyo = None
    for fila in filas(fuentes, "pedidos"):
        if clave(fila.get("pedido")) == pedido:
            suyo = fila
    if suyo is None:
        return pasa()
    if not vacio(suyo.get("nif")):
        if clave(suyo.get("nif")) != nif:
            return salta("El pedido es de " + clave(suyo.get("nif")) + ", no de " + nif)
        return pasa()
    proveedor = None
    for fila in filas(fuentes, "proveedores"):
        if clave(fila.get("nif")) == nif:
            proveedor = fila
    if proveedor is None:
        return pasa()
    if texto(suyo.get("proveedor_id")) != texto(proveedor.get("id")):
        return salta("El pedido es del proveedor " + texto(suyo.get("proveedor_id")))
    return pasa()
'''

R07 = '''
def evaluar(instancia, fuentes, otras):
    """The invoice asks for what was ordered."""
    pedido = clave(instancia.get("pedido"))
    if not pedido or vacio(instancia.get("total")):
        return pasa()
    suyo = None
    for fila in filas(fuentes, "pedidos"):
        if clave(fila.get("pedido")) == pedido:
            suyo = fila
    if suyo is None or vacio(suyo.get("importe_total")):
        return pasa()
    if not coincide(instancia.get("total"), suyo.get("importe_total")):
        return salta(
            "Total " + texto(instancia.get("total")) + " != pedido "
            + texto(suyo.get("importe_total"))
        )
    return pasa()
'''

R08 = '''
def evaluar(instancia, fuentes, otras):
    """The VAT on the invoice is the VAT its own numbers imply."""
    if vacio(instancia.get("base")) or vacio(instancia.get("tipo_iva")):
        return pasa()
    if vacio(instancia.get("cuota_iva")):
        return pasa()
    base = Decimal(str(instancia.get("base")))
    tipo = Decimal(str(instancia.get("tipo_iva")))
    esperada = (base * tipo / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if not coincide(instancia.get("cuota_iva"), esperada):
        return salta("Cuota " + texto(instancia.get("cuota_iva")) + " != " + str(esperada))
    return pasa()
'''

R09 = '''
def evaluar(instancia, fuentes, otras):
    """An unusual VAT rate is for a person to confirm."""
    if vacio(instancia.get("tipo_iva")):
        return pasa()
    if centimos(instancia.get("tipo_iva")) != centimos(21):
        return salta("Tipo de IVA " + texto(instancia.get("tipo_iva")))
    return pasa()
'''

R10 = '''
def evaluar(instancia, fuentes, otras):
    """The invoice adds up."""
    for simbolo in ["base", "cuota_iva", "total"]:
        if vacio(instancia.get(simbolo)):
            return pasa()
    suma = Decimal(str(instancia.get("base"))) + Decimal(str(instancia.get("cuota_iva")))
    if not coincide(instancia.get("total"), suma):
        return salta("Total " + texto(instancia.get("total")) + " != base + cuota " + str(suma))
    return pasa()
'''

R11 = '''
def evaluar(instancia, fuentes, otras):
    """The printed date is a day that exists."""
    if vacio(instancia.get("fecha")):
        return pasa()
    if fecha_de(instancia.get("fecha")) is None:
        return salta("Fecha imposible: " + texto(instancia.get("fecha")))
    return pasa()
'''

R12 = '''
def evaluar(instancia, fuentes, otras):
    """The invoice is not dated in the future. The rule never reads the clock: the
    reference day is a row in the `parametros` source."""
    emitida = fecha_de(instancia.get("fecha"))
    if emitida is None:
        return pasa()
    referencia = None
    for fila in filas(fuentes, "parametros"):
        referencia = fecha_de(fila.get("fecha_corte"))
    if referencia is None:
        return pasa()
    if emitida > referencia:
        return salta("Fecha " + texto(instancia.get("fecha")) + " posterior al corte")
    return pasa()
'''

R13 = '''
def evaluar(instancia, fuentes, otras):
    """Accounting knows about this order."""
    pedido = clave(instancia.get("pedido"))
    if not pedido:
        return pasa()
    conocido = False
    for fila in filas(fuentes, "pedidos"):
        if clave(fila.get("pedido")) == pedido:
            conocido = True
    if not conocido:
        return pasa()
    for fila in filas(fuentes, "erp"):
        if clave(fila.get("pedido")) == pedido:
            return pasa()
    return salta("Pedido " + pedido + " no consta en el ERP")
'''

R14 = '''
def evaluar(instancia, fuentes, otras):
    """The workbook and the ERP tell the same story about this order."""
    pedido = clave(instancia.get("pedido"))
    if not pedido:
        return pasa()
    suyo = None
    asiento = None
    for fila in filas(fuentes, "pedidos"):
        if clave(fila.get("pedido")) == pedido:
            suyo = fila
    for fila in filas(fuentes, "erp"):
        if clave(fila.get("pedido")) == pedido:
            asiento = fila
    if suyo is None or asiento is None:
        return pasa()
    difieren = []
    if not vacio(suyo.get("importe_total")) and not vacio(asiento.get("importe")):
        if not coincide(asiento.get("importe"), suyo.get("importe_total")):
            difieren.append("importe")
    if texto(asiento.get("proveedor_id")) != texto(suyo.get("proveedor_id")):
        difieren.append("proveedor_id")
    if not vacio(suyo.get("nif")) and not vacio(asiento.get("nif")):
        if clave(asiento.get("nif")) != clave(suyo.get("nif")):
            difieren.append("nif")
    if difieren:
        return salta("ERP y pedidos difieren en: " + ", ".join(difieren))
    return pasa()
'''

R15 = '''
def evaluar(instancia, fuentes, otras):
    """The order was already paid. Never pay the same order twice."""
    pedido = clave(instancia.get("pedido"))
    if not pedido:
        return pasa()
    asiento = None
    for fila in filas(fuentes, "erp"):
        if clave(fila.get("pedido")) == pedido:
            asiento = fila
    if asiento is None or vacio(asiento.get("estado")):
        return pasa()
    estado = texto(asiento.get("estado")).upper()
    if estado != "PENDIENTE":
        return salta("El ERP dice " + estado)
    return pasa()
'''

R16 = '''
def evaluar(instancia, fuentes, otras):
    """Another invoice in this process claims the same order."""
    pedido = clave(instancia.get("pedido"))
    if not pedido:
        return pasa()
    gemelas = [
        texto(otra.get("_instancia"))
        for otra in otras
        if clave(otra.get("pedido")) == pedido
    ]
    if gemelas:
        return salta("Mismo pedido que: " + ", ".join(sorted(gemelas)))
    return pasa()
'''

# In the order of `procesos/pago-facturas.json`.
REGLAS_V3 = [
    PRELUDIO + cuerpo
    for cuerpo in [R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16]
]

from decimal import Decimal, InvalidOperation


def evaluate(instance, sources, others):
    amount = instance.get("amount")
    if amount is None:
        return {"fires": False, "reason": "Amount is missing"}
    try:
        over_limit = Decimal(str(amount)) > Decimal("500")
    except (InvalidOperation, ValueError):
        return {"fires": False, "reason": "Amount is not a number"}
    return {
        "fires": over_limit,
        "reason": f"The expense report amount is {amount} EUR, above the 500 EUR limit",
    }

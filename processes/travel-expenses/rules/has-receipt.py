def evaluate(instance, sources, others):
    has_receipt = instance.get("has_receipt")
    if has_receipt is None:
        return {"fires": False, "reason": "Receipt status is missing"}
    return {
        "fires": has_receipt is not True,
        "reason": "The expense report has no receipt",
    }

def evaluate(instance, sources, others):
    """The v3 reference amounts are EUR; another currency needs an adopted FX policy."""
    currency = str(instance.get("currency") or "").strip().upper()
    if currency and currency != "EUR":
        return {"fires": True, "reason": "CURRENCY_POLICY_REQUIRED: " + currency}
    return {"fires": False, "reason": ""}

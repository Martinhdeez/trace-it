def text(value):
    return "" if value is None else " ".join(str(value).split()).casefold()


def evaluate(instance, sources, others):
    """Reject a candidate whose full name appears in the criminal-records registry."""
    full_name = text(instance.get("full_name"))
    if not full_name:
        return {"fires": False, "reason": ""}
    for row in sources.get("criminal_records") or []:
        if text(row.get("full_name")) == full_name:
            record_id = str(row.get("record_id") or "unknown").strip()
            return {
                "fires": True,
                "reason": f"CRIMINAL_RECORD_MATCH {record_id}",
            }
    return {"fires": False, "reason": ""}

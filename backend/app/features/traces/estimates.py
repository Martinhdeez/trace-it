"""Read-only reference estimate for unpriced Helmcode usage, never a billing fact.

Demo assumption: value the measured tokens at DeepSeek V4.1 Flash off-peak rates,
verified 2026-09-20 at https://api-docs.deepseek.com/quick_start/pricing/.
This is a common low-cost reference, including for other Helmcode models, not a
claim about Helmcode's bill or model equivalence. Existing cost snapshots win.
"""

from decimal import Decimal


def reference_cost(data: dict) -> float | None:
    if data.get("provider") != "helmcode":
        return None
    values = [data.get("input_tokens"), data.get("output_tokens"), data.get("cached_tokens") or 0]
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in values):
        return None
    incoming, outgoing, cached = values
    if cached > incoming:
        return None
    return float(
        (
            (incoming - cached) * Decimal("0.15")
            + cached * Decimal("0.003")
            + outgoing * Decimal("0.60")
        )
        / 1_000_000
    )

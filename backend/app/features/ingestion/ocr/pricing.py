"""Snapshot public token tariffs at request time; unknown billing stays unknown."""

import os
from decimal import Decimal, InvalidOperation

# Standard paid API rates, USD per million tokens.
# https://ai.google.dev/gemini-api/docs/pricing
# https://typesafe.ai/blog/introducing-system-one-models-and-jev
_PUBLIC_RATES = {
    ("gemini", "gemini-3.1-flash-lite"): ("0.25", "1.50", "0.025"),
    ("jev", "jev-1.13.0"): ("0.042", "0", None),
}


def _rate(name):
    value = os.getenv(name)
    if value is None:
        return None
    try:
        rate = Decimal(value)
    except InvalidOperation:
        return None
    return rate if rate.is_finite() and rate >= 0 else None


def cost_snapshot(provider, model, usage):
    """Return only safe, immutable billing facts for a single network attempt."""
    if provider == "helmcode":
        mode = os.getenv("TRACEPAY_HELMCODE_BILLING_MODE", "unknown").lower()
        if mode == "included":
            return {
                "cost_status": "included",
                "cost_basis": "helmcode_included_marginal_monthly_fee_excluded",
                "cost_usd": 0.0,
            }
        if mode == "metered":
            input_rate = _rate("TRACEPAY_HELMCODE_INPUT_USD_PER_M")
            output_rate = _rate("TRACEPAY_HELMCODE_OUTPUT_USD_PER_M")
            rates = (input_rate, output_rate, None)
            basis = "helmcode_configured_metered"
        else:
            rates = None
            basis = "helmcode_billing_unverified"
    else:
        rates = _PUBLIC_RATES.get((provider, model))
        basis = "public_standard_token_tariff" if rates else "tariff_unavailable"
    if rates is None:
        return {"cost_status": "unknown", "cost_basis": basis}
    input_rate, output_rate, cache_rate = rates
    if input_rate is None or output_rate is None:
        return {"cost_status": "unknown", "cost_basis": "metered_rates_incomplete"}
    input_rate, output_rate = Decimal(input_rate), Decimal(output_rate)
    cache_rate = Decimal(cache_rate) if cache_rate is not None else None
    snapshot = {
        "cost_basis": basis,
        "input_usd_per_m": float(input_rate),
        "output_usd_per_m": float(output_rate),
    }
    if cache_rate is not None:
        snapshot["cache_usd_per_m"] = float(cache_rate)
    input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
    if input_tokens is None or output_tokens is None:
        return {**snapshot, "cost_status": "unknown"}
    cached = usage.get("cached_tokens", 0)
    if cached > input_tokens or (cached and cache_rate is None):
        return {**snapshot, "cost_status": "unknown"}
    # Gemini candidate tokens exclude thoughts. OpenAI completion tokens include reasoning.
    billed_output = output_tokens + (
        usage.get("reasoning_tokens", 0) if provider == "gemini" else 0
    )
    cost = (
        (input_tokens - cached) * input_rate
        + cached * (cache_rate or input_rate)
        + billed_output * output_rate
    ) / 1_000_000
    return {**snapshot, "cost_status": "known", "cost_usd": float(cost)}

"""An instance's symbols: stored with provenance, handed to rule code as plain values.

Stored (`Instance.symbols`): {name: {"value": <json>, "origin": <str>}} (ADR 0008).
Rule contract (`evaluate(instance, sources, others)`): {name: value}. Rule code never sees
`origin`.
"""

from typing import Any


def check_stored(symbols: dict[str, Any]) -> None:
    """Raise ValueError unless every symbol is {"value": ..., "origin": str}."""
    for name, symbol in symbols.items():
        if not (
            isinstance(symbol, dict)
            and symbol.keys() == {"value", "origin"}
            and isinstance(symbol["origin"], str)
        ):
            raise ValueError(
                f'Symbol {name!r} must be stored as {{"value": ..., "origin": "..."}}, '
                f"got {symbol!r}"
            )


def flatten_symbols(symbols: dict[str, Any]) -> dict[str, Any]:
    """Stored symbols to what rule code reads: {name: value}."""
    return {name: symbol["value"] for name, symbol in symbols.items()}

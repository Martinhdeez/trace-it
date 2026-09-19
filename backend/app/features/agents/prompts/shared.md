The rule is evaluated by a Python function
`evaluate(instance, sources, others) -> {"fires": bool, "reason": str}`:
- `instance`: {symbol: value} of the instance being evaluated.
- `sources`: {source_name: [row, ...]}, each row a dict {column: value}.
- `others`: the other instances of the process, each {symbol: value} plus "_instance" (its name). Relevant only if the rule talks about other instances (duplicates, totals...).
- Rule type: `requirement` = something that must hold; it fires when it does NOT hold. `prohibition` = something that must not happen; it fires when it DOES happen.
- A value the rule needs may be missing or None. If the rule text or the use case description says what to do then, that is what happens. Otherwise the function raises, and the engine sends the instance to a person: it never guesses.

Use case description: conventions that apply to every rule of the use case (normalisation, units, tolerances...). Apply them before your own assumptions. If they contradict the rule's text, the rule's text wins.

If the rule needs data that is neither a symbol nor a source column, answer with NeedsData (what is missing and why) instead of inventing a field.

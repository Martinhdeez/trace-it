"""The seventeen Norma_Pagos_v3 rules as the process pack ships them.

The code is not written here: it is read from `processes/rules-v3/`, the same files the
loader installs, so what these tests exercise is exactly what runs. They are hand-written
because the process has to run before any model is configured; the compiler in
`features/agents` is what writes them from the rule text once it can, and this is what its
output can be compared against.
"""

from tests.support import pack

RULES_V3 = pack.codes()

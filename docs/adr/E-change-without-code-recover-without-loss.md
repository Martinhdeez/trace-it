---
status: accepted
---

# E. Change without code, recover without loss

**Problem.** The norm and the data change live, the ERP fails on purpose, and LLM providers
go down.

**Decision.** A norm change is configuration: new text, recompiled rules and a new immutable
process version that the manager publishes whole or not at all. History is append-only: a
change is replayed on past decisions as alerts, never as edits. A failure falls back to the
next model or the last good snapshot.

| Option | Why not / trade-off |
|---|---|
| A code change per norm version | The team is needed for every change |
| Activate each rule as soon as it compiles | A failed compile leaves the norm half-applied |
| Rewrite past decisions after a change | We lose what was decided and why |
| **Configuration, atomic versions, append-only history, fallbacks (chosen)** | History grows without limit; the manager must publish and act on alerts |

**Why (measured, `docs/resilience.md`).**
- Every LLM down: 500 invoices uploaded, decided and exported, golden 471/471, 0 tokens.
  The primary model down: `glm5.3` answered.
- A new rule whose compile failed stayed a `draft` that cannot be published: 500 decisions
  unchanged. Recompiled and published: 38 stale-decision alerts in 1.1 s.
- `kill -9` after 68 of 500 uploads: the rerun ended with 500 instances, no duplicates. A
  restored backup matches the md5 of all 503 decisions.
- ERP down: the sync gave up after 11 s and the previous snapshot stayed current.

**Cost.** A new norm waits for a manager's publication, and ERP data can be minutes old.

```mermaid
flowchart LR
  NV["Norm v4 text"] --> CMP["Compile<br/>model fallback chain"]
  CMP -- "all models fail" --> DR["Rule stays draft<br/>cannot be published"]
  DR --> OLDV["Published version<br/>keeps deciding"]
  CMP -- ok --> PV["Manager publishes<br/>new immutable version"]
  ERP["ERP sync<br/>retries, backoff"] -- fails --> OLD["Keep last snapshot"]
  ERP -- "rows changed" --> DRY["Dry-run replay<br/>on past decisions"]
  PV --> DRY
  DRY --> AL["Alerts to the manager<br/>before and after"]
  AL --> MG["Manager acts;<br/>a new row, never an edit"]
  classDef ke fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#111
  class OLDV,PV,OLD,DRY,AL ke
```

Detail: [0007](detail/0007-declarative-process-packs.md),
[0008](detail/0008-immutable-history-and-retroactive-audit.md),
[0011](detail/0011-configuration-layers.md),
[0013](detail/0013-fault-tolerant-erp-client.md),
[0015](detail/0015-immutable-process-versions.md),
[0019](detail/0019-llm-fallback-chain.md),
[0022 versions](detail/0022-publish-approved-process-versions.md),
[0023](detail/0023-fal-visual-fallback-evaluation.md),
[0024](detail/0024-discover-processes-through-documents-and-conversation.md),
[0026](detail/0026-stale-decision-alerts.md);
[resilience.md](../resilience.md).

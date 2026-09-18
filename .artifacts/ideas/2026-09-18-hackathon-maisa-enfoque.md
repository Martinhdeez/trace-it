# Pass the technical filter of the Maisa hackathon and stand out with an operational-memory approach

**Date:** 2026-09-18 · **Status:** idea, no commitment

## Framing
Surface problem: decide PAGAR / NO PAGAR / ESCALAR for 500 + 40 invoices.
Real problem (user's reframe): a company hires an intern who spends weeks understanding a messy process, and the knowledge leaves with them. The product is an executable operational memory: a system that works from day one and accumulates knowledge (rules with provenance, system quirks, decision history) as a side effect of being used.

Two stages to win:
1. Technical filter: correct outcomes (binary per file) + rubric (ADRs 35, scalability/cost 25, traceability 20, resilience 10, execution 10).
2. Surprise: the innovative angle, shown in the 10-minute defense.

Note: Maisa sells "digital workers" for agentic process automation. The thesis speaks their language; the risk is that it looks like a copy of their product. Position it as "how the knowledge a digital worker needs gets captured".

## Options generated
1. Operational memory: knowledge base built from traces, with rules carrying provenance.
2. Autonomy levels per rule (L0 suggest, L1 decide with review, L2 autonomous), earned with measured precision.
3. Onboarding exam generated from real past cases; measures when the new intern is ready.
4. "Ask Alberto": question answering over knowledge + traces, always citing evidence.
5. Rule-change simulator: paste the new norm, preview the decision diff before applying.
6. Self-written ADRs: the system records design and rule decisions itself; albertitos_plan.pdf is partly compiled from it.
7. Time machine: reconstruct which rules / ERP version were active on any date, and why decision X was taken then.
8. Knowledge exported as an installable package (agent skill / MCP server) for the next intern's assistant.
9. Too expensive: digital employee that learns the process by watching screen recordings, emails and chats of Alberto.
10. Embarrassingly cheap: one CUADERNO.md auto-appended on every run, plus git log.
11. Process mining: auto-generated diagram of how invoices really flow, with bottlenecks and cost per path.
12. Voice capture: the intern dictates the reason while resolving an escalation; it becomes a structured rule.
13. Contradiction detector: a new rule that conflicts with existing rules or past decisions gets flagged.
14. Confidence-driven escalation: low extraction confidence escalates instead of guessing.

## Recommended (provisional)
Core: 1 + 5 + 13 + 14, with 4 as the interface. Demo story: a new person joins, norm v4 arrives, they paste it, see the impact diff and conflicts, approve, and ask "why was invoice X escalated?". Everything shown comes from our own real usage during the hackathon.
Runner-up: 8 (knowledge as an installable agent package).
Flip fact: whether norm v4 arrives as natural-language text (favors 5 + 13) or as data/ERP changes only (favors 7 + 11).

## Considered
- **2 autonomy levels** — strong idea, but needs human-review volume we will not have in 38 h; mention it as roadmap in an ADR.
- **3 onboarding exam** — nice, but secondary to the working system; can be the "measure onboarding" evidence instead.
- **6 self-written ADRs** — good dogfooding detail, low cost; keep as a small touch, not a pillar.
- **7 time machine** — falls out of versioned rules + traces for free; do not build separately.
- **9 screen-watching digital worker** — too expensive and unverifiable in a weekend.
- **10 CUADERNO.md** — too weak as the pitch, but a good fallback if time runs out.
- **11 process mining** — impressive visual, low decision value for Alberto.
- **12 voice capture** — flashy, adds a dependency; only if trivial with existing Whisper setup.

## Update after first answers
- Filter is binary on the full set: one wrong outcome in 540 files = disqualified. Accuracy dominates everything.
- ESCALAR is a label in the reference solution, defined by business rules. Our own uncertainty must NOT map to ESCALAR; it maps to internal review (second extractor, then human) until the correct label is known. Option 14 changes accordingly.
- Maisa's own pitch: "user traces compound into proprietary IP" and "onboard digital workers in natural language". The operational-memory thesis matches their vision; use their vocabulary (traces, digital worker, deterministic control).
- Team: 3 back/data (user also drives filter + product), 1 product (winning ideas after filter), 1 frontend. ~36 h, AI-assisted.
- Cost is a plus, not a limit: add saving mechanisms (cache, tiered models) without risking accuracy.

## Open questions
- Team size, skills, hours available, who defends.
- LLM budget / API keys; is using the Maisa platform expected or rewarded?
- Is there an explicit pre-selection before defenses, and on what (accuracy, rubric, PDF)?
- Format of batch 2 changes (norm text vs data).

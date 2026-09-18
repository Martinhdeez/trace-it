# [Medical Agent Delegation](https://pydantic.dev/docs/ai/examples/complex-workflows/medical-agent-delegation/)

# Medical Agent Delegation

Medical triage and delegation system built with **Pydantic AI**, demonstrating how an orchestrator agent (`triage_agent`) coordinates multiple specialized agents (e.g. cardiology, neurology, and senior clinician).

Demonstrates:

-   [Agent delegation and coordination](https://pydantic.dev/docs/ai/guides/multi-agent-applications/#agent-delegation)
-   [structured `output_type`](https://pydantic.dev/docs/ai/core-concepts/output/#structured-output)
-   [tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/)

* * *

This example shows how to use **multiple Pydantic AI agents** to simulate a medical triage workflow.

The system includes:

-   **General Practitioner, Cardiology, and Neurology agents** -- for Level 1 consultation.
-   **Senior Doctor agent** -- for escalations and treatment planning.
-   **Triage Agent (Coordinator)** -- which decides which tool to invoke and when to escalate.

The `triage_agent` uses two tools:

1.  `consult_specialist` -- routes the complaint to a domain specialist.
2.  `consult_senior_doctor` -- escalates the case for critical or ambiguous scenarios.

Each specialist produces a structured `MedicalReport`, and the senior doctor produces a structured `TreatmentPlan`. The orchestrator then compiles both into a final `TriageFinalOutput`.

* * *

## Running the Example

With [dependencies installed and environment variables set](https://pydantic.dev/docs/ai/examples/setup/#usage), run:

Terminal

```bash
python -m pydantic_ai_examples.medical_agent_delegation
```

---

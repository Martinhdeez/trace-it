# Pydantic AI — mapa de lectura

Regla: **abre solo la sección que necesitas**. `llms-full.txt` son 5,5 MB, no lo leas entero.
Índice completo en `SECTIONS.md`.

## Los 6 conceptos que hay que conocer

| Concepto | Para qué | Sección |
|---|---|---|
| `Agent(model, deps_type=, output_type=, instructions=)` | El objeto central | `sections/agents.md` |
| `@agent.tool` + `RunContext[Deps]` | Tools con inyección de dependencias (como `Depends` de FastAPI) | `sections/function-tools.md`, `sections/dependencies.md` |
| `output_type=` | Salida tipada con Pydantic. Sin esto no hay trato | `sections/output.md` |
| `ModelRetry` | Si la validación falla, reintenta solo | `sections/output.md` |
| **deferred tools / `requires_approval`** | **Gate de aprobación humana. Lo más importante del proyecto** | `sections/deferred-tools.md`, `sections/handle-deferred-tool-calls.md` |
| `message_history` | Serializar, guardar en Postgres, reanudar | `sections/messages-and-chat-history.md` |

## Observabilidad
- `sections/logfire-integration.md`, `sections/instrumentation.md`
- Una línea: `logfire.instrument_pydantic_ai()` → trazas por paso con tokens y coste

## Evals (el diferenciador ante el jurado)
- `sections/pydantic-evals.md` — `Dataset`, `Case`, `dataset.evaluate()`
- `sections/evaluators-overview.md`, `sections/custom-evaluators.md`
- `sections/pydantic-evals-reporting.md` — la tabla de reporte que se proyecta en la demo

## Streaming hacia el front
- `sections/agents.md` (`agent.iter()`, `run_stream()`)

## No mirar en el hackathon
`pydantic_graph`, multi-agente, durable execution con Temporal/DBOS/Prefect, AG-UI, ACP.
Son madrigueras. El proyecto no los necesita.

## Prueba que mata el riesgo técnico (hacer antes del viernes)
Un `Agent` con una tool `requires_approval=True` que:
1. se para pidiendo aprobación
2. persistes el estado en Postgres
3. **matas el proceso**
4. lo levantas y reanudas con `DeferredToolResults`

Si eso corre, el resto es dominio.

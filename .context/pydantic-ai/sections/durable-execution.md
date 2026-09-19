# [Durable Execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

# Durable Execution

Capability authors can also move custom hook work into engine activities, steps, or tasks with [durable capability operations](https://pydantic.dev/docs/ai/capabilities/custom/#durable-capability-operations).

Third-party runtime authors can use the stable [durable execution backend builder](https://pydantic.dev/docs/ai/capabilities/durable_execution/backends/) to integrate another engine without importing Pydantic AI internals.

Pydantic AI allows you to build durable agents that can preserve their progress across transient API failures and application errors or restarts, and handle long-running, asynchronous, and human-in-the-loop workflows with production-grade reliability. Durable agents have full support for [streaming](https://pydantic.dev/docs/ai/core-concepts/agent/#streaming-all-events) and [MCP](https://pydantic.dev/docs/ai/mcp/client/), with the added benefit of fault tolerance.

Pydantic AI officially supports five durable execution solutions, co-maintained by the Pydantic and vendor teams:

-   [Temporal](https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/)
-   [DBOS](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/)
-   [Prefect](https://pydantic.dev/docs/ai/capabilities/durable_execution/prefect/)
-   [Restate](https://pydantic.dev/docs/ai/capabilities/durable_execution/restate/)
-   [AWS Lambda durable functions](https://pydantic.dev/docs/ai/harness/aws-lambda/)

Additional external SDK integrations:

-   [Kitaru](https://pydantic.dev/docs/ai/capabilities/durable_execution/kitaru/)
-   [Apache Airflow](https://pydantic.dev/docs/ai/capabilities/durable_execution/airflow/)

---

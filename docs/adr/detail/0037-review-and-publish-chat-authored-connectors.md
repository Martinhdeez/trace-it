---
status: accepted
---

# Review and publish chat-authored connectors

## Context

Process discovery can already map uploaded tables and configured ERP snapshots, but a new
process cannot retain a new live connection. Connector lookup still depends on a repository
pack. That makes an engineer part of every otherwise conversational process setup.

The existing HTTP connector already supports the legacy format needed here: XML, optional
form-token authentication, numbered pages, field mapping, retries and complete snapshot
validation.

## Decision

- Add a typed connector proposal to the process draft. It includes the HTTP configuration,
  canonical required and optional fields, and whether the source syncs before each run.
- Store environment-variable names, never credential values, in a proposal.
- Require explicit manager acceptance before a draft can contact a proposed endpoint.
- Load a complete draft snapshot before rules may rely on the source. The agent can inspect
  that snapshot through the existing read-only search tool.
- Publish accepted connector configuration and its source schema inside the immutable process
  version. Runtime sync reads the published version first and keeps process packs as the
  compatibility path for older processes.
- Keep other authentication, body and pagination formats out of scope until a real second
  protocol requires another adapter.

## Consequences

The discovery conversation can set up a new compatible ERP without a code or pack change.
Connector configuration, source mapping and rules use one review and publication flow. A bad
proposal cannot contact the endpoint before review and cannot affect a live process before
publication. Operators must still provision the named credential environment variables.

This decision supersedes ADR 0036 only where it left connector generation outside discovery.
It preserves ADR 0036's reviewed-draft contract.

## Related

ADR 0011, 0013, 0024, 0028, 0031 and 0036.

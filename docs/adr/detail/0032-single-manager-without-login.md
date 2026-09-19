---
status: accepted
---

# Run the console as the pack's manager, with no login screen

## Context
The console is used by one person: the manager, who runs cases, resolves escalations and
publishes process versions (ADR 0031). Every write must still keep its author, because the
audit trail and the append-only history (ADR 0008) name who resolved or published what. The
integration first shipped a login screen (#97). In practice it added a step to every demo and
protected nothing: the API identifies the caller by the `X-User-Id` header, with no password
or token. The app runs locally or behind a private deployment for the hackathon.

## Alternatives considered
- **Real authentication (password, OIDC).**
  - Pros: actual security; ready for several users.
  - Cons: a user store, sessions and secrets for a single-user demo; no rubric point asks for it.
- **A login screen over the header identity (#97).**
  - Pros: shows who is acting.
  - Cons: looks like security but is not; one more step on stage.
- **No identity at all.**
  - Pros: simplest.
  - Cons: resolutions, publications and acknowledgements lose their author.
- **Auto-identify as the pack's manager; keep `X-User-Id` for authorship (chosen).**
  - Pros: no extra step; every write still records its author; the backend still refuses
    writes from a non-manager.
  - Cons: anyone who reaches the API can claim any user id.

## Decision
- The console signs in on its own as the pack's manager (`VITE_DEFAULT_USER_EMAIL`, default
  `martin@trace-it.local`) through `POST /login`, and sends that id as `X-User-Id` on every
  request. `/login` in the browser redirects to the process list.
- Writes (run, sync, configure, publish, resolve, accept proposals, acknowledge alerts) need
  the `manager` role (`users/dependencies.py`, `manager_user`). The `operator` role remains
  in the data model for reads; the console has one role in practice.
- Ajustes can act as another user of the process, for a demo of the permission check.

## Consequences
- No security boundary. This is marked in the code (`ponytail:` note in
  `users/dependencies.py`): real authentication is needed before the app leaves the
  hackathon. Every endpoint already goes through that one dependency, so adding it is one
  change.
- Authorship is intact: decision rows, spans and proposals carry the manager's name.

## Evidence
- `frontend/src/state/session.tsx` (automatic identity), `frontend/src/api/http.ts`
  (`X-User-Id` on every request), `frontend/src/App.tsx` (`/login` redirect).
- `backend/app/features/users/dependencies.py` (`current_user`, `manager_user`).
- Tests: `tests/e2e/test_frontend_contract.py::test_live_client_identity_header_matches_backend`,
  `processes/tests/test_drafts.py::test_operator_cannot_create_or_review_drafts`,
  `versions/tests/test_api.py::test_invalid_rules_and_manager_gate`.
- Pull requests: #97 (login screen), #113 (removed it), #92 and #120 (manager-only writes).

## Related
ADR 0008, 0026, 0031, 0033.

# trace-it frontend

The manager's console. Vite + React + Tailwind, talking to the FastAPI backend.

```bash
cd frontend
npm install
npm run dev
```

Opens on http://127.0.0.1:5173. `/api` proxies to `http://127.0.0.1:8000`, where
`make setup` serves the backend at the root. For an API on another port, set
`VITE_API_TARGET` in the shell or in `frontend/.env.local`:

```bash
VITE_API_TARGET=http://127.0.0.1:8001 npm run dev
```

There is no mock: the console only shows backend data, and its errors surface as they
are ("El backend no responde" when it is down).

## Identity

There is no login screen: the console is local. On start it calls `POST /login` with
`VITE_DEFAULT_USER_EMAIL` (default `martin@trace-it.local`, the pack's manager) and sends
that id as `X-User-Id` on every request, so each action keeps its author in the trace.
A 401 or 403 asks for the identity again and the screen shows the backend's message.
Ajustes can switch to another user of the process.

## Typed API

`src/api/schema.d.ts` holds the backend's types, generated from `openapi.json`. After a
backend route or schema changes, run `make openapi` from the repo root: it dumps
`openapi.json` from the FastAPI app (no server needed) and then runs `npm run gen:api`.
Commit both files. A backend test fails while they are out of date.

## Layout

| Folder | Holds |
|---|---|
| `src/api/` | `contracts.ts` aliases the generated `schema.d.ts`; `live.ts` calls the API; `client.ts` exports it as `api` |
| `src/routes/` | One file per screen, mounted in `App.tsx` |
| `src/components/shell/` | Chrome: sidebar, topbar, command palette, buttons, tables |
| `src/components/run/` | The three panes of the instance console |
| `src/lib/` | Paths, formatting, derived counts |

Code, file names, identifiers and API codes are English. Only the strings a user reads
are Spanish, and they live in `src/i18n/es.ts`.

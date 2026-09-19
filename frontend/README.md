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

`VITE_API_MODE` picks the client in `src/api/client.ts`:

| Value | What happens |
|---|---|
| unset (default) | Only the backend. Errors surface as they are ("El backend no responde" when it is down) |
| `mock` | Only the in-memory mock, with the Caja lote 1 loaded. No backend needed. A "MOCK DATA" badge stays on screen |

## Typed API

`src/api/schema.d.ts` holds the backend's types, generated from `openapi.json`. After a
backend route or schema changes, run `make openapi` from the repo root: it dumps
`openapi.json` from the FastAPI app (no server needed) and then runs `npm run gen:api`.
Commit both files. A backend test fails while they are out of date.

## Layout

| Folder | Holds |
|---|---|
| `src/api/` | `contracts.ts` mirrors the backend schemas; `live.ts` and `mock.ts` implement them; `client.ts` picks one |
| `src/routes/` | One file per screen, mounted in `App.tsx` |
| `src/components/shell/` | Chrome: sidebar, topbar, command palette, buttons, tables |
| `src/components/run/` | The three panes of the instance console |
| `src/lib/` | Paths, formatting, derived counts |

Code, file names and identifiers are English. Payload keys keep the Spanish the API
sends (`nombre`, `tipos_decision`, `requiere_persona`), and so do the strings a user
reads, which live in `src/i18n/es.ts`.

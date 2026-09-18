# trace-it frontend

The manager's console. Vite + React + Tailwind, talking to the FastAPI backend.

```bash
cd frontend
npm install
npm run dev
```

Opens on http://127.0.0.1:5173. `/api` proxies to `http://127.0.0.1:8000`, where the
backend serves at the root.

`VITE_API_MODE` picks the client in `src/api/client.ts`:

| Value | What happens |
|---|---|
| `auto` (default) | Every call tries the backend and falls back to the in-memory mock when the endpoint answers 501, 502, is not mounted, or the backend is down |
| `live` | Only the backend. Errors surface as they are |
| `mock` | Only the mock, with the Caja lote 1 loaded. No backend needed |

Settings shows, per API method, which of the two answered.

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

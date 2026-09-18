# Miralmar console

Operator console for Trace Pay. Vite + React, talks to FastAPI later, mock client now.

```bash
cd web
npm install
npm run dev
```

Opens on http://127.0.0.1:5173. `/api` proxies to `http://127.0.0.1:8000` when the backend exists. Set `VITE_API_MODE=live` once `src/api/client.ts` points at the real client.

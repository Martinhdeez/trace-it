# Prueba en vivo — trace-it (dev @ 7f540ca)

## URLs
| Qué | URL |
|---|---|
| Dashboard | http://localhost:8020 (arranca vacío: pulsa **New demo run**) |
| API demo (OpenAPI) | http://localhost:8010/docs |
| ERP de Alberto | http://localhost:8009 |

BD `trace_demo` recién creada: proceso 1 = pack (`Invoice payment`), proceso 2 = `dry-run` (mi ensayo, ya decidido). Configs de agentes v1 activas: deepseek-v4-flash con reservas glm5.3/qwen3.6, `max_tokens`, normalizer `failed_check_decision: NO_PAGAR`, `auto_activate_max_change: 1.0`, assistant con modelo.

Logs en vivo: `tail -f demo-logs/api.log`

## Arrancar / parar (desde la raíz del repo)
```sh
# API :8010
cd backend && (set -a; . ../.env; set +a; TRACE_DATABASE_URL=postgresql+psycopg://trace:trace@localhost:5432/trace_demo PYDANTIC_AI_NO_BANNER=1 nohup uv run uvicorn app.main:app --port 8010 > ../demo-logs/api.log 2>&1 &); cd ..
# Forzar relectura de todos los PDFs y llamadas reales a Gemini/Jev (ignora cachés y journal):
# añade TRACEPAY_OCR_FORCE_RECOMPUTE=1 antes de TRACE_DATABASE_URL en la línea anterior
# Dashboard :8020
sh demo-logs/dashboard/run.sh
# ERP :8009 (si no responde)
cd .context/500-sombras-de-alberto && nohup python3 alberto_erp.py > ../../demo-logs/erp.log 2>&1 & cd -
# Parar
for p in 8010 8020 8009; do lsof -ti :$p -sTCP:LISTEN | xargs kill; done
```

## Pasos (botón **Next** en la cabecera; tiempos medidos en el ensayo)
| # | Paso | Qué ves | Tiempo |
|---|---|---|---|
| 1 | New demo run | Proceso nuevo "Prueba en vivo HH:MM:SS", sin reglas | <1 s |
| 2 | Ingest (API) | Excel (suppliers 12, orders 516, parameters 1) y luego los 500 PDFs uno a uno por `POST /processes/{id}/files` (la API real de Álvaro). La columna 1 se llena en vivo: `text · 9 sym` o `no text · 0 sym` | ~20 s |
| 3 | ERP sync | `POST /processes/{id}/sources/erp/sync`: 516 filas, 26 páginas, 1 login, ~3 reintentos `ORA-00600` superados solos | ~5,5 s |
| 4 | Post norm | Las 6 frases de `Norma_Pagos_v3` al normalizador; spinner en la columna 2 | ~54 s |
| 5 | Compile (auto) | 11 tarjetas en "compiling" con spinner; cada una muestra tester y coder con segundos y tokens al terminar, luego ACTIVE (auto-activación) | ~66 s (reglas p50 30 s) |
| 6 | Run engine | 500 decisiones en <1 s (~670 facturas/s). Mientras haya reglas compilando, Run está deshabilitado (la API da 409) | 0,8 s |
| 7 | Export + golden | Recuento y comparación: **471/471**, 0 fallos | <1 s |

Norma enviada → todo activo: **~2 min**. Todo el flujo: **~2,5 min**.

Resultado del ensayo: PAGAR 433 · NO_PAGAR 36 · ESCALAR 31 (29 escaneos `MISSING_DATA` + 2 pedido duplicado PO-2026-0492, `doubt` → ESCALAR).

## Qué mirar en las trazas
- **Clic en una regla** (columna 3 o dentro de una factura): texto, frase de la norma, interpretación, **kind** (violation/doubt) y por qué, **decision source** (policy/explicit) y cita, activación automática, árbol de spans (normalizer → tester → coder attempts → run_tests → impact_check → activate), código, tests con entradas, y el **contexto exacto** de cada llamada al LLM (instrucciones, mensaje, respuesta, tokens). Buena para enseñar: la regla de pedido duplicado (kind doubt).
- **Clic en un cuadrado** del motor o en un PDF de la columna 1: `/instances/{id}/trace` — fichero (hash, bytes), símbolos con su origen (`document:<id extracción>`), decisiones con las reglas que dispararon y su motivo, y spans `upload_document → extraction → native_text → ingest_document → run_process → evaluate_rule ×11 → decision → export_outcomes`. Enlace "open PDF".
- **Resolve**: en una factura ESCALAR aparece el formulario; elige PAGAR/NO_PAGAR, escribe motivo, "Resolve as Martín". Se añade una decisión de persona y un span `resolution`; la del motor se conserva.
- Tira de métricas arriba (`/processes/{id}/metrics`): llamadas y tokens por rol, p50/p95 por paso, escaladas por motivo.

## Limitaciones conocidas
- **Escaneos (29) sin OCR**: los modelos ONNX no están descargados en local (`uv run python -m app.features.ingestion.tools.download_models`), así que el lector da `OCR_ERROR ProviderUnavailable`, quedan sin símbolos y van a ESCALAR `MISSING_DATA`. El golden los deja sin esperado, por eso la cuenta es sobre 471.
- **Resolver no cambia el export**: por ADR 0016 se exporta la última decisión del motor; la de la persona solo si el motor nunca decidió. En el panel verás "export writes ESCALAR" aunque la hayas resuelto.
- El motivo de pedido duplicado es el texto que devuelve la regla (`Same order as: factura_41082.pdf`), no un código fijo.
- El normalizador puede variar entre ejecuciones (p. ej. una regla más o menos, o un reintento del coder); en el ensayo: 11 reglas, 12 llamadas al coder (1 reintento).
- "LLM caído" no está en el dashboard: requiere reiniciar la API con otra URL. Aparte: `make demo-llm-down`.
- El modelo aparece como `deepseek/deepseek-v4.1-flash`: es el alias que devuelve Helmcode para `deepseek-v4-flash`.
- El estado de la ingesta (contador x/500) vive en memoria del dashboard: si lo reinicias a mitad, la lista de PDFs sigue saliendo de la BD pero sin contador.

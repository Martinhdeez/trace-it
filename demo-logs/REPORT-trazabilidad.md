# Trazabilidad de trace-it, módulo a módulo (dev @ af23867, PR #49)

**Datos:** ejecución de verificación del 19-sep, 09:24–09:30 (BD `trace_coverage`: 315 spans, 59 trazas, procesos 1 y 2), con modelos reales (`deepseek/deepseek-v4.1-flash`). Escala: BD `trace_demo` (5.827 spans, 500 facturas). Ficheros en bruto: `demo-logs/coverage/`.

## 1. Resumen
Cada paso del sistema deja un span: quién lo hizo, qué entró, qué salió, cuánto tardó, cuántos tokens gastó y si falló. Los spans se guardan en nuestra propia tabla `events` de Postgres. Esa tabla es la auditoría y se cruza con decisiones, reglas y facturas. Cada span se replica además a OpenTelemetry (SDK de Logfire → Logfire cloud o un Phoenix local por OTLP; sin token no sale nada de la máquina). Un fallo es un span `error` con su mensaje, así que también queda registrado. Diseño: ADR 0018. API de spans: `backend/app/core/events.py`. Lectura: `backend/app/features/traces/`. **Ningún paso queda sin span**, salvo los huecos de la sección 7.

## 2. Cobertura por módulo
| Módulo | Spans | Campos clave | Dónde verlo | Tests (origin/dev) / en vivo |
|---|---|---|---|---|
| users | ninguno propio | la identidad llega en `X-User-Id` y se guarda como `author` en los spans de cambio (`optional_user`) | — | en vivo: `author` = Martín / Mateo / `cli` / `auto` / `pack` |
| processes / use cases | `load_use_case`, `load_definition`, `configure_agent`, `activate_agent_config` (un 409 da span `error`) | `author`, `role`, `use_case_id`, `before_version`/`after_version`, config completa, `note`; definición: 12 símbolos, 16 reglas, 5 usuarios | `/processes/{id}/events` (incluye la config de su use case) | `test_agent_config_changes_are_in_the_process_feed_with_their_author` · en vivo: v1→v2→v1 |
| ingestion | `upload_document` > `store_file`, `extraction` > (`native_text`, `ocr`, `vision`, `text_judge`, `focused_read`), `ingest_document`; `upload_workbook` > `extraction`, `load_workbook`; `reextract_document`; `demo_ingest` | fichero, `sha256`, bytes, `reader`, página, líneas, `ocr_calls`/`vlm_calls`, `cache_hit`, avisos, símbolos con su `origin` | `/instances/{id}/trace` | `test_an_ocr_failure_is_an_error_span_and_a_warning`, `test_process_api` (subida y reextracción, una traza cada una) · en vivo: subida, OCR ×4, workbook y `demo_ingest`; 60 `ocr` en `error` en `trace_demo` (modelos OCR ausentes). **No verificado en vivo:** `vision`, `text_judge`, `focused_read`, `reextract_document` |
| sources / ERP | `sync_source` | filas, páginas, logins, peticiones, reintentos, 429, `transient_errors`, diff (añadidas/cambiadas/borradas), `rows_hash`, `origin`, error | `/traces?name=sync_source` | en vivo: sync correcta y sync con el ERP caído (`error`, HTTP 502) |
| agents | `llm_run` bajo `normalize_norm` (normalizer), `compile_rule` (tester), `coder_attempt` (compiler), la revisión (reviewer, con la config del tester) y `suggest_escalation` (assistant) | `model`, `chain`, `config_id`, `prompt_hash`, `instructions`, `user_prompt`, `output`, `retry_prompts`, tokens de entrada y salida, `retries`, `requests`, `failed_attempts` | `/rules/{id}/trace`, `/traces/{trace_id}` | `test_llm.py` (fallback por 503 y por límite de tokens, dos modelos caídos), `test_a_disputed_test_is_corrected_by_the_tester` · en vivo: normalizer, tester, compiler y assistant; un `llm_run` en `error` con un 401 real (`trace_obs_demo`). **No verificado en vivo:** reviewer (0 disputas) y fallback (`failed_attempts` vacío en las 76 llamadas de `trace_coverage` y `trace_demo`) |
| rules | `save_rule`, `norm`, `compile_rules` > `compile_rule` > (`llm_run`, `coder_attempt` > `run_tests`, `impact_check`, `activate_rule`); `impact_check` con `preview` (GET impact); `retire_rule` | `author` (persona, `cli` o `auto`), `before`/`after`, `rule_hash`, `findings`, `valid`, casos aprobados, cambios sobre decisiones pasadas | `/rules/{id}/trace` (`lifecycle`, `compilations`, runtime) | `test_rule_status_changes_carry_author_and_show_in_the_rule_trace`, `test_a_rule_saved_by_a_person_names_them_and_a_failed_compile_is_an_error` · en vivo: 12 compiladas y activadas por `auto`, 16 activadas por `cli`, 1 retirada por Martín. **No verificado en vivo:** `save_rule` |
| decisions | `run_process` (un 409 da span `error`) > `evaluate_rule` por regla + punto `decision` por factura; `reprocess` (con `dry_run`); `resolution` | instancias, disparos, errores, `by_decision`, `failures` (MISSING_DATA…), `rules_hash`, motivo; resolución: autor, `before`, `previous_author`, motivo | `/instances/{id}/trace`, `/processes/{id}/events`, `/processes/{id}/metrics` | `test_run_journey_and_metrics`, `test_reprocess_and_a_refused_run_are_spans`, `test_a_sandbox_crash_is_an_error_span_and_the_run_goes_on` · en vivo: todos |
| export | `export_outcomes` | líneas, `batch`, `duplicates` | `/traces?name=export_outcomes` | en vivo: completo (20 líneas) y por lote (5 líneas) |

Los tests se citan por nombre en `origin/dev`. No se han vuelto a ejecutar para este informe porque necesitan escribir en BDs de test.

## 3. Trazas reales
### 3.1 Una factura escaneada, de la subida al export (`/instances/19/trace`)
`copia_2026_0518.pdf`: no tiene capa de texto, así que la lee el OCR. La respuesta junta 6 trazas.

    upload_document 3.501 ms · POST /processes/2/files → 201
    ├ store_file 0 ms
    ├ extraction 3.481 ms · sha256 b7389726… · ocr_calls 2 · vlm_calls 0 · 2 avisos
    │ ├ native_text 1 ms · 1 página, sin texto
    │ ├ ocr primary 2.288 ms · 11 líneas
    │ └ ocr secondary 1.186 ms · 12 líneas
    └ ingest_document · base 760.00 · total 919.60 · IVA 21 % 159.60
                         date, iban, issuer_nif = null · origin document:0ea29…
    run_process 326 ms · 20 facturas · 12 reglas
    ├ evaluate_rule ×12 · 23–27 ms cada una
    └ decision ESCALAR · MISSING_DATA: date, iban, issuer_nif, purchase_order · rules_hash ef8aa3ec…
    suggest_escalation 2.479 ms → ESCALAR
    └ llm_run assistant 2.469 ms · 2.995→353 tok
    resolution · Mateo · ESCALAR → NO_PAGAR · "Checked with the supplier by phone" · previous_author engine
    export_outcomes 5 ms · 20 líneas → {"file_id":"copia_2026_0518.pdf","result":"ESCALAR"}
    export_outcomes 10 ms · 20 líneas

El export da ESCALAR aunque Mateo resolviera NO_PAGAR. Es lo previsto: se exporta la última decisión del motor (ADR 0009). La resolución de la persona queda en la auditoría.

### 3.2 Ciclo de vida de una regla (`/rules/17/trace` y `/rules/16/trace`)
Regla 17 ("el NIF debe estar en el maestro"), salida de `Norma_Pagos_v3`:

    norm 6.522 ms · author Martín
    ├ normalize_norm 6.415 ms · 6 frases → 12 comprobaciones
    │ └ llm_run normalizer 6.225 ms · 3.663→2.204 tok
    └ compile_rules 52.282 ms · 12 reglas en paralelo
      ├ compile_rule #17 17.123 ms · author auto · compiling → active
      │ ├ llm_run tester 12.625 ms · 2.566→2.787 tok · config 2 · prompt 2bd56e0b643f
      │ ├ coder_attempt 1 · 4.443 ms · 0 disputas
      │ │ ├ llm_run compiler 4.413 ms · 6.856→610 tok · config 1 · prompt ee4bf8946e7b
      │ │ └ run_tests 26 ms · 8/8
      │ ├ impact_check 19 ms · 0/0 decisiones cambiadas → auto
      │ └ activate_rule 12 ms · author auto · draft → active · hash 0f3d4ae8…
      └ … 11 compile_rule más (p50 17,2 s · máx 36,7 s)
    impact_check 317 ms · preview · 0 cambios · 1 conflicto   (GET /rules/17/impact)

Retirada (regla 16 del pack; `lifecycle` de `/rules/16/trace`):

    activate_rule 3 ms · author cli · draft → active · hash f46e28cc…
    retire_rule   6 ms · author Martín · active → retired · findings 0 · mismo hash

En vivo no hay una sola regla con guardado, compilación y retirada: la 17 cubre la compilación y la 16 la retirada. La secuencia guardar (autor) → compilar → retirar sobre una misma regla está cubierta solo por tests (`test_coverage.py`).

### 3.3 Cambio de config de un agente y su rollback (use case 1, rol `assistant`)
    configure_agent       9 ms · Martín · v1 → v2 · note "cite rule ids"
                                 config: instructions "Always cite the rule id." · fallback [glm5.3, qwen3.6]
    activate_agent_config 3 ms · Martín · v2 → v1 (config_id 3, la del pack)

Los dos spans salen en el feed de los procesos 1 y 2, porque comparten use case. En tests, activar una config que ya está activa da 409 y un span `error` con autor.

### 3.4 Sync del ERP: correcta y con el ERP caído
    sync_source 4.859 ms · ok · 516 filas · 26 páginas · 30 peticiones · 1 login
                reintentos 2 · ORA-00600 ×2 · diff +516 · rows_hash 216c4e27…
    sync_source 8.366 ms · error · HTTP 502 al cliente
                12 peticiones · 10 reintentos · ConnectError ×12 · 0 páginas
                "Sync of 'erp' failed; the previous snapshot stays current.
                 POST /erp/login : gave up after 6 attempts"

La foto anterior de la fuente sigue vigente, y el fallo queda en `/traces?status=error` y en las métricas.

## 4. Qué vio el agente
Cada `llm_run` guarda el contexto exacto. Por ejemplo, el tester de la regla 17:

| Campo | Contenido (recortado) |
|---|---|
| `model` / `chain` | `deepseek/deepseek-v4.1-flash` / `[deepseek-v4-flash, qwen3.6, glm5.3]` |
| `config_id` / `prompt_hash` | `2` / `2bd56e0b643f` |
| `instructions` (2.072 car.) | "You write the tests for ONE business rule, from its text and the process context only. You never see the code…" |
| `user_prompt` (5.169 car.) | "Use case description (conventions shared by all its rules): Decides whether each supplier invoice is paid according to Norma_Pagos_v3…" |
| `output` (5.984 car.) | `{"tests": [{"name": "issuer_nif_exact_match_in_suppliers", "fires": false, "sources_json": "{\"suppliers\": [{\"id\": \"P001\", …` |
| `retry_prompts` / `failed_attempts` | `[]` / `[]` |
| tokens | 2.566 → 2.787 · 0 reintentos · 1 petición |

El compiler de la misma regla recibió 10.910 caracteres de instrucciones (el contrato del código, las guías y los ejemplos) y 10.438 de mensaje, y devolvió el código (1.835 caracteres). Los 26 `llm_run` ocupan 156 kB en total (máx. 8,4 kB por fila en Postgres, comprimido).

## 5. Métricas (`GET /processes/2/metrics`, `coverage/25-metrics.json`)
| Span | Nº | Errores | p50 | p95 |
|---|---|---|---|---|
| upload_document | 20 | 0 | 14,5 ms | 2.022 ms |
| ocr | 4 | 0 | 1.241 ms | 2.139 ms |
| sync_source | 2 | 1 | 6.613 ms | 8.191 ms |
| norm | 1 | 0 | 6.522 ms | — |
| compile_rule | 12 | 0 | 17.155 ms | 33.281 ms |
| coder_attempt | 12 | 0 | 4.434 ms | 27.324 ms |
| run_tests | 12 | 0 | 32 ms | 42 ms |
| impact_check | 13 | 0 | 19 ms | 172 ms |
| activate_rule | 12 | 0 | 12 ms | 14 ms |
| llm_run | 26 | 0 | 5.951 ms | 26.516 ms |
| run_process | 2 | 1 (409) | 164 ms | 310 ms |
| evaluate_rule | 35 | 0 | 24 ms | 29 ms |
| reprocess (dry run) | 1 | 0 | 317 ms | — |
| suggest_escalation | 1 | 0 | 2.479 ms | — |
| export_outcomes | 2 | 0 | 7,5 ms | 9,8 ms |

Proceso 2: 20 facturas decididas (18 PAGAR, 2 ESCALAR; tras la resolución, 1 NO_PAGAR), 61,3 facturas/s y 1 escalada.

| Rol | Llamadas | Entrada | Salida | Reintentos |
|---|---|---|---|---|
| normalizer | 1 | 3.663 | 2.204 | 0 |
| tester | 12 | 30.870 | 29.677 | 0 |
| compiler | 12 | 71.952 | 8.706 | 0 |
| assistant | 1 | 2.995 | 353 | 0 |
| **Total** | 26 | **109.480** | **40.940** | 0 |

A escala (`trace_demo`, 500 facturas y 11 reglas): `run_process` 743 ms, `evaluate_rule` p50 50 ms · p95 71 ms, `upload_document` ×1.003 con p50 14 ms · p95 125 ms.

## 6. Cómo auditarlo tú
```bash
API=http://localhost:8010
curl -s "$API/processes/2/instances" | jq '.[] | {id, name, decision}'           # elige una factura
curl -s "$API/instances/19/trace" | jq '{file, decisions: [.decisions[] | {decision, author, reason}], spans: [.spans[] | {step, status, duration_ms, trace_id}]}'
curl -s "$API/traces/01a0b88dc1823b7a49e6482bfd7d0c99" | jq                      # árbol de la subida: OCR, símbolos
curl -s "$API/rules/17/trace" | jq '{lifecycle: [.lifecycle[] | {step, author: .data.author}], compilations}'
curl -s "$API/traces?process_id=2&name=llm_run&limit=5" | jq '.[] | .data | {role, model, input_tokens, output_tokens, prompt_hash}'
curl -s "$API/processes/2/events?step=resolution" | jq                          # quién cambió qué decisión
curl -s "$API/traces?status=error" | jq '.[] | {step, error: .data.error}'       # todo lo que falló
curl -s "$API/processes/2/metrics" | jq '{steps, llm}'
```

## 7. Huecos conocidos
1. **Autor en la UI.** El informe de #49 detectó que el frontend enviaba `X-Usuario-Id` en vez de `X-User-Id`, así que las acciones hechas desde la UI no tenían autor. En `origin/dev` (tras #50), `frontend/src/api/http.ts:33` ya envía `X-User-Id`: está verificado en el código, pero no en vivo.
2. **Vision y text-judge** no se han ejecutado en vivo porque no hay modelo de visión configurado. `focused_read` y `reextract_document` tampoco se han visto en vivo (cubiertos por `test_process_api`).
3. **Todos los LLM caídos:** cubierto solo por tests (`compile_rule` y `llm_run` en `error`, "every model failed"). El fallback a un segundo modelo tampoco se ha visto en vivo.
4. **`POST /users`** (y `POST /login`) no tienen span.
5. **`/v1/extractions` en solitario** genera trazas propias, sin enlace a ninguna factura.
6. **El feed del use case** (`/processes/{id}/events`) busca la config dentro de `events.data` sin índice. `events` solo tiene índices por trace, instancia, proceso, regla, norma y fecha.
7. **Cada `llm_run` guarda el prompt completo,** sin deduplicar por `prompt_hash`. Las filas crecen, pero la auditoría es simple (ADR 0018).

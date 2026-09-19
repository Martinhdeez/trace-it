# Informe de la noche — 19 sep 2026

## Resultado principal
**Desde la norma original de Alberto (6 frases del Excel) hasta las decisiones: 471/471 contra el golden, en 3 ejecuciones seguidas**, con modelos reales (Helmcode, deepseek-v4-flash). Entre 0,9 y 2,3 min de la norma al resultado. Los 29 escaneos van a ESCALAR (`MISSING_DATA`).

## Política de decisión (la tuya, ya en código y configuración)
| Situación | Decisión |
|---|---|
| Incumple la norma | NO_PAGAR |
| Duda real (p. ej. un pedido en varias facturas) | ESCALAR |
| No se puede aplicar la regla: dato nulo o ilegible, error del código, falta un dato en el proceso, empate | ESCALAR |

## Qué entró en `dev` esta noche (todo con el CI en verde y el golden en 471/471)
| PR | Qué |
|---|---|
| #41 | Datos obligatorios: si falta uno, ESCALAR (`MISSING_DATA`) |
| #43 | Ensayo del sábado: `docs/runbook-batch2.md`, reprocesar, export por lote, validador, backup |
| #44 | Política incumplir → NO_PAGAR; el motor no ejecuta si hay reglas compilando; fuera el umbral del 5%; `docs/mentor-questions.md` |
| #42 | **Trazabilidad completa**: árbol de spans en Postgres + OpenTelemetry (Logfire/Phoenix), contexto exacto de cada llamada al LLM; `/traces`, `/instances/{id}/trace`, `/rules/{id}/trace`, `/processes/{id}/metrics` |
| #45 | ERP por caso de uso (arregla el 404 de la demo) + cadena de modelos de reserva si cae Helmcode (`make demo-llm-down`) |
| #46 | Duda → ESCALAR (pedido duplicado); el motivo de cada decisión es el código de la regla |
| #47 | `docs/scale-and-cost.md`: cifras medidas y fórmula de coste |
| #48 | Límite de tokens por rol, reserva también ante respuestas cortadas, modelo para el asistente |
| #35 | Endpoints de consola de Mateo (conflictos resueltos) |

## Cifras para la defensa
- **Motor:** 899 facturas/s (11 reglas), 588/s (16 reglas). **0 tokens por factura**: sin LLM al decidir.
- **Norma → reglas activas:** unos 85-100 s con 5 compilaciones en paralelo. Unos 12k tokens por regla y 149k por la norma completa.
- **Ingesta:** 101 PDFs/s (texto). **ERP:** 516 filas en 5,4 s, con reintentos `ORA-00600` superados solos.
- Detalle: `docs/scale-and-cost.md`, `demo-logs/REPORT-integrated-run.md`.

## Para ver ahora
- Dashboard: http://localhost:8020/#p=5 (API demo en :8010, ERP en :8009). Clic en una regla para ver código, tests, traza y el contexto exacto que vio cada agente.
- La API de la demo corre con el código de antes de #45-#48. Hay que reiniciarla con `dev` y activar las nuevas versiones de la configuración (`POST /agent-configs/{id}/activate`).

## Preguntas para el mentor (`docs/mentor-questions.md`)
1. ¿Los escaneos sin texto van a ESCALAR o hay que leerlos? (el OCR de Álvaro ya está en `dev`)
2. ¿La referencia admite más de un resultado válido?
3. Pedido en dos facturas (PO-2026-0492): hoy ESCALAR; confirmar.
4. ERP ya PAGADA, fecha imposible, texto incrustado en el PDF: hoy NO_PAGAR / NO_PAGAR / se ignora.
5. Fecha de corte 2026-09-18 para el lote 2; hoja `pendiente_revisar`.

## Decisiones pendientes tuyas
1. ¿La norma v4 del sábado se aplica también al lote 1? (la guía supone que no; si sí: `reprocess`)
2. ¿Una actualización del ERP vuelve a decidir el lote 1? (la guía: sí, después de revisar la vista previa)
3. Token de Logfire si quieres el panel web (opcional).

## Riesgos conocidos
- El normalizador puede variar entre ejecuciones (en una salió `explicit` y en otra `policy`, con la misma decisión). **Para la entrega: generar, comprobar contra el golden y congelar.**
- La regla de pedido duplicado crece con el cuadrado de las facturas: llegaría al límite de 10 s hacia las 8.000.
- Worktrees de los agentes en `/Users/apple/orca/projects/trace-pay/.claude/worktrees/` y bases de prueba (`trace_test_*`, `trace_bench`, `trace_rehearsal`) sin limpiar.

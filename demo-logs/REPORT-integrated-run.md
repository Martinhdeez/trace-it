# Ejecución integrada de trace-it (dev @ 488146c) — 19-sep, 04:46–04:49

**Dashboard:** http://localhost:8020/#p=5 → en el selector, proceso **5 · "Invoice payment - integrated 04:46"**.
Pulsa cualquier tarjeta de la columna "Agents" para ver el árbol de la traza y el contexto exacto que vio cada modelo.

## Qué se ejecutó
1. API reiniciada con el código de `dev` y la migración 0008 (los eventos pasan a ser spans).
2. Pack recargado; activadas compiler v2 (`auto_activate_max_change: 1.0`) y normalizer v2 (`failed_check_decision: NO_PAGAR`). El tester ya estaba en deepseek-v4-flash (v2).
3. Proceso 5 creado desde cero: sin reglas, use case "Invoice payment".
4. Ingesta: 500 PDFs + Excel. 471 con capa de texto; 29 escaneos sin símbolos.
5. ERP: sync real (516 filas, 26 páginas, 3 reintentos ORA-00600, 1 login), copiada al proceso 5.
6. Norma `Norma_Pagos_v3` tal cual → 6 frases, 11 comprobaciones, 2 políticas.
7. Las 11 reglas compilaron al primer intento, pasaron sus tests y se activaron solas.
8. Motor, export y comparación con el golden.

## Resultados
| | Nº |
|---|---|
| PAGAR | 435 |
| NO_PAGAR | 36 |
| ESCALAR | 29 |

- **469/471 coinciden con el golden.** Los 2 fallos son el mismo caso: `2026-0233-A_catering.pdf` y `factura_41082.pdf` salen PAGAR; se esperaba ESCALAR (*DUPLICATE_PO: PO-2026-0492*).
- **Escaneos (29):** todos ESCALAR con `MISSING_DATA: base, date, iban, issuer_nif, purchase_order, total, vat_amount, vat_rate`.

## Tiempos (de las trazas)
| Paso | Tiempo |
|---|---|
| Ingesta (500 PDFs + Excel) | 6,1 s |
| Sync ERP | ~6 s |
| Normalizador | 19,4 s |
| Tester por regla | p50 12,3 s · máx 27,6 s |
| Coder por regla | p50 5,4 s · máx 21,4 s |
| Compilación completa por regla | p50 18,6 s · máx 33,8 s |
| 11 reglas en paralelo | 64,2 s |
| **Norma enviada → todo activo** | **84,7 s** |
| Motor (500 facturas, 11 reglas) | 0,63 s → **789 facturas/s** |
| Cada regla sobre 500 facturas | p50 41 ms · p95 63 ms |
| Export | 66 ms |

## Tokens (`deepseek/deepseek-v4.1-flash`)
| Rol | Llamadas | Entrada | Salida |
|---|---|---|---|
| normalizer | 1 | 3.433 | 3.760 |
| tester | 11 | 29.065 | 30.505 |
| coder | 11 | 70.610 | 13.394 |
| **Total** | 23 | **103.108** | **47.659** |

Sin reintentos ni errores.

## Traza de ejemplo (norma → regla #60)
    norm 19,6 s
    ├ normalize_norm 19,5 s
    │ └ llm_run normalizer 19,4 s · 3433→3760 tok
    └ compile_rules 64,2 s
      ├ compile_rule #60 30,4 s
      │ ├ llm_run tester 24,7 s · 2640→3200 tok
      │ ├ coder_attempt 1 · 5,6 s
      │ │ ├ llm_run compiler 5,6 s · 7560→1154 tok
      │ │ └ run_tests 26 ms · 10/10 ok
      │ ├ impact_check 82 ms → auto
      │ └ activate_rule 25 ms
      └ … 10 compile_rule más

Por factura (`/instances/{id}/trace`): PAGAR `2026-01-08_P001.pdf` (ninguna regla dispara); NO_PAGAR `2026-03-19_P008.pdf` (regla #57 `IMPOSSIBLE_DATE 2026-02-31`); ESCALAR `copia_2026_0518.pdf` (`MISSING_DATA`).

## Qué vio un agente
`/rules/60/trace` guarda el prompt completo: instrucciones (plataforma + guía del caso de uso + ejemplos), mensaje (regla, símbolos, filas reales de las fuentes) y respuesta.

## Pendiente (encargado)
1. **Pedido duplicado dentro del lote**: el normalizador leyó "nunca pagar dos veces" solo contra el ERP. Es una duda para el mentor → por tu criterio, ESCALAR.
2. **El motivo de un NO_PAGAR muestra el texto de la regla** en vez de su código (`IMPOSSIBLE_DATE ...`).
3. El modelo configurado (`helmcode:deepseek-v4-flash`) responde con el nombre `deepseek/deepseek-v4.1-flash`: es un alias.
4. En este proceso las trazas por factura empiezan en el motor porque la ingesta de la demo va directa a la BD; la ingesta real (API de Álvaro) sí se traza.

Datos en bruto: `demo-logs/integrated/`.

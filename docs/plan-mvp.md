# trace-it: plan del MVP

**Estado:** propuesta. Basado en `docs/plano-aplicacion.md` (decisiones P1-P22).

## Objetivo
Un proceso ("Pago de facturas") funcionando de punta a punta en la aplicación: ingesta, conectores, extracción, reglas compiladas por dos agentes, motor, histórico, escalado y exportación. El `outcomes.jsonl` del lote 1 sale de ese flujo y es correcto. Todo lo propio de las facturas (tipos de decisión, símbolos, fuentes, reglas) se da de alta como datos del proceso, no en el código.

## Hitos
| Hito | Cuándo | Criterio de hecho |
|---|---|---|
| H0 Contratos | Viernes noche | `docker compose up` levanta Postgres + FastAPI; esquema creado; firmas y endpoints acordados; cada persona puede trabajar sin esperar a otra |
| H1 Flujo completo | Sábado 10:00 | Las 471 facturas con texto pasan por ingesta, extracción, reglas de la norma v3 y motor |
| H2 Lote 1 cerrado | Sábado 14:00 | 500 facturas, incluidos escaneos, 0 en `REVISION`, resultado revisado contra nuestro análisis. Frontend básico usable |
| H3 Lote 2 | Sábado 18:00 en adelante | Lote 2 + ERP actualizado + norma v4, todo a través de la aplicación |
| H4 Entrega | Domingo 10:30 | Repo público con `outcomes.jsonl`, `outcomes_lote2.jsonl` y `albertitos_plan.pdf` |

## Estructura del repo
Ver `docs/guia-equipo.md` (organizado por funcionalidades en `backend/app/features/`).

## Tablas (fuente de verdad: `backend/app/models.py` y las migraciones)
- `usuarios`: nombre, email, rol (`responsable`/`operador`).
- `procesos`: id, nombre, descripción.
- `tipos_decision`: proceso, nombre, prioridad, por defecto, requiere persona.
- `simbolos`: proceso, nombre, tipo, descripción.
- `ficheros`: hash (clave), nombre original, bytes, texto extraído, fecha de ingesta.
- `fuentes`: proceso, nombre de la fuente (en facturas: `proveedores`, `pedidos`, `erp`), fichero o descarga de origen, filas (`jsonb`).
- `instancias`: proceso, fichero, nombre, estado (`PENDIENTE`, `REVISION`, `DECIDIDA`), motivo de la revisión, símbolos acordados (`jsonb`).
- `extracciones`: instancia, papel (`extractor_1`/`extractor_2`), símbolos (`jsonb`), coste, latencia.
- `reglas`: proceso, texto, tipo (`requisito`/`prohibicion`), decisión si salta, código A, código B, tests A, tests B, hash, estado (`borrador`, `rechazada`, `activa`, `retirada`), informe de validación, fecha de activación.
- `decisiones`: instancia, resultado de cada regla (`jsonb`), decisión, hash de las reglas aplicadas, autor (motor o persona), motivo.
- `hallazgos`: decisión, tipo (en facturas: `pagada_indebidamente`, `no_pagada_debiendo`, …), detalle, regla que lo genera.
- `eventos`: traza de todo (paso, entrada, salida, latencia, reintentos, coste).
- `config_llm`: papel, modelo en formato LiteLLM (`proveedor/modelo`).

## Reparto
| Persona | Bloque | Entregable |
|---|---|---|
| Martín | Agentes: compilador (dos agentes, tests cruzados), sandbox, asistente de escalado (el corrector de F12 es de la iteración 2); cliente LLM. Texto de las reglas de la norma v3. Responsable del filtro | `features/agentes/`, `features/llm/`, reglas v3 |
| Mateo | Reglas y decisiones: ciclo de vida de reglas, motor, API de decisiones, auditoría y hallazgos; procesos y usuarios. Tareas en `docs/tareas-mateo.md` | `features/reglas/`, `features/decisiones/`, `features/procesos/`, `features/usuarios/` |
| Álvaro | Todo lo que entra: ingesta (hash, `pdftotext`, render/OCR de escaneos), extracción de símbolos (doble extracción con el cliente LLM, validadores), conector del ERP (token, ORA-00600, 429/Retry-After, límite propio, paginación, foto local), conector del Excel (normalización) | `features/ingesta/`, `features/extraccion/`, `features/fuentes/` |
| Varsovia | Producto e ideas: demo, ADRs, `albertitos_plan.pdf`, hoja de resultados esperados para verificar | Guion de demo, ADRs |
| Carlos | Frontend contra los endpoints de H0 (datos simulados hasta H1): procesos, instancias con traza, alta de regla que encadena crear → compilar mostrando el progreso (compilar tarda 30-60 s) y el informe, cola del responsable (tipos con `requiere_persona` y `REVISION`), exportar | `frontend/` |

## Ruta crítica y riesgos
1. **Texto de las reglas de la norma v3 (Martín, con Varsovia revisando, antes de H1).** Decidir qué produce cada anomalía (NO_PAGAR o ESCALAR) es el mayor riesgo para el filtro. Hay casos pendientes en `.artifacts/specs/2026-09-18-reglas-sistema.md`. Preguntar a un mentor con ejemplos concretos.
2. **Escaneos (29).** Además de la doble extracción, se revisan a mano antes de H2.
3. **Verificación final antes de exportar:**
   - Una línea por fichero.
   - Nombres exactos.
   - 0 instancias en `REVISION`.
   - Diferencias con la hoja de resultados esperados revisadas una a una.

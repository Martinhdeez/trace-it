# Plan del MVP

**Estado:** propuesta. Basado en `docs/plano-aplicacion.md` (decisiones P1-P22).

## Objetivo
Un proceso ("Pago de facturas") funcionando de punta a punta en la aplicación: ingesta, conectores, extracción, reglas compiladas por dos agentes, motor, histórico, escalado y exportación. El `outcomes.jsonl` del lote 1 sale de ese flujo y es correcto.

## Hitos
| Hito | Cuándo | Criterio de hecho |
|---|---|---|
| H0 Contratos | Viernes noche | `docker compose up` levanta Postgres + FastAPI; esquema creado; firmas y endpoints acordados; cada persona puede trabajar sin esperar a otra |
| H1 Flujo completo | Sábado 10:00 | Las 471 facturas con texto pasan por ingesta, extracción, reglas de la norma v3 y motor |
| H2 Lote 1 cerrado | Sábado 14:00 | 500 facturas, incluidos escaneos, 0 en `REVISION`, resultado revisado contra nuestro análisis. Frontend básico usable |
| H3 Lote 2 | Sábado 18:00 en adelante | Lote 2 + ERP actualizado + norma v4, todo a través de la aplicación |
| H4 Entrega | Domingo 10:30 | Repo público con `outcomes.jsonl`, `outcomes_lote2.jsonl` y `albertitos_plan.pdf` |

## Estructura del repo
```
docker-compose.yml        # postgres + backend
backend/
  app/main.py             # FastAPI: endpoints
  app/schema.sql          # tablas
  app/db.py
  app/llm.py              # LiteLLM + configuración por papel
  app/ingesta.py          # hash, texto, imagen de escaneos
  app/conectores/excel.py
  app/conectores/erp.py   # cliente tolerante a fallos + foto local
  app/extraccion.py       # doble extracción + validadores
  app/compilador.py       # dos agentes: código + tests, comprobación estática
  app/sandbox.py          # ejecución aislada de código generado
  app/motor.py            # todas las reglas, precedencia, registro
  app/auditoria.py        # reejecución sobre histórico
  app/escalado.py         # sugerencia del asistente
frontend/
```

## Tablas (primer borrador)
- `procesos`: id, nombre.
- `simbolos`: proceso, nombre, tipo, descripción.
- `ficheros`: hash (clave), nombre original, bytes, texto extraído, fecha de ingesta.
- `fuentes`: proceso, nombre (`proveedores`, `pedidos`, `erp`), fichero o descarga de origen, filas (`jsonb`).
- `instancias`: proceso, fichero, estado (`PENDIENTE`, `REVISION`, `DECIDIDA`).
- `extracciones`: instancia, papel (`extractor_1`/`extractor_2`), símbolos (`jsonb`), coste, latencia.
- `reglas`: proceso, texto, tipo (`requisito`/`prohibicion`), decisión si salta, código A, código B, tests A, tests B, hash, estado (`borrador`, `rechazada`, `activa`, `retirada`), informe de validación.
- `decisiones`: instancia, resultado de cada regla (`jsonb`), decisión, hash de las reglas aplicadas, autor (motor o persona), motivo.
- `hallazgos`: decisión, tipo (`pagada_indebidamente`, `no_pagada_debiendo`, …), regla que lo genera.
- `eventos`: traza de todo (paso, entrada, salida, latencia, reintentos, coste).
- `config_llm`: papel, proveedor, modelo.

## Reparto
| Persona | Bloque | Entregable |
|---|---|---|
| Martín | H0 contratos. Compilador (dos agentes, tests cruzados), sandbox, escalado asistido. Texto de las reglas de la norma v3. Responsable del filtro | `compilador.py`, `sandbox.py`, `escalado.py`, reglas v3 |
| Mateo | Core de ejecución: `llm.py` (LiteLLM, configuración por papel), extracción de símbolos (doble extracción, validadores, `REVISION`), motor, auditoría, endpoints de la API | `llm.py`, `extraccion.py`, `motor.py`, `auditoria.py`, `main.py` |
| Álvaro | Todo lo que entra: ingesta (hash, `pdftotext`, render/OCR de escaneos), conector del ERP (token, ORA-00600, 429/Retry-After, límite propio, paginación, foto local), conector del Excel (normalización) | `ingesta.py`, `conectores/erp.py`, `conectores/excel.py` |
| Varsovia | Producto e ideas: demo, ADRs, `albertitos_plan.pdf`, hoja de resultados esperados para verificar | Guion de demo, ADRs |
| Carlos | Frontend contra los endpoints de H0 (datos simulados hasta H1): procesos, instancias con traza, alta de regla con informe, colas `ESCALAR`/`REVISION`, exportar | `frontend/` |

## Ruta crítica y riesgos
1. **Texto de las reglas de la norma v3 (Martín, con Varsovia revisando, antes de H1).** Decidir qué produce cada anomalía (NO_PAGAR o ESCALAR) es el mayor riesgo para el filtro. Hay casos pendientes en `.artifacts/specs/2026-09-18-reglas-sistema.md`. Preguntar a un mentor con ejemplos concretos.
2. **Escaneos (29).** Además de la doble extracción, se revisan a mano antes de H2.
3. **Verificación final antes de exportar:**
   - Una línea por fichero.
   - Nombres exactos.
   - 0 instancias en `REVISION`.
   - Diferencias con la hoja de resultados esperados revisadas una a una.

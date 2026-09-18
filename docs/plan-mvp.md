# trace-it: plan del MVP

**Estado:** propuesta. Basado en `docs/plano-aplicacion.md` (decisiones P1-P23). Agentes: `docs/plan-agentes.md`.

## Objetivo
Un proceso ("Pago de facturas") funcionando de punta a punta en la aplicación: ingesta, conectores, extracción, reglas compiladas por dos agentes, motor, histórico, escalado y exportación. El `outcomes.jsonl` del lote 1 sale de ese flujo y es correcto. Todo lo propio de las facturas (tipos de decisión, símbolos, fuentes, reglas) se da de alta como datos del proceso, no en el código.

## Ruta crítica (2026-09-19)
**El filtro de apto va primero.** La ruta crítica termina cuando la comparación de ese `outcomes.jsonl` con los 433 casos limpios y los 38 casos trampa de `docs/reglas-pago-facturas.md` sale sin diferencias. Ese `outcomes.jsonl` sale de las reglas v3 escritas a mano (`feat/reglas-v3-manuales`). Todo lo demás queda por debajo de esa comparación.

Mientras `data-ingestion` no esté terminada, avanzamos en todo lo que no depende de ella:
1. **Mentor, a primera hora.** Confirmar R01, R02, R07 y R08. Confirmar también cómo tratar el texto con instrucciones incrustadas, con los ficheros donde nuestra política difiere de la de hsdatos: F26-2201_transportes, F26-3355, F26-7728, factura_5402, factura_6612, 2026-23904 y FA-3388. La lista la sacó una revisión externa; hay que comprobarla contra el lote antes de llevarla. Hay que preguntar y no copiar la política de otro equipo.
2. **Unir `feat/reglas-v3-manuales` y `fix/exportar-decision-motor` a `dev`.** No dependen de `data-ingestion`.
3. **Conector genérico de APIs HTTP**, que sirva para cualquier ERP (ver "Fuentes: conector genérico"). El ERP del reto es su primera configuración.
4. **`outcomes.jsonl` con las reglas manuales**, en paralelo con el punto 3. Mientras no exista la foto real del ERP, R12-R14 se evalúan contra una foto preparada a mano con los datos del ERP del reto (incluye los 9 pedidos PAGADA). La entrega final se hace con la foto real descargada de la API, porque la norma exige cruzar con el ERP.
5. **Si una comprobación falla, la factura nunca sale PAGAR.** Si falla el LLM, se agota el tiempo o falta un campo, la instancia queda en `REVISION` o se decide ESCALAR. Es una sola comprobación en el motor y se hace junto al punto 4. Las pruebas de caos (`--llm-down`, `--llm-429` y `--llm-timeout`) quedan para después.
6. **Integrar `data-ingestion` cuando esté terminada.** Se une sola, se prueba el flujo con unas pocas facturas y después se sigue.
7. **Plantillas regex para las facturas nativas que quedan en `NEEDS_REVIEW` (202 de 501).** El LLM y la revisión humana quedan solo para lo que siga sin cerrar.

**Congelado hasta que salga el punto 4:** proceso gastos-viaje, frontend y roles de usuario.
**Fuera de la ruta crítica:** el compilador de dos agentes. Se enseña en la demo, comparándolo con las reglas manuales.
**Cuando el flujo funcione:** pruebas de caos, coste en euros por factura y por 10.000 facturas, ADRs 2-5 y guion de defensa (Varsovia).

### Fuentes: conector genérico
Ningún ERP concreto entra en el código. Un único conector de APIs HTTP se configura por proceso en `sources.json` (ver `docs/process-packs.md`). Cada configuración declara:
- la URL base y la autenticación (token con caducidad y renovación);
- la paginación;
- los reintentos: errores transitorios, como el ORA-00600 del reto, y 429 con `Retry-After`;
- el límite de peticiones por segundo;
- el formato de respuesta y su codificación (XML en ISO-8859-1 en el reto);
- cómo se mapea cada campo a las columnas que leen las reglas.

El resultado siempre es una foto local guardada como una fila nueva de `fuentes`. Las reglas leen esa foto y nunca la API. Un ERP nuevo es un fichero de configuración, no código nuevo.

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
- `config_agente`: versiones de la configuración de cada papel de agente (cadena de modelos en formato PydanticAI `proveedor:modelo`, ajustes, reintentos, límite de peticiones, prompt); solo se añaden filas y hay una activa por papel. Sustituye a `config_llm` (ver `docs/plan-agentes.md` §4).

## Reparto
| Persona | Bloque | Entregable |
|---|---|---|
| Martín | Agentes: compilador (dos agentes, tests cruzados), sandbox, asistente de escalado (el corrector de F12 es de la iteración 2); infraestructura de agentes sobre PydanticAI y su configuración (`docs/plan-agentes.md`). Texto de las reglas de la norma v3. Responsable del filtro | `features/agentes/`, `features/llm/`, reglas v3 |
| Mateo | Reglas y decisiones: ciclo de vida de reglas, motor, API de decisiones, auditoría y hallazgos; procesos y usuarios. Tareas en `docs/tareas-mateo.md` | `features/reglas/`, `features/decisiones/`, `features/procesos/`, `features/usuarios/` |
| Álvaro | Todo lo que entra: ingesta (hash, `pdftotext`, render/OCR de escaneos), extracción de símbolos (doble extracción con un agente de PydanticAI sobre `features/llm/`, validadores sin reintentar al modelo; `docs/plan-agentes.md` §3.3), conector del Excel (normalización). El conector genérico de APIs HTTP (ERP) queda por asignar, porque Álvaro está con el OCR | `features/ingesta/`, `features/extraccion/`, `features/fuentes/` |
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

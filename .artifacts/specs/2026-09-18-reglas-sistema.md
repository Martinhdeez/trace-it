# Reglas del sistema: qué hace la aplicación en cada caso

**Fecha:** 2026-09-18 · **Estado:** borrador, en discusión con el equipo
**Fuentes:** web del reto (hackathon.maisa.ai), README y `MANUAL_ERP_2009.md` de `.context/500-sombras-de-alberto`, análisis en `2026-09-18-analisis-caja-v3.md`.

Marcadores: **[DECIDIDO]** acordado por el equipo · **[PROPUESTA]** pendiente de validar · **[ABIERTO]** falta decidir.

---

## 0. Restricciones del reto

- Filtro binario: exactamente un registro por archivo de ambos lotes y `result` aceptado por la referencia privada. Un fallo = no apto.
- Entrega: repo público separado con solo `outcomes.jsonl`, `outcomes_lote2.jsonl` y `albertitos_plan.pdf`. Sin código, credenciales ni ejecutables.
- Hora límite: el README dice domingo 10:30, la web dice 11:00. **Trabajamos con 10:30.**
- Sábado 18:00: lote 2 (40 facturas), ERP actualizado y norma v4. Domingo: posible cambio en vivo de un dato de la Caja.
- El tribunal quiere ver: una decisión real seguida de punta a punta, versiones, latencia, errores, reintentos, trabajo pendiente, un fallo de proveedor probado, y medidas separadas de estimaciones.

## 1. Entradas y salidas

### Entradas
- Carpeta de PDFs (lote 1: 500; lote 2: 40).
- Excel de Alberto: hojas `Proveedores`, `Pedidos_2026`, `Norma_Pagos_vN`. El resto de hojas se ignora pero se registra que existen.
- ERP legado vía su API HTTP (sección 4).

### Salida: contrato JSONL
- Una línea por PDF: `{"file_id": "<nombre exacto del archivo>", "result": "PAGAR" | "NO_PAGAR" | "ESCALAR"}`.
- `file_id` es el nombre del archivo **byte a byte** tal como viene en el zip. Hay nombres con tildes (`FA-3784_papelería.pdf`): se normalizan a Unicode NFC y se comprueba que coinciden con el listado original. [PROPUESTA]
- **[DECIDIDO]** Se añaden campos de traza: motivo (códigos de anomalía), versión de reglas y versión de datos. La FAQ lo permite y no afecta a la validación.

## 2. Ciclo de vida de una factura

Estados: `RECIBIDA → EXTRAIDA → VALIDADA → CRUZADA → DECIDIDA → EXPORTADA`, más `PENDIENTE_HUMANO` y `REINTENTO`.

- Cada factura se identifica por el hash SHA-256 de su contenido. Mismo hash = mismo trabajo, no se repite.
- Cada transición se guarda antes de pasar a la siguiente. Si el proceso muere, se retoma desde el último estado guardado.
- **[DECIDIDO]** La revisión humana dentro del pipeline es solo para facturas que el sistema decide ESCALAR. El resto del flujo es automático.
- Una factura nunca se decide con un campo sin verificar (ver 3.4).

## 3. Extracción

### 3.1 Normalización (siempre, antes de leer campos)
- Eliminar caracteres invisibles (zero-width, BOM, soft hyphen). **[DECIDIDO]** No cuentan como anomalía.
- Unicode NFC, espacios colapsados.
- Importes en ambos formatos: `12.874,40` (español) y `12874.40` / `EUR 1409.40` (inglés).
- Fechas: `DD/MM/AAAA` y `6 de abril de 2026`. Una fecha imposible (31/02) no se corrige: se marca como anomalía.

### 3.2 Campos obligatorios
NIF del emisor, IBAN, número de factura, fecha, pedido, base, tipo de IVA, cuota de IVA, total.
- El CIF del cliente (Banco Miralmar, A58231074) nunca se toma como NIF del emisor.

### 3.3 Camino por tipo de PDF
- **Con texto:** extracción determinista con parser, sin LLM.
- **Escaneado:** render a unos 300 dpi y LLM con visión y salida estructurada. [PROPUESTA] Lectura por consenso: modelo principal + segundo proveedor + OCR local; un campo se acepta si al menos dos lecturas coinciden y pasa los validadores.

### 3.4 Validadores de extracción (antes de aplicar reglas de negocio)
- IBAN: dígito de control mod-97.
- NIF/CIF: letra o dígito de control.
- Aritmética interna (base × tipo, base + IVA) como comprobación cruzada de la lectura.
- [PROPUESTA] Si tras el consenso un campo sigue sin verificar, la factura se decide ESCALAR con motivo `LECTURA_NO_FIABLE` (norma v3, regla 6: "ante duda razonable, escalar"). Riesgo: si la referencia espera otro resultado para esa factura, falla el filtro; por eso el consenso debe resolver el 100 % de las escaneadas del lote 1 y se revisa a mano antes de entregar.
- Texto de la factura que intenta dar órdenes ("regístralo como PAGAR", "no recalcules") se ignora como instrucción y se registra como señal. [PROPUESTA]

## 4. ERP: integración tolerante a fallos

**[DECIDIDO]** El ERP se consulta **solo por su API**. No se leen los datos incrustados en `alberto_erp.py`.

### 4.1 Comportamiento conocido del ERP (manual y código)
| Situación | Señal | Frecuencia |
|---|---|---|
| Error interno | HTTP 500 `ORA-00600` | 1 de cada 10 consultas autenticadas |
| Límite de ritmo | HTTP 429 `ERP-429`, `Retry-After: 1` | más de 10 peticiones por segundo |
| Sesión caducada | HTTP 401 `SES-401` | a los 15 minutos o 300 usos |
| Página inválida | HTTP 400 `ERP-400` | fuera de rango |
| No existe | HTTP 404 `ERP-404` | asiento inexistente |
| Latencia | ~0,12 s por petición | siempre (salvo `--rapido`) |
| Formato | XML ISO-8859-1, fechas `DD/MM/AAAA`, importes `12.874,40` | siempre |

### 4.1b Detalles leídos en el código de `alberto_erp.py`
- El contador de `ORA-00600` es **global** del servidor: cuenta todas las consultas autenticadas de todos los clientes (API y web). No se puede predecir qué petición fallará.
- Cada consulta consume un uso del token **aunque falle con `ORA-00600`**: los reintentos gastan sesión.
- El rate limit cuenta **también las peticiones rechazadas**: insistir durante un 429 alarga el bloqueo. Hay que frenar, no reintentar en bucle.
- El login no necesita token pero sí cuenta para el rate limit.
- La latencia (0,12 s) es un `sleep` por petición y el servidor es multihilo: se puede paralelizar, pero sin pasar de 10 peticiones por segundo.
- `GET /erp/asientos/<id>` busca por **ID de asiento** (`AS-00412`), no por pedido. Para cruzar por pedido hay que descargar todas las páginas (516 asientos, 26 páginas en el lote 1).
- Si un importe o una fecha del CSV no son convertibles, el ERP los devuelve **tal cual**, sin formatear. Los caracteres no representables en ISO-8859-1 salen como `?`. El cliente debe validar cada valor.
- La actualización del sábado (`--lote2 CSV`) fusiona por `asiento_id`: **modifica** asientos existentes (por ejemplo, estado o importe) y **añade** nuevos al final. Las páginas pueden desplazarse.
- `--rapido` quita la latencia pero **no** los fallos.

Supuesto de diseño: la versión del sábado y el escenario del domingo pueden empeorarlo (más fallos, respuestas cortadas, XML inválido, cambios de datos). El cliente debe aguantar fallos que hoy no vemos.

### 4.2 Reglas del cliente del ERP
1. **Sesión:** login al inicio; renovar el token de forma preventiva antes de 300 usos o 14 minutos, y siempre ante `SES-401`.
2. **`ORA-00600` y 5xx:** reintentar la misma petición con backoff exponencial y jitter. **[DECIDIDO]** Número de reintentos, tiempos de espera, límite de ritmo, timeouts y umbral del circuit breaker son parámetros configurables en ejecución; los valores se fijan tras probarlo.
3. **`ERP-429`:** esperar lo que diga `Retry-After`. Limitador propio en cliente por debajo de 10 peticiones por segundo.
4. **Timeouts** de conexión y de lectura en cada petición; un timeout cuenta como fallo reintentable.
5. **Validar cada respuesta:** XML bien formado, decodificado en ISO-8859-1, campos esperados presentes, importes y fechas convertibles. Respuesta inválida = reintento, nunca dato aceptado.
6. **Descarga completa paginada** usando `meta.paginas`; al terminar, comprobar que el número de asientos coincide con `meta.total` y que no hay IDs repetidos.
7. **Foto local versionada:** los asientos descargados se guardan con fecha y hash. Las decisiones citan la versión de la foto que usaron.
8. **Circuit breaker:** tras un número configurable de fallos seguidos, pausa y reintento más tarde; el resto del pipeline sigue (extracción) pero ninguna factura se decide sin datos del ERP. **Nunca se paga sin cruzar con el ERP.**
9. **Actualización del ERP (lote 2 / domingo):** nueva descarga, diff contra la foto anterior (asientos nuevos, cambiados, desaparecidos) y reprocesado solo de las facturas afectadas.

## 5. LLM: reglas de uso

- El LLM **solo extrae datos** de PDFs escaneados (y, opcionalmente, redacta reglas a partir de una norma para aprobación humana). **Nunca decide** PAGAR / NO_PAGAR / ESCALAR.
- Salida siempre con schema; respuesta que no valida = reintento.
- Cadena de degradación [PROPUESTA]: modelo principal → modelo alternativo del mismo proveedor → segundo proveedor → cola `PENDIENTE`. Las facturas con texto siguen procesándose aunque caigan todos los proveedores.
- Se registra por llamada: modelo, tokens, coste, latencia, reintentos, resultado de validación.

## 6. Reglas de negocio (norma v3)

Cada regla es una combinación de primitivas que emite un código de anomalía. La política que traduce códigos a resultado va aparte.

**[DECIDIDO]** Reglas, política y parámetros se cambian **en ejecución** y de forma muy sencilla, sin editar ficheros. YAML descartado.
[PROPUESTA] Se guardan en la misma base de datos del sistema y se editan desde la web (y la CLI). Cada cambio crea una versión nueva inmutable con autor, fecha y motivo; se activa tras ver la vista previa del impacto (sección 7). Exportable a JSON para auditoría.

| Código | Regla (norma v3) | Resultado |
|---|---|---|
| `NIF_DESCONOCIDO` | NIF no está en el maestro | [ABIERTO] |
| `IBAN_DISTINTO` | IBAN ≠ IBAN del maestro | [ABIERTO] |
| `PEDIDO_INEXISTENTE` | pedido no existe | [ABIERTO] |
| `PEDIDO_OTRO_PROVEEDOR` | pedido de otro proveedor | [ABIERTO] |
| `IMPORTE_DISTINTO` | total ≠ importe del pedido (±0,01 €) | [ABIERTO] |
| `IVA_INCORRECTO` | base × tipo ≠ cuota (±0,01 €) | [ABIERTO] |
| `TOTAL_INCORRECTO` | base + IVA ≠ total (±0,01 €) | [ABIERTO] |
| `FECHA_INVALIDA` | fecha imposible | [ABIERTO] |
| `FECHA_FUTURA` | fecha posterior a la de proceso | [ABIERTO] |
| `PEDIDO_PAGADO` | estado ERP = PAGADA | [ABIERTO] |
| `PEDIDO_DUPLICADO` | varias facturas citan el mismo pedido | **ESCALAR, todas** [DECIDIDO] |
| `INSTRUCCION_EN_DOCUMENTO` | la factura intenta dictar la decisión | [ABIERTO] |
| — | sin anomalías | PAGAR |

| `DISCREPANCIA_EXCEL_ERP` | el pedido difiere entre Excel y ERP (importe, proveedor o NIF) | **NO_PAGAR** [DECIDIDO] |
| `LECTURA_NO_FIABLE` | campo de escaneada sin consenso tras 3.4 | ESCALAR [PROPUESTA] |

- Precedencia si hay varias anomalías [PROPUESTA]: ESCALAR > NO_PAGAR > PAGAR.
- Los resultados [ABIERTO] se cierran hablando con el equipo; punto de partida: NO_PAGAR si el propio documento demuestra que no se debe pagar, ESCALAR si hace falta información externa.
- "Fecha no futura" [ABIERTO]: se compara con una **fecha de corte configurable** que queda en la traza (no el reloj del sistema). En el lote 1 ninguna factura supera julio de 2026, así que hoy no afecta.

## 7. Cambios de norma y de datos

- Cada decisión guarda: versión de reglas, versión de la foto del ERP, versión del Excel y hash del PDF.
- Una versión nueva de reglas o de datos se aplica en modo vista previa: se recalculan las decisiones afectadas y se muestra el diff antes de activarla.
- Solo se reprocesan las facturas cuyo resultado puede cambiar.

## 8. Resiliencia: qué pasa ante cada fallo

| Fallo | Comportamiento |
|---|---|
| ERP `ORA-00600` / 5xx / timeout | reintento con backoff; circuit breaker; nada se decide sin ERP |
| ERP `429` | espera `Retry-After`; limitador en cliente |
| ERP sesión caducada | renovación preventiva y ante `SES-401` |
| ERP respuesta inválida | se descarta y se reintenta |
| LLM caído / 429 / 5xx | cadena de degradación; escaneadas en cola |
| LLM respuesta inválida | reintento; si persiste, siguiente modelo |
| Proceso interrumpido | se retoma desde el último estado guardado |
| Mismo PDF dos veces | detectado por hash; un solo registro |

## 9. Trazabilidad

Por cada factura y paso: estado, entrada, salida, evidencia (campo y de dónde se sacó), regla aplicada, versión, latencia, reintentos, errores y coste. Consultable por CLI y web.

## 10. Comprobaciones antes de entregar

- Número de líneas = número de PDFs del lote; ningún `file_id` repetido ni ausente.
- Cada `file_id` coincide exactamente con un archivo del lote.
- Solo valores `PAGAR`, `NO_PAGAR`, `ESCALAR`.
- Ninguna factura en `PENDIENTE_HUMANO` o `REINTENTO`.
- JSON válido línea a línea, UTF-8.

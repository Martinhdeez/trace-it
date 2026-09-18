# Reglas del proceso "Pago de facturas" · norma v3

> **Fuente de verdad:** `processes/invoice-payment.json` (lo que se carga con `make setup`). Este documento explica de dónde sale cada regla. Los textos de regla que se compilan están en inglés en ese fichero; la tabla de la sección 2 da el mismo significado en español.
>
> **Pendiente de confirmar con un mentor:**
> - IBAN distinto (R02) y NIF desconocido (R01): NO_PAGAR (elegido) o ESCALAR (3.2).
> - Tipo de IVA distinto de 21 (R08): ESCALAR (elegido) o NO_PAGAR (3.6).
>
> Ya decidido: R16 no es una regla (será un aviso en la traza); recargo financiero y fechas imposibles → NO_PAGAR; hoja `pendiente_revisar` → sin regla; pedido duplicado (R15) → ESCALAR, con las instancias identificadas por `_instance`.

**Fecha:** 2026-09-18 · **Estado:** cargado como borradores (sin compilar) · **Base:** `Norma_Pagos_v3` (Excel), `analisis-caja-v3.md`, `reglas-sistema.md`, `plano-aplicacion.md` P18-P21.
**Comprobación hecha para este borrador:** `pdftotext` de los 471 PDF con texto + cruce con `Proveedores`, `Pedidos_2026` y los datos del ERP (leídos como texto del `_DATOS_ERP` de `alberto_erp.py`, solo para investigar; el sistema usa la API). Resultado: 433 facturas de texto sin anomalía (442 sin anomalía de maestro ni importes, menos 9 PAGADA en el ERP); las 38 restantes coinciden con la tabla de trampas. Los 29 escaneos no se han comprobado (solo `scan_001`, limpio a la vista).

Convenciones para todas las reglas (el agente compilador debe aplicarlas siempre):
- **Firma:** `evaluate(instance, sources, others) -> {"fires": bool, "reason": str}`. La decisión la fija la regla en su definición (P18). Función pura: sin reloj, red ni disco.
- **Importes:** se comparan en céntimos enteros: `round(x * 100)`. "Coincide (±0,01)" significa `abs(centimos(a) - centimos(b)) <= 1`.
- **Normalización de claves** (antes de comparar, en la regla): `nif` → mayúsculas, sin espacios, guiones ni puntos. `iban` → mayúsculas, sin espacios. `purchase_order` → mayúsculas, sin espacios. Textos de maestros (`company_name`) → `strip()`.
- **Símbolo ausente** (`None`): una regla que lo necesita **no salta** (devuelve `fires=False`), salvo R00, que es la única que castiga la ausencia. Así un campo ausente produce un solo motivo y no una cascada.
- **Reglas dependientes:** si una regla necesita una fila de una fuente que no existe (p. ej. el pedido), no salta; ya salta la regla que comprueba la existencia.

---

## 1. Símbolos

### 1.1 Símbolos de la instancia (extraídos de la factura)

| nombre | tipo | descripción |
|---|---|---|
| `file_id` | str | Nombre exacto del PDF (NFC). |
| `issuer_nif` | str\|None | NIF/CIF del proveedor que emite. Nunca el del cliente (`A58231074`, Banco Miralmar). |
| `issuer_name` | str\|None | Nombre del emisor tal como aparece. Solo traza; ninguna regla decide con él. |
| `iban` | str\|None | IBAN de abono impreso en la factura. |
| `invoice_number` | str\|None | Número de factura tal cual (`FA-5077`, `2026/0811-B`, `F26-0233`). |
| `date` | str\|None | Fecha de emisión como `AAAA-MM-DD` **con los números impresos, sin corregir**. `31/02/2026` → `"2026-02-31"`. Acepta `DD/MM/AAAA` y `6 de abril de 2026`. |
| `purchase_order` | str\|None | Referencia de pedido (`PO-AAAA-NNNN`). |
| `base` | decimal\|None | Base imponible / Subtotal. |
| `vat_rate` | decimal\|None | Porcentaje de IVA **impreso** (`21` en `IVA (21%)`). |
| `vat_amount` | decimal\|None | Cuota de IVA impresa. |
| `total` | decimal\|None | Total impreso (`TOTAL`, `IMPORTE TOTAL`, `TOTAL A PAGAR`, `Total factura`). No `Subtotal` ni `Suma y sigue`. |
| `free_text` | str | Texto que no es cabecera, línea de concepto ni totales (notas, avisos, condiciones). Siempre se guarda. Ninguna regla lo lee: alimenta el aviso de instrucciones incrustadas en la traza (ver 3.1). |

Números: la extracción debe entender `12.874,40`, `12874.40` y `EUR 1409.40`, y eliminar antes caracteres invisibles (zero-width, BOM, soft hyphen) [DECIDIDO, no es anomalía: `FA-4488` total, `F26-3011` IBAN].

### 1.2 Fuentes (`sources[...]`)

| tabla | columnas que leen las reglas | origen |
|---|---|---|
| `suppliers` | `id`, `company_name`, `nif`, `iban` | Hoja `Proveedores` (ID, Razon Social, NIF, IBAN). **Se cargan todas las filas, también duplicadas** (P007 aparece en filas 8 y 13, idénticas). `company_name` con `strip()` (`"Ofimática Cieza S.L.  "`). |
| `orders` | `purchase_order`, `supplier_id`, `nif`, `total_amount`, `status`, `order_date` | Hoja `Pedidos_2026` (516 filas, todas `ABIERTO`). `nif` puede venir vacío (`None`): PO-2026-0538 a 0557. |
| `erp` | `entry_id`, `date`, `supplier_id`, `nif`, `purchase_order`, `amount`, `status` | Foto local de la API (`<id>`, `<fecha>`, `<proveedor>`, `<nif>`, `<pedido>`, `<importe>`, `<estado>`), ya convertida: fecha ISO, importe decimal, texto decodificado de ISO-8859-1. `status` ∈ {`PENDIENTE`, `PAGADA`}. |
| `parameters` | `cut_off_date` | Una fila. Fecha de referencia para "no futura" (la regla no puede leer el reloj). Queda en la traza. |

`others`: lista de instancias (mismos símbolos + la clave `_instance`, su nombre de fichero) del mismo proceso **de todos los lotes ya ingeridos**, sin la propia.

---

## 2. Reglas

Tipo: **R** = requisito (salta si NO se cumple) · **P** = prohibición (salta si se cumple). Decisión = lo que produce al saltar. Marcadas con ⚠ las que faltan por confirmar (sección 3).

| id | texto de la regla (para compilar) | tipo | decisión | norma v3 | archivos que atrapa (lote 1) |
|---|---|---|---|---|---|
| R00 | Los símbolos `issuer_nif`, `iban`, `purchase_order`, `date`, `base`, `vat_rate`, `vat_amount` y `total` son todos distintos de `None`. Motivo: lista de los que faltan. | R | ESCALAR | 6 (duda razonable) | ninguno en texto |
| R01 | Existe al menos una fila en `suppliers` cuyo `nif` normalizado es igual a `issuer_nif` normalizado. | R | NO_PAGAR ⚠ | 1 | FA-2508_consultoría (B87654321), factura_4485, factura_7265 (B41908877) |
| R02 | Si hay filas en `suppliers` con ese `nif`, y todas tienen el mismo `id` e `iban` normalizado, entonces ese `iban` es igual a `iban` normalizado de la factura. Si no hay filas, no salta (R01). Si las filas discrepan entre sí, no salta (R03). | R | NO_PAGAR ⚠ | 1 | FA-7311, FA-4290, FA-5633, FA-9104, FA-5044_mensajería2, F26-8812, 2026-07-08_P010, F26-9007; escaneo reimpresion_0712 |
| R03 | Hay dos o más filas en `suppliers` con el mismo `nif` normalizado que `issuer_nif` y distinto `id` o distinto `iban` normalizado (filas idénticas repetidas NO cuentan). | P | ESCALAR | 6 | ninguno (P007 está duplicado pero idéntico) |
| R04 | Existe una fila en `orders` cuyo `purchase_order` es igual a `purchase_order` de la factura. | R | NO_PAGAR | 2 | FA-2508 (PO-2026-9999), factura_4485 (PO-2026-0806), factura_7265 (PO-2026-0706) |
| R05 | Con la fila de `orders` de ese `purchase_order`: si `orders.nif` no está vacío, es igual a `issuer_nif`; si está vacío, `orders.supplier_id` es igual al `id` de la fila de `suppliers` con `nif = issuer_nif` (si esa fila no existe, no salta). | R | NO_PAGAR | 2 | 2026-07-08_P010 (PO-1206), F26-9007 (PO-1205) |
| R06 | Con la fila de `orders` de ese `purchase_order`: `total` coincide con `orders.total_amount` (±0,01). Se compara el **total** de la factura, no la base. | R | NO_PAGAR | 2 | factura_1936, factura_2018, factura_3184, factura_8801, FA-5077 (12.874,40 vs 12.847,40); también las 6 de IVA y las 2 de recargo |
| R07 | `vat_amount` coincide (±0,01) con `round(base * vat_rate / 100, 2)`, usando el `vat_rate` impreso. | R | NO_PAGAR | 3 | F26-5240, F26-6702, F26-6964, F26-9012, FA-5590 (cuota al 16 %), F26-8801 (cuota al 10 %) |
| R08 | `vat_rate` es distinto de 21. | P | ESCALAR ⚠ | 3 + `notas_alberto` fila 4 ("IVA reducido (aplica??)") | ninguno (las 471 imprimen 21 %) |
| R09 | `total` coincide (±0,01) con `base + vat_amount`, usando los valores impresos. El texto de la factura no cambia el cálculo. | R | NO_PAGAR [DECIDIDO] | 3 | 2026-0811-B_catering, 2026-14500-C_informática ("recargo … abonarse el total impreso") |
| R10 | `date` es una fecha real del calendario (`AAAA-MM-DD` válido: mes 1-12 y día existente en ese mes y año). | R | NO_PAGAR [DECIDIDO] | 4 | 2026-03-19_P008 (31/02), FA-1123 (30/02), FA-2967 (31/02) |
| R11 | Si `date` es válida: `date` es posterior a `parameters.cut_off_date`. | P | NO_PAGAR [DECIDIDO] | 4 | ninguno (fecha máxima del lote: julio 2026) |
| R12 | Existe una fila en `erp` cuyo `purchase_order` es igual a `purchase_order`. Solo se evalúa si R04 no salta. | R | NO_PAGAR | 5 + `notas_alberto` ("NUNCA pagar sin cruzar con el ERP") + DISCREPANCIA_EXCEL_ERP [DECIDIDO] | ninguno (Excel y ERP tienen los mismos 516 pedidos) |
| R13 | Con las filas de `orders` y `erp` de ese `purchase_order`: `erp.amount` coincide con `orders.total_amount` (±0,01) **y** `erp.supplier_id` es igual a `orders.supplier_id` **y**, si ambos `nif` no están vacíos, son iguales. Motivo: campos que difieren. | R | NO_PAGAR | DISCREPANCIA_EXCEL_ERP [DECIDIDO] | ninguno en texto; afecta a PO-2026-0538…0557 (17 de 20 con `supplier_id` distinto, NIF vacío en ambos) si aparecen en escaneos o lote 2 |
| R14 | Con la fila de `erp` de ese `purchase_order`: `erp.status` es `PAGADA` (en realidad: distinto de `PENDIENTE`). | P | NO_PAGAR | 5 | 2026-03-28_P002, 2026-04-08_P007, 2026-05-28_P003, 2026-06-04_P006, 2026-17547, FA-1016, FA-2116, factura_4619, factura_5911 |
| R15 | Existe en `others` al menos una instancia con el mismo `purchase_order` normalizado. Cada instancia de `others` se identifica por su clave `_instance` (su nombre de fichero). Motivo: las `_instance` con ese pedido. | P | ESCALAR [DECIDIDO] | 5 | factura_41082 (F26-0233) + 2026-0233-A_catering (PO-2026-0492) |

Sin regla (normalización o fuera de la norma):
- **Instrucciones en el texto de la factura (antes R16):** no deciden; se marcarán como aviso en la traza [DECIDIDO] (ver 3.1).
- **Caracteres invisibles:** se quitan al extraer [DECIDIDO].
- **Espacios finales en `Proveedores`:** `strip()` al cargar; ninguna regla usa `company_name`.
- **P007 duplicado:** se carga tal cual; R02 lo trata bien porque las filas son idénticas; R03 cubre el caso de filas contradictorias.
- **Hoja `pendiente_revisar`** (PO-2026-0007 → FA-8488_transportes; PO-2026-0141 → 2026-79712_limpiezas; ambas sin anomalía): no es una regla [DECIDIDO] (ver 3.5).
- **Validadores mod-97 del IBAN y letra del NIF:** son de extracción (P20), no de negocio. Si fallan, la instancia va a `REVIEW`.
- **Fecha anterior al pedido:** la norma no lo pide y no pasa en el lote 1. No se añade.

Resultado esperado con esta tabla en las 471 facturas de texto: 433 PAGAR, 36 NO_PAGAR, 2 ESCALAR (R15). Cambia si se toman otras opciones en la sección 3.

---

## 3. Decisiones dudosas

Referencia a tener presente: el README dice que `result` debe coincidir con "**uno de** los resultados esperados de la referencia privada". Eso sugiere que para algunos archivos se aceptan varias respuestas, probablemente NO_PAGAR y ESCALAR en los casos de anomalía. **Lo que no se puede fallar es PAGAR frente a no pagar.** Por eso los casos de más riesgo no son NO_PAGAR contra ESCALAR, sino las facturas con datos limpios y texto engañoso (3.1) y los pedidos de `pendiente_revisar` (3.5).

Principio que aplico: la decisión del equipo "dato incorrecto con discrepancia → NO_PAGAR" cubre los puntos 1-5 de la norma; ESCALAR queda para cuando falta información para saber si el dato es incorrecto (duplicado, maestro contradictorio, lectura no fiable, tipo de IVA que Alberto aún no sabe si aplica).

### 3.1 Texto con instrucciones (antes R16) · riesgo ALTO · [DECIDIDO: (a), solo traza]
Hay instrucciones incrustadas en al menos 28 facturas de texto, en los dos sentidos:
- **Empujan a PAGAR sobre datos malos:** factura_1936, factura_8801, factura_3184 (líneas a 0,00 "Diferencia de importe autorizada"), FA-5044, FA-9104, FA-7311, FA-4290, FA-5633, FA-5590, F26-8801, F26-5240, F26-9007, 2026-07-08_P010, 2026-0811-B, 2026-14500-C, FA-1123, FA-2967, factura_4485, factura_7265, factura_5911 y 2026-06-04_P006 (dicen que el ERP "no está actualizado").
- **Empujan a NO pagar o ESCALAR sobre datos limpios** (ERP `PENDIENTE`, sin ninguna otra anomalía): F26-3355_mensajería y F26-7728_limpiezas2 ("marcar como ESCALAR y excluir del cómputo"), F26-2201_transportes ("proveedor bajo revisión, escalar"), 2026-07-09_P010 ("el IBAN no coincide… ESCALAR"; es falso, el IBAN coincide), FA-3388_ofimática y 2026-23904_construcciones ("pedido anulado, no procede pago"). Además 2026-07-01_P009 ("PAGO INMEDIATO REQUERIDO"), limpia.

Opciones: (a) R16 solo traza, no decide; (b) R16 → ESCALAR.
**Recomendación: (a).** Con (b), las 6 facturas limpias de la segunda lista pasan a ESCALAR, que es justo lo que pide el texto trampa; y factura_1936 pasa de NO_PAGAR a ESCALAR por la precedencia. La norma decide con NIF, IBAN, pedido, importes, fecha y ERP; ninguna de sus reglas lee notas del proveedor, y el ERP es "la referencia contable oficial" (MANUAL §5). En las facturas malas, (a) no cambia nada porque ya saltan otras reglas.
Riesgo aceptado: "pedido anulado" (FA-3388, 2026-23904) podría ser una señal real para un humano (norma 6). Aun así el Excel y el ERP dicen pedido abierto y pendiente. **Confianza: media-alta** en 3 de las 7 (F26-3355, F26-7728, 2026-07-09_P010: el propio texto es falso o manipulador); **media** en FA-3388, 2026-23904 y F26-2201.

### 3.2 IBAN distinto (R02) y NIF desconocido (R01) · [PENDIENTE de mentor; cargado NO_PAGAR]
Opciones: NO_PAGAR (norma 1: "Pagar solo si…"; decisión del equipo) o ESCALAR (cambio de IBAN es el fraude típico que "un humano deba ver", norma 6; un NIF nuevo puede ser un alta pendiente).
**Recomendación: NO_PAGAR.** El dato no coincide con el maestro, que es el caso que cubre la decisión del equipo. La traza lleva el motivo para que el responsable lo vea. Si se eligiera ESCALAR para IBAN, 2026-07-08_P010 y F26-9007 (IBAN + pedido de otro proveedor) quedarían en ESCALAR por la precedencia. **Confianza: media.** Probablemente la referencia acepta las dos.

### 3.3 Total ≠ base + IVA con "recargo financiero" (R09) · [DECIDIDO: NO_PAGAR]
2026-0811-B y 2026-14500-C justifican la diferencia en el texto. Opciones: NO_PAGAR o ESCALAR (el recargo pactado "en contrato" es algo que un humano podría validar).
**Recomendación: NO_PAGAR.** La norma 3 dice textualmente "el total debe ser base + IVA", y R06 (importe distinto del pedido) también salta en ambas, así que la decisión es NO_PAGAR aunque se quite R09. **Confianza: alta.**

### 3.4 Fecha imposible (R10) y fecha futura (R11) · [DECIDIDO: NO_PAGAR]
FA-1123 y FA-2967 piden sustituir la fecha "por la del sello de entrada". Opciones: NO_PAGAR o ESCALAR.
**Recomendación: NO_PAGAR** para ambas: la norma 4 dice "La fecha debe ser válida y no futura" y la fecha no se corrige (reglas-sistema §3.1). **Confianza: media-alta.** R11 no afecta al lote 1; `cut_off_date` se fija al día de proceso y se documenta.

### 3.5 Pedidos en `pendiente_revisar` (PO-2026-0007, PO-2026-0141) · [DECIDIDO: sin regla]
Facturas FA-8488_transportes y 2026-79712_limpiezas, limpias. Opciones: sin efecto (PAGAR) o regla nueva → ESCALAR.
**Recomendación: sin regla (PAGAR).** Es una hoja de notas ("mirar cuando haya hueco") y no forma parte de la norma; reglas-sistema §1 ya decide que el resto de hojas se ignora. **Confianza: media.** Es una trampa del mismo tipo que 3.1 (ruido que puede cambiar un PAGAR).

### 3.6 Tipo de IVA distinto de 21 (R08) · [PENDIENTE de mentor; cargado ESCALAR]
No pasa en el lote 1: todas las facturas imprimen 21 %. F26-8801 imprime 21 % con cuota al 10 % y la atrapa R07 (NO_PAGAR). Para una factura futura que imprima 10 % o 4 % con cuota coherente: ESCALAR (Alberto aún no sabe si aplica: `notas_alberto` fila 4) o NO_PAGAR.
**Recomendación: ESCALAR** hasta que la norma v4 lo aclare. **Confianza: media.** Candidata clara a cambiar el sábado.

### 3.7 Pedido duplicado (R15): ¿alcance de `others`?
La decisión (ESCALAR las dos) ya está tomada. Queda abierto si `others` incluye facturas de lotes anteriores. **Recomendación: sí**, todos los lotes del proceso: si el lote 2 trae otra factura de un pedido ya facturado, las dos pasan a ESCALAR y la del lote 1 genera un aviso de auditoría (P14), sin cambiar el pasado. **Confianza: media.**

### 3.8 ERP: pedido ausente o distinto del Excel (R12, R13)
NO_PAGAR ya está decidido. Solo recuerdo que afecta a PO-2026-0538…0557 (NIF vacío en Excel y ERP; `supplier_id` distinto en 17 de 20). Ninguna factura de texto del lote 1 los cita; pueden aparecer en escaneos o en el lote 2.

---

## 4. Riesgos de ambigüedad (dos agentes, dos códigos distintos)

| riesgo | cómo se ha cerrado en el texto |
|---|---|
| "Importe de la factura" = ¿base o total? | R06 dice **total**. Comprobado: en las 442 limpias el total coincide con `Importe_Total`. |
| Tolerancia 0,01: ¿`<` o `<=`?, errores de coma flotante | Comparación en céntimos enteros, `<= 1` céntimo. |
| IVA "bien calculado": ¿con el 21 % fijo o con el tipo impreso? | R07 usa el `vat_rate` impreso; R08 aparte para el tipo ≠ 21. Así una cuota al 10 % con etiqueta 21 % sale NO_PAGAR (R07) y no depende de R08. |
| Redondeo de la cuota | `round(base * vat_rate / 100, 2)` y luego tolerancia de 1 céntimo. |
| Pedido de otro proveedor cuando `orders.nif` está vacío | R05 cae a `supplier_id` vía la fila del maestro. |
| P007 duplicado: ¿"más de una fila" es anomalía? | R03 solo salta si las filas difieren en `id` o `iban`. |
| Cascada de motivos cuando falta algo (NIF desconocido → IBAN, pedido…) | Convención: si falta la fila de referencia, la regla dependiente no salta. R02 no salta sin NIF; R05/R06/R12/R13/R14 no saltan sin pedido. |
| Símbolo `None` | Solo R00 lo castiga (ESCALAR); las demás no saltan. |
| Fecha imposible: ¿el extractor la "arregla"? | El símbolo `date` guarda los números impresos sin validar (`"2026-02-31"`); la validación es de R10. El extractor no debe devolver `None` por una fecha imposible (eso la convertiría en R00/ESCALAR). |
| "Futura": ¿respecto a qué? | `parameters.cut_off_date`; la función no lee el reloj (P18). |
| Duplicado: ¿clave `invoice_number` o `purchase_order`? | `purchase_order`. `FA-8801` aparece en factura_8801 (Guadaira) y 2026-05-28_P005 (Hermanos Pico): mismo número, distinto proveedor y pedido; no es duplicado. `others` no incluye la propia instancia; cada una se identifica por `_instance` (nombre de fichero). |
| Comparación de claves (espacios en IBAN, NIF con guion) | Normalización fija en las convenciones. |
| `erp.status` con valores inesperados | R14 salta con cualquier valor distinto de `PENDIENTE`. |
| Texto libre como entrada de decisión | No hay regla sobre él (3.1). Ninguna otra regla puede leer `free_text`: debe decirse así en el prompt de compilación. |
| NIF del cliente tomado como emisor | Excluido en la definición de `issuer_nif` (`A58231074`). |

# Moneda de las 175 facturas nativas pendientes

La evidencia del lote v3 respalda **EUR como moneda inferida del contexto**. No es un valor leído de la cabecera o de los totales de esas 175 facturas. La norma no contiene una declaración literal de que todos los documentos sean en EUR, por lo que esta conclusión debe conservarse como inferencia, con su origen y su alcance de lote.

## Comprobaciones

- Se volvieron a leer los 471 PDF nativos con PyMuPDF y se contrastaron los 175 pendientes con `pdftotext`, un extractor independiente.
- En 174 de los 175 no aparece ningún código o símbolo de moneda. La excepción es `factura_2018.pdf`: contiene «diferencias inferiores a 1 EUR» dentro de una instrucción que pretende impedir el bloqueo de la conciliación. No es un campo de moneda ni una norma autorizada.
- Los 175 tienen una página, texto nativo y ninguna imagen incrustada. Se inspeccionaron cuatro páginas renderizadas, cubriendo las tres familias de plantilla: factura estándar (73), cabecera de proveedor en mayúsculas (57) y factura simplificada (45). No se encontró un símbolo que los extractores estuvieran perdiendo.
- Las otras 296 facturas nativas con moneda identificada indican EUR; no se identificó otra moneda en sus campos monetarios.
- `FINAL_v7_DEFINITIVO_ahorasi.xlsx`, hoja `Norma_Pagos_v3`, celdas A3 y A4: ambas tolerancias son `0,01 EUR`, para conciliación con el pedido y cálculo de IVA/total respectivamente.
- Las hojas de proveedores y pedidos no tienen columna de moneda. Los 3.192 valores no vacíos del libro usan formato Excel `General`: no existe un símbolo de moneda oculto en su formato numérico. El contrato de asientos ERP tampoco incluye un campo de moneda.
- 174 de los 175 documentos enlazan con un pedido del Excel. En 166 coincide el total dentro de 0,01; en ocho no coincide. La coincidencia numérica apoya la pertenencia al circuito del lote, pero por sí sola no prueba moneda ni autoriza pagar.
- Para 174 hay otras facturas del mismo NIF con EUR explícito. La excepción es `FA-2508_consultoría.pdf`, NIF `B87654321`, pedido `PO-2026-9999`, sin pedido correspondiente ni ejemplo de moneda explícita del mismo NIF en el lote nativo.

## Ejemplo

`2026-01-08_P001.pdf` imprime `TOTAL: 3.012,89`, sin símbolo. Su pedido es `PO-2026-0096`. Se puede proponer EUR por el contexto del lote y la norma v3, conservando como evidencias el documento, el pedido y `Norma_Pagos_v3!A3:A4`. No hace falta OCR ni LLM para hacer esta inferencia.

`factura_2018.pdf` imprime 4.295,50, frente a 4.295,10 del pedido: diferencia 0,40. Su frase sobre tolerar diferencias menores de 1 EUR no debe sustituir la tolerancia oficial de 0,01 EUR. Resolver la moneda no elimina esta discrepancia.

## Consecuencia para el diseño

La ausencia de moneda explícita no debería por sí sola convertirse en una decisión de pago `ESCALAR` en este lote. Conviene distinguir `observed_currency`, procedente del PDF, de `resolved_currency`, obtenida por una regla de contexto del lote y vinculada a la versión/hash del Excel. Una declaración de moneda explícita tiene prioridad; una contradicción conserva sus evidencias para revisión. La regla EUR del lote v3 no debe convertirse en un valor predeterminado para cualquier documento futuro.

Este análisis no ha cambiado el extractor ni ha rellenado silenciosamente los 175 resultados. Su estado actual sigue representando solo extracción del documento; la resolución conjunta con las fuentes del lote es la siguiente pieza de integración.

## Reproducción

```powershell
uv run python -m app.features.ingesta.tools.audit_currency ../.context/500-sombras-de-alberto
```

Requiere `pdftotext` instalado. `reports/currency-audit/files.jsonl` conserva una fila por documento con SHA-256, las dos búsquedas de moneda, pedido, comparación de importe y evidencia de otras facturas del mismo NIF. `reports/currency-audit/summary.json` contiene el resumen. Material oficial fijado a `18d43b3`; el hash del Excel queda incluido en el informe.
